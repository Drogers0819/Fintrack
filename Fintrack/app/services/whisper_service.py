"""
Claro Action Whisper Service

Zero API cost. Generates one actionable prompt per page load
based on the user's stage in their journey.

Priority order:
1. Post-onboarding standing order setup (days 1-7)
2. Pay day prompts
3. Pre-check-in nudge
4. Goal milestones
5. Life check-in prompt (mid-month)
6. General plan status
"""

from datetime import date, datetime
from dateutil.relativedelta import relativedelta


def generate_action_whisper(user, plan, goals):
    """
    Generate a single action whisper for the overview page.

    Args:
        user: User model instance
        plan: Plan dict from generate_financial_plan() or None
        goals: List of goal dicts

    Returns:
        dict with: message, action_label, action_url, icon, type
        or None if no whisper is appropriate
    """
    if not user.factfind_completed or not plan or "error" in plan:
        return None

    today = date.today()
    pots = plan.get("pots", [])
    active_pots = [p for p in pots if not p.get("completed") and p.get("monthly_amount", 0) > 0
                   and p.get("type") not in ("lifestyle", "buffer")]

    # Calculate days since signup
    days_since_signup = 0
    if user.created_at:
        days_since_signup = (today - user.created_at.date()).days

    # Check each whisper type in priority order
    whisper = None

    # 1. Post-onboarding: standing order setup (first 7 days)
    whisper = _standing_order_whisper(user, pots, active_pots, days_since_signup)
    if whisper:
        return whisper

    # 2. Pay day prompt
    whisper = _payday_whisper(user, plan, pots, today)
    if whisper:
        return whisper

    # 3. Pre-check-in nudge (2 days before month end)
    whisper = _checkin_whisper(today)
    if whisper:
        return whisper

    # 4. Goal milestones (50%, 75%, completed)
    whisper = _milestone_whisper(pots, plan)
    if whisper:
        return whisper

    # 5. Life check-in (mid-month, around 14th-16th)
    whisper = _life_checkin_whisper(today, days_since_signup, user)
    if whisper:
        return whisper

    # 6. Claro directed £X counter
    whisper = _directed_counter_whisper(user, plan)
    if whisper:
        return whisper

    # 7. Active debt position (LOW priority — informational)
    whisper = _debt_position_whisper(pots)
    if whisper:
        return whisper

    # 8. Default: plan status
    whisper = _default_whisper(plan, active_pots)
    if whisper:
        return whisper

    return None


# ─── WHISPER GENERATORS ───────────────────────────────────

def _standing_order_whisper(user, pots, active_pots, days_since_signup):
    """Days 1-7: Prompt user to set up standing orders for each pot."""
    if days_since_signup > 7 or not active_pots:
        return None

    income_day = user.income_day or 25
    pay_suffix = _ordinal(income_day)

    if days_since_signup <= 1:
        pot = active_pots[0]
        return {
            "message": f"First step: open your banking app and set up a standing order for \u00a3{pot['monthly_amount']:,.0f}/month to a \"{pot['name']}\" pot. Set it for the {pay_suffix}, the day after your pay lands.",
            "action_label": "I've done this",
            "action_url": None,
            "icon": "bank",
            "type": "setup"
        }

    elif days_since_signup <= 3 and len(active_pots) > 1:
        pot = active_pots[1]
        return {
            "message": f"Next: set up \u00a3{pot['monthly_amount']:,.0f}/month to your \"{pot['name']}\" pot. Two standing orders and your plan is running on autopilot.",
            "action_label": "Done",
            "action_url": None,
            "icon": "check-circle",
            "type": "setup"
        }

    elif days_since_signup <= 5:
        return {
            "message": "Check your bank app. Have your standing orders gone through? Once they're running, your plan executes itself every month.",
            "action_label": None,
            "action_url": None,
            "icon": "search",
            "type": "setup"
        }

    elif days_since_signup <= 7:
        total_allocated = sum(p["monthly_amount"] for p in pots)
        return {
            "message": f"You're all set. \u00a3{total_allocated:,.0f}/month is now directed across your goals. Your next check-in will be at the end of the month.",
            "action_label": "View my plan",
            "action_url": "/plan",
            "icon": "target",
            "type": "setup_complete"
        }

    return None


