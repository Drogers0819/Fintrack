"""
Net worth service — the metric that replaces "Savings rate" on the
overview page. Honest about the financial position of users 22-35:
most start in a deficit (credit card debt, overdrafts, loans). The
metric surfaces savings minus debts, plus the user's progress since
they completed onboarding.

Discipline
----------
Debt is debt — no carve-outs for student loans, no "but this is a
mortgage" exception. The single carve-out we couldn't avoid is data
the model doesn't carry: outstanding mortgage balances aren't stored
anywhere, so they don't appear in the calc. That's a data limitation,
documented in DEVELOPMENT.md, not a deliberate exclusion.

Asset / liability rules
-----------------------
Assets: every active or completed Goal where the name isn't a debt
keyword AND current_amount > 0. A completed Emergency Fund still
holds £3,000 — that's an asset and we count it.

Liabilities: every Goal where the name IS a debt keyword AND
(target - current) > 0. A paid-off credit card has remaining=0 and
drops out naturally.

Net worth = assets - liabilities.

Progress = current net worth - starting_net_worth snapshot (captured
at plan_wizard_complete=True, never overwritten).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


_ZERO = Decimal("0")


def _to_decimal(value) -> Decimal:
    if value is None:
        return _ZERO
    return Decimal(str(value))


def compute_current_net_worth(user) -> Decimal:
    """Sum savings goal balances and subtract remaining debt balances.

    Status filter is intentionally absent: completed savings goals
    still hold value (their current_amount stays on the user's books)
    and completed debt goals naturally drop out via the
    `(target - current) > 0` filter on the liability side.
    """
    from app.models.goal import Goal
    from app.services.goal_classification import _is_debt_goal_name

    goals = Goal.query.filter_by(user_id=user.id).all()

    assets = _ZERO
    liabilities = _ZERO

    for goal in goals:
        name = goal.name or ""
        current = _to_decimal(goal.current_amount)
        target = _to_decimal(goal.target_amount)

        if _is_debt_goal_name(name):
            remaining = target - current
            if remaining > 0:
                liabilities += remaining
        else:
            if current > 0:
                assets += current

    return assets - liabilities


def compute_progress(user) -> Decimal:
    """Improvement since onboarding completed.

    Returns 0 when starting_net_worth has not been snapshotted yet —
    a user mid-onboarding has no baseline to compare against, so
    progress is undefined until plan_wizard_complete fires.
    """
    starting = getattr(user, "starting_net_worth", None)
    if starting is None:
        return _ZERO
    return compute_current_net_worth(user) - _to_decimal(starting)


def get_net_worth_summary(user) -> dict[str, Any]:
    """Template-ready summary dict.

    Always returns a stable dict shape so the template can branch on
    `has_started` without worrying about missing keys.
    """
    starting_raw = getattr(user, "starting_net_worth", None)
    has_started = starting_raw is not None
    current = compute_current_net_worth(user)
    starting = _to_decimal(starting_raw) if has_started else _ZERO
    progress = current - starting if has_started else _ZERO

    return {
        "current": current,
        "starting": starting,
        "progress": progress,
        "has_started": has_started,
    }


def snapshot_starting_net_worth(user) -> bool:
    """Persist the user's net worth as their starting baseline.

    Idempotent: if `starting_net_worth` is already set, do nothing and
    return False. Returns True when a snapshot is written.

    Called once at the end of onboarding (plan_wizard_complete=True),
    when all factfind data and goal chips have been persisted.
    """
    from app import db

    if getattr(user, "starting_net_worth", None) is not None:
        return False

    snapshot = compute_current_net_worth(user)
    user.starting_net_worth = snapshot
    db.session.commit()
    logger.info("Snapshotted starting_net_worth=%s for user=%s", snapshot, user.id)
    return True
