"""
Crisis flow service — Block 2 Task 2.4.

Three entry points captured by /crisis: lost income, unexpected cost,
and pause request. Each writes a row to `crisis_events` and (for the
income path) updates user state. Cost absorption reuses the existing
can_i_afford planner helper rather than reimplementing.

FCA discipline
--------------
Nothing in this module recommends a financial product, suggests a debt
arrangement, or tells the user what to do with money outside Claro.
The service writes the event and surfaces what *the plan* can do; the
templates handle signposting to free regulated UK resources
(StepChange, MoneyHelper, Citizens Advice, Samaritans, Mind).
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


def record_lost_income(
    user,
    *,
    change_type: str,
    new_monthly_income: float | Decimal | None,
    occurred_on: date | None = None,
    income_unknown: bool = False,
) -> Any:
    """Write a `lost_income` event and update the user's monthly_income
    if a new value was provided.

    `income_unknown=True` is the "I don't know yet" path: we still write
    the event so the system knows something changed, but we leave
    monthly_income alone so the plan keeps using the previous figure
    until the user comes back with a number.
    """
    from app import db
    from app.models.crisis_event import CrisisEvent

    event = CrisisEvent(
        user_id=user.id,
        event_type="lost_income",
        income_change_type=change_type,
        income_unknown=income_unknown,
        occurred_on=occurred_on,
    )

    if not income_unknown and new_monthly_income is not None:
        amount = Decimal(str(new_monthly_income))
        event.new_monthly_income = amount
        user.monthly_income = amount

    db.session.add(event)
    db.session.commit()
    return event


def record_unexpected_cost(
    user,
    *,
    description: str,
    amount: float | Decimal,
    already_paid: bool,
    occurred_on: date | None = None,
) -> Any:
    """Write an `unexpected_cost` event. Doesn't mutate user state on
    its own — the user updates their plan (or doesn't) on the response
    page; the row is the audit trail."""
    from app import db
    from app.models.crisis_event import CrisisEvent

    event = CrisisEvent(
        user_id=user.id,
        event_type="unexpected_cost",
        cost_description=description,
        cost_amount=Decimal(str(amount)),
        cost_already_paid=already_paid,
        occurred_on=occurred_on,
    )
    db.session.add(event)
    db.session.commit()
    return event


def record_pause_request(user) -> Any:
    """Write a `pause_requested` event. The actual pause is manual via
    support email until Task 2.6 ships self-service. The row gives
    support a record so they can look it up when the user emails."""
    from app import db
    from app.models.crisis_event import CrisisEvent

    event = CrisisEvent(
        user_id=user.id,
        event_type="pause_requested",
    )
    db.session.add(event)
    db.session.commit()
    return event


def calculate_cost_absorption(user, cost_amount: float | Decimal) -> dict[str, Any]:
    """Run the existing can_i_afford planner helper for an unexpected
    cost. Returns the helper's dict with two extra keys:
      • show_signposting (bool) — true when cost > £500 OR > 50% of the
        monthly surplus, surfacing free-resource links alongside the
        plan adjustment.
      • surplus — the monthly surplus from the user's current plan,
        used by the response template.
    """
    from app.models.goal import Goal
    from app.services.planner_service import can_i_afford, generate_financial_plan

    amount = float(cost_amount)
    profile = user.profile_dict()
    goals = [
        g.to_dict()
        for g in Goal.query.filter_by(user_id=user.id, status="active")
        .order_by(Goal.priority_rank.asc()).all()
    ]
    plan = generate_financial_plan(profile, goals)

    if "error" in plan:
        return {
            "affordable": False,
            "amount": round(amount, 2),
            "message": plan["error"],
            "impact": "no_plan",
            "show_signposting": amount > 500,
            "surplus": 0,
        }

    result = can_i_afford(plan, "this cost", amount)
    surplus = float(plan.get("surplus") or 0)
    show_signposting = amount > 500 or (
        surplus > 0 and amount > surplus * 0.5
    )
    result["show_signposting"] = bool(show_signposting)
    result["surplus"] = round(surplus, 2)
    return result