def _payday_whisper(user, plan, pots, today):
    """Show allocation breakdown on pay day."""
    income_day = user.income_day or 25

    if today.day not in (income_day, income_day + 1 if income_day < 28 else income_day):
        return None

    surplus = plan.get("surplus", 0)
    funded_pots = [p for p in pots if p.get("monthly_amount", 0) > 0
                   and not p.get("completed")
                   and p.get("type") not in ("lifestyle", "buffer")]

    if not funded_pots:
        return None

    allocations = []
    for pot in funded_pots[:3]:
        allocations.append(f"\u00a3{pot['monthly_amount']:,.0f} to {pot['name']}")

    alloc_text = ", ".join(allocations)
    if len(funded_pots) > 3:
        alloc_text += f" + {len(funded_pots) - 3} more"

    return {
        "message": f"It's pay day. Here's where your \u00a3{surplus:,.0f} surplus goes: {alloc_text}.",
        "action_label": "View full plan",
        "action_url": "/plan",
        "icon": "trending-up",
        "type": "payday"
    }


def _checkin_whisper(today):
    """Nudge 2-3 days before month end."""
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = days_in_month - today.day

    if days_left > 3 or days_left < 0:
        return None

    if days_left == 0:
        return {
            "message": "It's the last day of the month. Time for your monthly check-in. How much did you actually put toward each goal?",
            "action_label": "Start check-in",
            "action_url": "/check-in",
            "icon": "clipboard-list",
            "type": "checkin"
        }
    else:
        return {
            "message": f"Your monthly check-in is due in {days_left} day{'s' if days_left > 1 else ''}. Have your bank app handy, it takes 2 minutes.",
            "action_label": "Do it now",
            "action_url": "/check-in",
            "icon": "clipboard-list",
            "type": "checkin"
        }


def _milestone_whisper(pots, plan):
    """Celebrate goal milestones."""
    for pot in pots:
        if pot.get("completed"):
            continue

        target = pot.get("target", 0)
        current = pot.get("current", 0)
        name = pot.get("name", "")
        pot_type = pot.get("type", "")

        if pot_type in ("lifestyle", "buffer") or target <= 0:
            continue

        progress = current / target

        if progress >= 1.0:
            next_pot = _find_next_pot(pots, pot)
            redirect_msg = ""
            if next_pot:
                redirect_msg = f" That \u00a3{pot.get('monthly_amount', 0):,.0f}/month now goes toward your {next_pot['name']}."

            return {
                "message": f"You did it! {name} is fully funded.{redirect_msg}",
                "action_label": "View goals",
                "action_url": "/my-goals",
                "icon": "award",
                "type": "milestone"
            }

        elif progress >= 0.75:
            months = pot.get("months_to_target")
            time_msg = f" ~{months} month{'s' if months != 1 else ''} to go." if months else ""
            return {
                "message": f"Your {name} is 75% funded. \u00a3{current:,.0f} of \u00a3{target:,.0f}.{time_msg} You're in the home stretch.",
                "action_label": None,
                "action_url": None,
                "icon": "zap",
                "type": "milestone"
            }

        elif progress >= 0.5:
            months = pot.get("months_to_target")
            time_msg = f" At this pace, it completes in ~{months} month{'s' if months != 1 else ''}." if months else ""
            return {
                "message": f"Halfway there. Your {name} is 50% funded. \u00a3{current:,.0f} of \u00a3{target:,.0f}.{time_msg}",
                "action_label": None,
                "action_url": None,
                "icon": "star",
                "type": "milestone"
            }

    return None


def _life_checkin_whisper(today, days_since_signup, user=None):
    """Mid-month life check-in prompt."""
    if days_since_signup < 14:
        return None

    # Don't show if already done this month
    if user and user.last_life_checkin:
        if user.last_life_checkin.month == today.month and user.last_life_checkin.year == today.year:
            return None

    if 13 <= today.day <= 16:
        return {
            "message": "Anything come up this month we should know about? A birthday, an unexpected bill, or a change at work? Quick updates keep your plan accurate.",
            "action_label": "Quick check-in",
            "action_url": "/life-checkin",
            "icon": "message-circle",
            "type": "life_checkin"
        }

    return None


