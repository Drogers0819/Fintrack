"""
Recurring contributions — chip-level persistence for the factfind
sub-chips that previously collapsed into a single scalar per source.

Public surface
--------------
  • sync_contributions_from_factfind(user, source, chip_data, custom_entries)
      Wipes and re-creates rows for the source, then recomputes the
      cached aggregate on User. Called from the factfind POST handler.

  • get_contributions_for_user(user, source=None) -> list
      Returns rows for a user, optionally filtered by source.

  • get_contributions_total(user, source=None) -> Decimal
      Sums amounts; this is the canonical computation behind the
      cached User.{source}_total fields.

  • get_contributions_for_goal(goal) -> list
      Returns all contributions linked to a goal. Used by the
      commitments panel (goals subsection) and companion context.

Cached-aggregate invariant
--------------------------
After every sync_contributions_from_factfind call, the matching User
column (User.subscriptions_total or User.other_commitments) is
overwritten with the sum of the rows for that source. The columns
are kept as cache-only storage; they remain authoritative for the
12+ downstream consumers (planner, companion, surplus_reveal, etc.)
that already read them as scalars.

Never write to User.subscriptions_total or User.other_commitments
outside this service.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Iterable

logger = logging.getLogger(__name__)


# Map source → User column that caches its aggregate. Single source of
# truth for the cache invariant.
_SOURCE_TO_AGGREGATE_COLUMN = {
    "subscriptions": "subscriptions_total",
    "other_commitments": "other_commitments",
}


def _validate_source(source: str) -> None:
    if source not in _SOURCE_TO_AGGREGATE_COLUMN:
        raise ValueError(
            f"Unknown contribution source: {source!r}. "
            f"Valid: {tuple(_SOURCE_TO_AGGREGATE_COLUMN)}."
        )


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def get_contributions_for_user(user, source: str | None = None):
    """Return RecurringContribution rows for a user, optionally
    filtered by source. Ordering: amount descending so the largest
    contributions surface first wherever the rows are rendered."""
    from app.models.recurring_contribution import RecurringContribution

    if source is not None:
        _validate_source(source)

    query = RecurringContribution.query.filter_by(user_id=user.id)
    if source is not None:
        query = query.filter_by(source=source)
    return query.order_by(RecurringContribution.amount.desc()).all()


def get_contributions_total(user, source: str | None = None) -> Decimal:
    """Sum contribution amounts for a user, optionally filtered by
    source. Returns Decimal("0") when there are no matching rows."""
    rows = get_contributions_for_user(user, source=source)
    total = sum((_to_decimal(r.amount) for r in rows), Decimal("0"))
    return total.quantize(Decimal("0.01"))


def get_contributions_for_goal(goal):
    """Return all RecurringContribution rows linked to the given goal,
    ordered by amount descending. Used by the commitments panel goals
    subsection and the companion context builder."""
    from app.models.recurring_contribution import RecurringContribution

    return (
        RecurringContribution.query
        .filter_by(linked_goal_id=goal.id)
        .order_by(RecurringContribution.amount.desc())
        .all()
    )


def sync_contributions_from_factfind(
    user,
    source: str,
    chip_data: dict | None,
    custom_entries: Iterable[dict] | None,
) -> None:
    """Replace the user's contributions for `source` with fresh rows.

    `chip_data`: dict keyed by chip_id, values are dicts with at least
    {"label": str, "amount": number}. Standard chips. Entries with
    amount <= 0 are dropped.

    `custom_entries`: iterable of {"label": str, "amount": number}
    dicts. User-typed custom entries that have no chip_id. Entries
    with amount <= 0 or blank label are dropped.

    After writing rows, recomputes and persists the cached aggregate
    column on User. The sync is intentionally wipe-and-recreate: it
    matches the factfind UX where the user re-submits the entire chip
    selection each time, and avoids partial-update bookkeeping.

    Returns None. Commits the session.
    """
    from app import db
    from app.models.recurring_contribution import RecurringContribution

    _validate_source(source)

    # 1. Wipe existing rows for this source.
    RecurringContribution.query.filter_by(
        user_id=user.id, source=source,
    ).delete(synchronize_session=False)

    rows_to_insert: list[RecurringContribution] = []

    # 2. Standard chips.
    if chip_data:
        for chip_id, entry in chip_data.items():
            if not isinstance(entry, dict):
                continue
            amount = _to_decimal(entry.get("amount"))
            if amount <= 0:
                continue
            label = (entry.get("label") or chip_id or "").strip()
            if not label:
                # No label and no chip_id wouldn't be displayable; skip.
                continue
            rows_to_insert.append(RecurringContribution(
                user_id=user.id,
                source=source,
                chip_id=chip_id,
                label=label,
                amount=amount,
            ))

    # 3. Custom user-typed entries.
    if custom_entries:
        for entry in custom_entries:
            if not isinstance(entry, dict):
                continue
            amount = _to_decimal(entry.get("amount"))
            if amount <= 0:
                continue
            label = (entry.get("label") or "").strip()
            if not label:
                continue
            rows_to_insert.append(RecurringContribution(
                user_id=user.id,
                source=source,
                chip_id=None,
                label=label,
                amount=amount,
            ))

    for row in rows_to_insert:
        db.session.add(row)

    # 4. Cached aggregate write-back.
    aggregate_column = _SOURCE_TO_AGGREGATE_COLUMN[source]
    new_total = sum(
        (_to_decimal(r.amount) for r in rows_to_insert),
        Decimal("0"),
    ).quantize(Decimal("0.01"))
    setattr(user, aggregate_column, new_total)

    db.session.commit()
    logger.info(
        "Synced %d %s contributions for user=%s (total=%s)",
        len(rows_to_insert), source, user.id, new_total,
    )


def recompute_cached_aggregate(user, source: str) -> Decimal:
    """Recompute and persist the cached aggregate for a source from
    the existing rows. Used by the backfill CLI and any future code
    that mutates rows outside the sync path.

    Returns the new total written to User.
    """
    from app import db

    _validate_source(source)
    total = get_contributions_total(user, source=source)
    aggregate_column = _SOURCE_TO_AGGREGATE_COLUMN[source]
    setattr(user, aggregate_column, total)
    db.session.commit()
    return total
