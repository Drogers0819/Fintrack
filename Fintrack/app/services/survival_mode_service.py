"""
Survival mode — Block 2 Task 2.5.

When income drops meaningfully (or the user manually flips it on),
the planner enters survival mode: non-essential goals pause,
lifestyle reduces to a survival floor, the plan focuses on
housing / debt minimums / essentials only.

This service handles the activation gate, the floor calculation,
and the on/off transitions. The actual planner branch lives in
planner_service._generate_survival_plan; this module decides
*whether* to flip the switch and stamps the audit trail.

FCA discipline: nothing in this module recommends a financial
product, suggests how to handle creditors, or advises on
borrowing. It mutates two columns on User and writes one
analytics event per transition.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


# 25% drop is the auto-activation threshold. Below this, the plan can
# usually adapt without survival mode (a 10% drop just means smaller
# goal contributions; a 30% drop means several goals stop being
# achievable on time). The number is calibrated, not load-bearing —
# tune later if real usage suggests otherwise.
INCOME_DROP_THRESHOLD = 0.25

# Survival lifestyle floor. Whichever is higher of:
#   • 20% of monthly income — scales with the user's situation
#   • £400/month — absolute floor for groceries, transport, basics
SURVIVAL_LIFESTYLE_FRACTION = 0.20
SURVIVAL_LIFESTYLE_HARD_FLOOR = 400.0


def should_auto_activate(user, new_monthly_income) -> bool:
    """Return True when the new income represents a >= 25% drop from
    the user's currently-stored monthly_income.

    Returns False when:
      • The user has no previous monthly_income on file (we don't have
        a baseline to compare against).
      • new_monthly_income is None (the unknown branch from /crisis/income).
      • The drop is smaller than INCOME_DROP_THRESHOLD.
      • Survival mode is already active (no double-fire).
    """
    if new_monthly_income is None:
        return False
    if user.monthly_income is None:
        return False
    if getattr(user, "survival_mode_active", False):
        return False

    previous = float(user.monthly_income)
    if previous <= 0:
        return False
    new_amount = float(new_monthly_income)
    drop_fraction = (previous - new_amount) / previous
    return drop_fraction >= INCOME_DROP_THRESHOLD


def activate_survival_mode(user, reason: str = "manual") -> None:
    """Flip the flag on, stamp the timestamp, fire the analytics event.

    `reason` is one of "manual" (toggled from settings) or "income_drop"
    (auto-activated by the crisis flow). The reason flows into the
    PostHog event so we can see which path is more common.
    """
    from app import db
    from app.services.analytics_service import track_event

    user.survival_mode_active = True
    user.survival_mode_started_at = datetime.utcnow()
    db.session.commit()

    track_event(user.id, "survival_mode_activated", {
        "reason": reason,
    })


def deactivate_survival_mode(user) -> None:
    """Flip the flag off but leave survival_mode_started_at intact as a
    historical record. We can use the timestamp later to count how long
    a user spent in survival mode, but we never overwrite or clear it
    — each activation moment is preserved on the next entry."""
    from app import db
    from app.services.analytics_service import track_event

    user.survival_mode_active = False
    db.session.commit()

    track_event(user.id, "survival_mode_deactivated", {})


def get_survival_floor(user) -> float:
    """The minimum monthly lifestyle budget under survival mode.
    `max(monthly_income * 0.20, 400)`. Returns the hard floor when the
    user has no income on file (defensive — shouldn't happen since the
    planner already requires monthly_income, but keeps the helper safe
    to call in isolation)."""
    income = user.monthly_income
    if income is None:
        return SURVIVAL_LIFESTYLE_HARD_FLOOR
    income_f = float(income)
    if income_f <= 0:
        return SURVIVAL_LIFESTYLE_HARD_FLOOR
    return max(income_f * SURVIVAL_LIFESTYLE_FRACTION, SURVIVAL_LIFESTYLE_HARD_FLOOR)