def _directed_counter_whisper(user, plan):
    """Show total allocated since signup."""
    if not user.created_at:
        return None

    today = date.today()
    months_active = max(1, (today.year - user.created_at.year) * 12 + today.month - user.created_at.month)

    if months_active < 2:
        return None

    surplus = plan.get("surplus", 0)
    total_directed = round(surplus * months_active, 0)

    if total_directed <= 0:
        return None

    return {
        "message": f"Following your plan has directed \u00a3{total_directed:,.0f} toward your goals over {months_active} months. That's \u00a3{surplus:,.0f}/month working for your future.",
        "action_label": None,
        "action_url": None,
        "icon": "bar-chart-2",
        "type": "counter"
    }


_DEBT_KEYWORDS = ("credit card", "overdraft", "loan", "pay off", "debt")


def _is_debt_pot(pot):
    name_low = (pot.get("name") or "").lower()
    return pot.get("type") == "debt" or any(k in name_low for k in _DEBT_KEYWORDS)


def _debt_position_whisper(pots):
    """Acknowledge active debt and frame the redirect once cleared."""
    debt_pots = [
        p for p in pots
        if _is_debt_pot(p) and not p.get("completed") and p.get("monthly_amount", 0) > 0
    ]
    if not debt_pots:
        return None

    debt_total = sum(
        max(float(p.get("target") or 0) - float(p.get("current") or 0), 0)
        for p in debt_pots
    )
    debt_monthly = sum(float(p.get("monthly_amount") or 0) for p in debt_pots)
    if debt_total <= 0 or debt_monthly <= 0:
        return None

    return {
        "message": (
            f"You're clearing £{debt_total:,.0f} in debt. Your plan handles this first — "
            f"£{debt_monthly:,.0f}/month goes to clearing it, then that money shifts to your other goals."
        ),
        "action_label": "View plan",
        "action_url": "/plan",
        "icon": "credit-card",
        "type": "debt_position"
    }


def _default_whisper(plan, active_pots):
    """Default: show closest-to-completion goal."""
    if not active_pots:
        return None

    closest = None
    closest_pct = 0

    for pot in active_pots:
        target = pot.get("target", 0)
        current = pot.get("current", 0)
        if target > 0:
            pct = current / target
            if pct > closest_pct and pct < 1.0:
                closest = pot
                closest_pct = pct

    if closest:
        months = closest.get("months_to_target")
        time_msg = f" ~{months} month{'s' if months != 1 else ''} to go." if months else ""
        return {
            "message": f"Your {closest['name']} is {closest_pct:.0%} funded.{time_msg} Your plan is working.",
            "action_label": "View plan",
            "action_url": "/plan",
            "icon": "bar-chart-2",
            "type": "status"
        }

    total = sum(p["monthly_amount"] for p in active_pots)
    return {
        "message": f"Your plan directs \u00a3{total:,.0f}/month across {len(active_pots)} goals. Set up your standing orders and it runs on autopilot.",
        "action_label": "View plan",
        "action_url": "/plan",
        "icon": "target",
        "type": "status"
    }


# ─── HELPERS ──────────────────────────────────────────────

def _find_next_pot(pots, completed_pot):
    """Find the next pot that would receive money after a pot completes."""
    active = [p for p in pots if not p.get("completed")
              and p.get("monthly_amount", 0) > 0
              and p.get("type") not in ("lifestyle", "buffer")
              and p.get("name") != completed_pot.get("name")]
    return active[0] if active else None


