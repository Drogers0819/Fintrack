"""
Spending breakdown + monthly commitments — overview page services.

Two related concepts that share data sources, so they live in one
module:

  • get_spending_breakdown_for_user(user, month, year)
    Aggregates this month's expense transactions by category, returns
    ring-chart-ready data with computed SVG arc math and harmonised
    colours.

  • get_monthly_commitments_for_user(user)
    Returns the user's known recurring monthly outflows (rent, bills,
    subscriptions, debt repayments, goal contributions). Pure read of
    the User model + active Goal rows. No transaction inference.

Colour discipline
-----------------
Categories use harmonised variants of their seed colours rather than
priority-rank colours, so a category has stable identity month to
month. The seed colours in DEFAULT_CATEGORIES (icon-friendly bright
hues) clash with the Obsidian Vault canvas, so we map each to a
desaturated/darkened variant tuned for deep-navy backgrounds.
RING_CATEGORY_COLOURS is the source of truth for ring rendering;
the DB seed colours stay untouched for icon use elsewhere.
"""

from __future__ import annotations

import calendar
import math
from datetime import date


# ─── Harmonised category colours for the ring chart ─────────
#
# Each value is a desaturated/darkened variant of the category's
# DEFAULT_CATEGORIES seed colour, tuned to sit on deep-navy without
# fighting the Roman Gold accents elsewhere on the page.
RING_CATEGORY_COLOURS: dict[str, str] = {
    "Food":          "#C07A55",  # warm rust-orange (~25°) — distinct warm anchor
    "Transport":     "#4A8EC4",  # clear sky blue (~210°) — wide hue gap from Food
    "Bills":         "#52A882",  # sage-teal (~155°) — green quadrant
    "Entertainment": "#9E7DC4",  # violet (~275°) — clearly not gold
    "Shopping":      "#C45278",  # dusty rose (~345°) — cool red
    "Health":        "#52A0A8",  # steel teal (~185°) — blue-green
    "Education":     "#8A8FC4",  # periwinkle (~235°) — blue-violet
    "Subscriptions": "#7B5CA8",  # medium purple (~265°) — distinct from Entertainment
    "Rent":          "#C49A55",  # warm amber (~40°) — warm but lighter than Food
    "Other":         "#7A7872",  # warm grey — neutral fallback
}

_FALLBACK_RING_COLOUR = "#6B6B65"


def colour_for_category(category_name: str) -> str:
    """Return the harmonised ring colour for a category. Unknown
    categories fall back to muted warm grey so an unexpected category
    name never blanks a segment."""
    return RING_CATEGORY_COLOURS.get(category_name, _FALLBACK_RING_COLOUR)


# Categories excluded from spending breakdown (not actual user spend).
_EXCLUDED_CATEGORIES = ("Income", "Transfer")


# Ring geometry. Radius 70 gives circumference ~439.82 — clean working
# numbers and a comfortable 200x200 viewBox with 20px stroke width.
RING_RADIUS = 70
RING_CIRCUMFERENCE = round(2 * math.pi * RING_RADIUS, 2)


# ─── Spending breakdown ──────────────────────────────────────


