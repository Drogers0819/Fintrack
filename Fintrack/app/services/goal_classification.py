"""
Goal classification helpers.

A small shared module so net_worth_service, spending_breakdown_service,
and any future service can ask "is this a debt-payoff goal?" without
sibling imports between unrelated service modules.

Debt detection is by name heuristic because the Goal.type column is
not reliably populated for debt goals — the onboarding goal-chips
handler writes every goal as type="savings_target" regardless of
purpose, and debt goals are recognised everywhere by the keywords in
their names ("credit card", "loan", "overdraft", "pay off").
"""

from __future__ import annotations


_DEBT_KEYWORDS = ("credit card", "loan", "overdraft", "pay off")


def _is_debt_goal_name(name: str | None) -> bool:
    """True when the goal's name marks it as a debt-payoff goal.

    Underscore prefix preserved from the original implementation so
    callers in the service layer keep the same import shape. The
    function is safe to call with None.
    """
    if not name:
        return False
    lower = name.lower()
    return any(keyword in lower for keyword in _DEBT_KEYWORDS)