def _ordinal(n):
    """Return ordinal string for a number: 1st, 2nd, 3rd, etc."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ─── TODAY'S WHISPER ────────────────────────────────────────
#
# A single calm sentence shown at the top of the overview right rail.
# Distinct from generate_action_whisper above, which returns a
# structured action dict with a CTA button. Today's whisper is just
# a reflection: priority-ordered, template-driven (zero API cost),
# deterministic, instant.
#
# Adding a whisper: append a function that returns the rendered
# string when the condition matches, None otherwise. Order in
# WHISPER_LIBRARY = priority. Fallback at the end always wins so the
# caller is guaranteed a non-empty string.

import calendar
import logging
from datetime import datetime, timedelta

_whisper_logger = logging.getLogger(__name__)


def _next_window_start(today):
    """The check-in window opens on the last 3 days of each calendar
    month. Return the first day of the next window, used to fill the
    'nothing required until X' whisper."""
    last_day = calendar.monthrange(today.year, today.month)[1]
    window_start = date(today.year, today.month, last_day - 2)
    if today < window_start:
        return window_start
    if today.month == 12:
        next_month, next_year = 1, today.year + 1
    else:
        next_month, next_year = today.month + 1, today.year
    next_last_day = calendar.monthrange(next_year, next_month)[1]
    return date(next_year, next_month, next_last_day - 2)


def _factfind_pending_whisper(user):
    if getattr(user, "factfind_completed", False):
        return None
    return (
        "Tell Claro about your money in four short steps. The plan "
        "unlocks the moment your profile is in."
    )


def _subscription_paused_whisper(user):
    resume = getattr(user, "subscription_paused_until", None)
    if resume is None:
        return None
    when = f"{resume.day} {resume.strftime('%B')}"
    return (
        f"Your subscription is paused. Billing resumes on {when}. "
        f"Your plan and goals stay where they are."
    )


def _survival_mode_whisper(user):
    if not getattr(user, "survival_mode_active", False):
        return None
    return (
        "Survival mode is on. The plan is focused on essentials only. "
        "When things change, switch back from settings and the goals resume."
    )


def _no_goals_yet_whisper(user):
    """User has finished factfind but hasn't picked a goal yet."""
    from app.models.goal import Goal
    if not getattr(user, "factfind_completed", False):
        return None
    if Goal.query.filter_by(user_id=user.id, status="active").count() > 0:
        return None
    return (
        "Your plan is ready. Pick a goal and Claro will work out what "
        "each month moves you closer to it."
    )


def _credit_card_whisper(user):
    """Their soonest-completing credit-card debt clears in N months."""
    info = user.get_credit_card_goal_completing_soon()
    if info is None:
        return None
    months_left, monthly_amount = info
    months = max(1, int(round(months_left)))
    amount = int(round(monthly_amount))
    return (
        f"Your credit card clears in roughly {months} "
        f"month{'s' if months != 1 else ''}. After that, that "
        f"£{amount} per month goes automatically toward your next goal."
    )


def _ahead_of_target_whisper(user):
    streak = user.get_savings_streak_months()
    if streak < 2:
        return None
    return (
        f"You've been ahead of your savings target for {streak} "
        f"month{'s' if streak != 1 else ''} running. Worth noticing."
    )


def _recent_checkin_whisper(user):
    """Surface the next reminder window so the user can stop thinking
    about it."""
    if not user.has_completed_recent_checkin():
        return None
    today = date.today()
    next_window_start = _next_window_start(today)
    next_date = f"{next_window_start.day} {next_window_start.strftime('%B')}"
    return (
        f"Your check-in this month told the plan everything it needs. "
        f"Nothing required from you until {next_date}."
    )


def _trial_active_whisper(user):
    if (getattr(user, "subscription_status", "") or "") != "trialing":
        return None
    trial_ends = getattr(user, "trial_ends_at", None)
    if trial_ends is None:
        return None
    days_left = (trial_ends - datetime.utcnow()).days
    if days_left < 0 or days_left > 14:
        return None
    return (
        f"You're {days_left} day{'s' if days_left != 1 else ''} into your "
        f"trial. The plan is live; everything you change shapes it in real time."
    )


WHISPER_LIBRARY = [
    _factfind_pending_whisper,
    _subscription_paused_whisper,
    _survival_mode_whisper,
    _no_goals_yet_whisper,
    _credit_card_whisper,
    _ahead_of_target_whisper,
    _recent_checkin_whisper,
    _trial_active_whisper,
]


_WHISPER_FALLBACK = None


def get_todays_whisper(user):
    """Walk the library in priority order; return the first whisper
    whose condition matches. Fallback for early-stage users.

    Defensive: any helper that raises is logged and skipped so a single
    flaky data shape can't blank the entire whisper card."""
    if user is None:
        return _WHISPER_FALLBACK

    for whisper_fn in WHISPER_LIBRARY:
        try:
            result = whisper_fn(user)
        except Exception:  # noqa: BLE001
            _whisper_logger.exception(
                "Whisper helper %s raised for user %s",
                whisper_fn.__name__, getattr(user, "id", "?"),
            )
            continue
        if result:
            return result

    return _WHISPER_FALLBACK