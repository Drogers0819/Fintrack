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


# Keyword → CSS-variable token. Same mapping the overview goal_visual
# macro and goal progress bars use, kept here as the single source of
# truth so the route can build (name, css_var) pairs for the plan
# whisper goal-colour dots without duplicating the keyword logic.
_GOAL_COLOUR_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("credit card", "loan", "overdraft", "pay off", "debt"), "--goal-stroke-debt"),
    (("house", "deposit", "mortgage", "home"), "--goal-stroke-house"),
    (("emergency", "safety", "rainy"), "--goal-stroke-emergency"),
    (("wedding", "baby", "family", "ring"), "--goal-stroke-wedding"),
    (("car", "vehicle"), "--goal-stroke-car"),
    (("holiday", "travel", "trip", "vacation"), "--goal-stroke-holiday"),
)


def goal_colour_token(name: str | None) -> str:
    """CSS-variable name for the colour associated with a goal's name.

    Returns e.g. ``"--goal-stroke-car"``. Falls back to the Roman Gold
    default for custom goal names that don't match a keyword. Callers
    embed this in inline styles as ``var(<token>)``.
    """
    if not name:
        return "--roman-gold"
    lower = name.lower()
    for keywords, token in _GOAL_COLOUR_RULES:
        if any(keyword in lower for keyword in keywords):
            return token
    return "--roman-gold"