def get_spending_breakdown_for_user(
    user, month: int | None = None, year: int | None = None,
) -> dict:
    """Aggregate this month's expense transactions by category.

    If the user has no transactions for the period BUT factfind data
    exists, returns a preview ring built from the factfind values
    (rent, bills, subscriptions, groceries, transport) with
    `is_preview=True`. Template uses the flag to render with reduced
    opacity, a "(estimate)" suffix on legend rows, and a banner
    explaining that the user is looking at a preview.

    Returns:
      {
        total_spent: float,
        categories: [...],
        month_label: "May 2026",
        is_preview: bool,
      }

    Empty state (no transactions, no factfind data): total_spent=0,
    categories=[], is_preview=False.
    """
    from sqlalchemy import extract, func
    from app import db
    from app.models.category import Category
    from app.models.transaction import Transaction

    today = date.today()
    if month is None:
        month = today.month
    if year is None:
        year = today.year

    month_label = date(year, month, 1).strftime("%B %Y")

    rows = (
        db.session.query(
            Category.name,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.user_id == user.id,
            Transaction.type == "expense",
            ~Category.name.in_(_EXCLUDED_CATEGORIES),
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    # Sum at the Python layer to avoid a second query and to keep the
    # totals consistent with what's been included in the segment list.
    total_spent = round(float(sum(float(r.total or 0) for r in rows)), 2)
    if total_spent > 0:
        categories = _compute_segments(
            [(r.name, float(r.total or 0)) for r in rows],
            total_spent,
        )
        return {
            "total_spent": total_spent,
            "categories": categories,
            "month_label": month_label,
            "is_preview": False,
        }

    # No transactions for the period — try a factfind-driven preview.
    preview_rows = _factfind_preview_rows(user)
    if preview_rows:
        preview_total = round(sum(amount for _, amount in preview_rows), 2)
        return {
            "total_spent": preview_total,
            "categories": _compute_segments(preview_rows, preview_total),
            "month_label": month_label,
            "is_preview": True,
        }

    # No transactions, no factfind data — true empty state.
    return {
        "total_spent": 0.0,
        "categories": [],
        "month_label": month_label,
        "is_preview": False,
    }


# ─── Factfind preview helpers ────────────────────────────────


# Map factfind profile fields to the same category names used by real
# transactions. Sharing names means RING_CATEGORY_COLOURS gives every
# category a stable identity whether the source is a transaction or a
# factfind estimate. Order matters only insofar as ties break by
# insertion order; _compute_segments sorts by amount.
_FACTFIND_CATEGORY_FIELDS = (
    ("Rent", "rent_amount"),
    ("Bills", "bills_amount"),
    ("Subscriptions", "subscriptions_total"),
    ("Food", "groceries_estimate"),
    ("Transport", "transport_estimate"),
)


def _factfind_preview_rows(user) -> list[tuple[str, float]]:
    """Return (category_name, amount) pairs from factfind values, sorted
    descending by amount. Skips zero / None values. Empty list when
    the user has no factfind data."""
    rows: list[tuple[str, float]] = []
    for category_name, attr in _FACTFIND_CATEGORY_FIELDS:
        amount = _amount_or_zero(getattr(user, attr, None))
        if amount > 0:
            rows.append((category_name, amount))
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows


def _compute_segments(rows: list[tuple[str, float]], total: float) -> list[dict]:
    """Build the list of segment dicts for the ring chart, with
    cumulative dashoffsets so adjacent segments line up cleanly."""
    segments: list[dict] = []
    cumulative_arc = 0.0

    for name, amount in rows:
        if amount <= 0:
            continue
        arc = (amount / total) * RING_CIRCUMFERENCE
        gap = RING_CIRCUMFERENCE - arc
        segments.append({
            "name": name,
            "amount": round(amount, 2),
            "percentage": round((amount / total) * 100, 1),
            "colour": colour_for_category(name),
            # The pair (visible-arc, gap) — SVG draws the visible arc
            # length then leaves the rest of the circumference blank.
            "stroke_dasharray": f"{round(arc, 2)} {round(gap, 2)}",
            # Negative offset positions this segment after all earlier
            # ones. Combined with a -90deg SVG rotation, arc 0 starts
            # at 12 o'clock.
            "stroke_dashoffset": str(round(-cumulative_arc, 2)),
        })
        cumulative_arc += arc

    return segments


# ─── Monthly commitments ─────────────────────────────────────
#
# Read User profile fields + active Goal rows. We deliberately exclude
# `groceries_estimate`, `transport_estimate`, `other_commitments` —
# those are factfind estimates, not signed-up commitments. Their
# spending shows up in the ring chart via real transactions; that's
# the right place for them.

from app.services.goal_classification import _is_debt_goal_name


def _amount_or_zero(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def get_monthly_commitments_for_user(user) -> dict:
    """Return the user's known recurring monthly commitments split
    into two distinct subsections, plus the factfind estimates.

    The new shape (Tier 2 clarity follow-up) separates fixed
    obligations (rent, bills, subscriptions) from goal contributions
    (one row per active goal with monthly_allocation > 0). This makes
    the categorical distinction visible without changing the totals.

    Order:
      • obligations: Rent / mortgage, Bills, Subscriptions
      • goal_contributions: descending by amount (visual weight
        matches the amount). priority_rank is intentionally NOT used
        here because the panel is a financial summary, not a planner
        ordering surface.

    `total_committed` is the sum of both subtotals — the grand total
    the template shows in Roman Gold. `items` is preserved as a
    legacy alias (concatenation of obligations + goal_contributions)
    so callers that still read the flat list keep working until they
    migrate.

    Returns:
      {
        obligations: [{name, amount, category}, ...],
        obligations_total: float,
        goal_contributions: [{name, amount, category}, ...],
        goal_contributions_total: float,
        items: [...],                  # legacy: obligations + goals
        total_committed: float,        # obligations_total + goal_contributions_total
        estimates: [{name, amount}, ...],
        total_estimated: float,
      }
    """
    from app.models.goal import Goal

    obligations: list[dict] = []

    rent = _amount_or_zero(getattr(user, "rent_amount", None))
    if rent > 0:
        obligations.append({"name": "Rent / mortgage", "amount": round(rent, 2), "category": "rent"})

    bills = _amount_or_zero(getattr(user, "bills_amount", None))
    if bills > 0:
        obligations.append({"name": "Bills", "amount": round(bills, 2), "category": "bills"})

    subs = _amount_or_zero(getattr(user, "subscriptions_total", None))
    if subs > 0:
        obligations.append({"name": "Subscriptions", "amount": round(subs, 2), "category": "subscriptions"})

    obligations_total = round(sum(o["amount"] for o in obligations), 2)

    goal_contributions: list[dict] = []
    goals = Goal.query.filter_by(user_id=user.id, status="active").all()
    for goal in goals:
        amount = _amount_or_zero(goal.monthly_allocation)
        if amount <= 0:
            continue
        goal_contributions.append({
            "name": goal.name,
            "amount": round(amount, 2),
            "category": "debt" if _is_debt_goal_name(goal.name or "") else "goal",
        })

    # Linked RecurringContributions surface under the goals subsection
    # too. Label format "<chip_label> → <goal_name>" makes the link
    # explicit. Only other_commitments-source contributions are eligible
    # — subscriptions stay in obligations to avoid double-counting the
    # cached subscriptions_total scalar.
    from app.models.recurring_contribution import RecurringContribution
    goal_id_to_name = {g.id: g.name for g in goals}
    linked_other = (
        RecurringContribution.query
        .filter(RecurringContribution.user_id == user.id)
        .filter(RecurringContribution.source == "other_commitments")
        .filter(RecurringContribution.linked_goal_id.isnot(None))
        .all()
    )
    for contrib in linked_other:
        goal_name = goal_id_to_name.get(contrib.linked_goal_id)
        if not goal_name:
            # The contribution's linked goal isn't in the active-goals
            # set (deleted, archived, completed). Treat as unlinked
            # and let it fall through to the estimates section below.
            continue
        goal_contributions.append({
            "name": f"{contrib.label} → {goal_name}",
            "amount": round(float(contrib.amount), 2),
            "category": "linked_contribution",
        })

    # Descending by amount. The visual weight in the panel matches the
    # numeric weight — the largest contribution sits at the top.
    goal_contributions.sort(key=lambda g: g["amount"], reverse=True)
    goal_contributions_total = round(
        sum(g["amount"] for g in goal_contributions), 2,
    )

    items = list(obligations) + list(goal_contributions)
    total = round(obligations_total + goal_contributions_total, 2)

    # ─── Factfind estimates ──────────────────────────────────
    # Deliberately separate from `items`. The "(estimate)" suffix is
    # owned by the service so the template doesn't need to know which
    # rows are estimates. Same skip-on-zero rule as the commitments.
    estimates: list[dict] = []

    groceries = _amount_or_zero(getattr(user, "groceries_estimate", None))
    if groceries > 0:
        estimates.append({
            "name": "Groceries (estimate)",
            "amount": round(groceries, 2),
        })

    transport = _amount_or_zero(getattr(user, "transport_estimate", None))
    if transport > 0:
        estimates.append({
            "name": "Transport (estimate)",
            "amount": round(transport, 2),
        })

    # Per-row unlinked other_commitments contributions take the place
    # of the legacy "Other (estimate)" roll-up scalar. A user with a
    # £200 LISA contribution they haven't yet linked to a goal sees
    # "LISA contributions" here; once linked, the row moves to the
    # goals subsection above. Subscriptions stay in obligations
    # whether linked or not — the cached subscriptions_total scalar
    # is the canonical surface for that source.
    #
    # Also covers the case where a contribution's linked goal has
    # been deleted / archived / completed: the linked_other loop above
    # skipped them; here we treat them as unlinked again so they
    # still appear somewhere on the panel.
    unlinked_other = (
        RecurringContribution.query
        .filter(RecurringContribution.user_id == user.id)
        .filter(RecurringContribution.source == "other_commitments")
        .order_by(RecurringContribution.amount.desc())
        .all()
    )
    active_goal_ids = set(goal_id_to_name.keys())
    for contrib in unlinked_other:
        if contrib.linked_goal_id in active_goal_ids:
            continue  # already surfaced in goal_contributions above
        estimates.append({
            "name": contrib.label,
            "amount": round(float(contrib.amount), 2),
        })

    total_estimated = round(sum(e["amount"] for e in estimates), 2)

    return {
        "obligations": obligations,
        "obligations_total": obligations_total,
        "goal_contributions": goal_contributions,
        "goal_contributions_total": goal_contributions_total,
        "items": items,  # legacy alias for existing callers
        "total_committed": total,
        "estimates": estimates,
        "total_estimated": total_estimated,
    }
