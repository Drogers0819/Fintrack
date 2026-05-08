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
    "Food":          "#B8704F",  # warmer terracotta, desaturated
    "Transport":     "#3D6585",  # deeper steel blue
    "Bills":         "#5F8A7A",  # deeper sage
    "Entertainment": "#C2A569",  # muted ochre, close to Roman Gold
    "Shopping":      "#8E5670",  # deeper plum
    "Health":        "#5F7E9D",  # muted slate blue
    "Education":     "#8E8EA8",  # muted lavender-grey
    "Subscriptions": "#7A6E9A",  # deeper purple
    "Rent":          "#5F8270",  # deeper green-sage
    "Other":         "#6B6B65",  # muted warm grey
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

_DEBT_KEYWORDS = ("credit card", "loan", "overdraft", "pay off")


def _is_debt_goal_name(name: str) -> bool:
    if not name:
        return False
    lower = name.lower()
    return any(keyword in lower for keyword in _DEBT_KEYWORDS)


def _amount_or_zero(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def get_monthly_commitments_for_user(user) -> dict:
    """Return the user's known recurring monthly commitments AND the
    factfind estimates that aren't commitments but still describe the
    typical monthly outflow.

    The two are kept distinct: `items` / `total_committed` are
    confirmed commitments (rent, bills, subscriptions, active goals),
    while `estimates` / `total_estimated` are factfind estimates
    (groceries, transport, other) that the template renders below the
    commitments with deliberately softer hierarchy.

    Order for items: Rent / mortgage, Bills, Subscriptions, then
    debt-shaped goals, then other goals. Order for estimates:
    Groceries, Transport, Other. Zero-valued fields skipped on both
    sides; an inactive goal is skipped.

    Returns:
      {
        items: [{name, amount, category}, ...],          # commitments
        total_committed: float,
        estimates: [{name, amount}, ...],                # factfind
        total_estimated: float,
      }
    """
    from app.models.goal import Goal

    items: list[dict] = []

    rent = _amount_or_zero(getattr(user, "rent_amount", None))
    if rent > 0:
        items.append({"name": "Rent / mortgage", "amount": round(rent, 2), "category": "rent"})

    bills = _amount_or_zero(getattr(user, "bills_amount", None))
    if bills > 0:
        items.append({"name": "Bills", "amount": round(bills, 2), "category": "bills"})

    subs = _amount_or_zero(getattr(user, "subscriptions_total", None))
    if subs > 0:
        items.append({"name": "Subscriptions", "amount": round(subs, 2), "category": "subscriptions"})

    goals = (
        Goal.query.filter_by(user_id=user.id, status="active")
        .order_by(Goal.priority_rank.asc(), Goal.id.asc())
        .all()
    )

    debt_goals = [g for g in goals if _is_debt_goal_name(g.name or "")]
    other_goals = [g for g in goals if not _is_debt_goal_name(g.name or "")]

    for goal in debt_goals:
        amount = _amount_or_zero(goal.monthly_allocation)
        if amount <= 0:
            continue
        items.append({
            "name": goal.name,
            "amount": round(amount, 2),
            "category": "debt",
        })

    for goal in other_goals:
        amount = _amount_or_zero(goal.monthly_allocation)
        if amount <= 0:
            continue
        items.append({
            "name": goal.name,
            "amount": round(amount, 2),
            "category": "goal",
        })

    total = round(sum(item["amount"] for item in items), 2)

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

    other = _amount_or_zero(getattr(user, "other_commitments", None))
    if other > 0:
        estimates.append({
            "name": "Other (estimate)",
            "amount": round(other, 2),
        })

    total_estimated = round(sum(e["amount"] for e in estimates), 2)

    return {
        "items": items,
        "total_committed": total,
        "estimates": estimates,
        "total_estimated": total_estimated,
    }
