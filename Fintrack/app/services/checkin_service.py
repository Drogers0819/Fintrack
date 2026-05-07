"""
Check-in service — pure functions that decide check-in page state
beyond the simple in-window/out-of-window logic in _checkin_view_state.

The forgiveness flow (Block 2 Task 2.3) lives here. A user who missed
last month's check-in and got a reminder ladder fired at them lands
on /check-in feeling guilty. The forgiveness state acknowledges it
once, lets them file retroactively, and gets out of the way.

`get_forgiveness_target` is the gate. It returns the (year, month)
the user should retroactively file for, or None to let the existing
form/scheduled/complete state machine handle the page.
"""

from __future__ import annotations

import calendar
from datetime import date


# Inside this many days, a retroactive submission is acceptable. Beyond
# it, we refuse the POST even if the form was rendered — protects
# against a tab left open across cycles, and a clear cap on how much
# history the forgiveness flow will rewrite.
RETROACTIVE_WINDOW_DAYS = 60


def _previous_month(today: date) -> tuple[int, int]:
    """Return (year, month) of the calendar month before today."""
    if today.month == 1:
        return today.year - 1, 12
    return today.year, today.month - 1


def _in_standard_window(today: date) -> bool:
    """Inside the last 3 days of the month — the standard check-in
    window. Mirrors _checkin_view_state's window math so the two stay
    in lockstep."""
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day >= last_day - 2


def get_forgiveness_target(user, today: date | None = None) -> tuple[int, int] | None:
    """Return (year, month) the user should retroactively check in for,
    or None if the standard view-state should handle this request.

    Forgiveness applies when:
      1. We're outside the standard last-3-days window.
      2. The user got at least one reminder this cycle (i.e. they were
         actually nudged to check in and didn't).
      3. They have no CheckIn for the previous calendar month — and
         either their most recent CheckIn is older than that month, or
         they have no CheckIn at all and pay-day was >= 14 days ago.

    The flow only ever surfaces the **most recent** missed month. Older
    misses stay missed; the plan adapts forward, not backward through
    history. This is deliberate: deeper retroactive editing creates
    more cognitive load than retention payoff.
    """
    from app.models.checkin import CheckIn

    if today is None:
        today = date.today()

    if _in_standard_window(today):
        return None

    has_reminder = (
        getattr(user, "checkin_reminder_1_sent", None) is not None
        or getattr(user, "checkin_reminder_2_sent", None) is not None
        or getattr(user, "checkin_reminder_3_sent", None) is not None
    )
    if not has_reminder:
        return None

    prev_year, prev_month = _previous_month(today)

    # If the previous-month CheckIn already exists, the user already
    # filed it (perhaps via the standard window late in the month).
    # Forgiveness is for misses, not corrections — edit mode handles
    # that path.
    prev_checkin = CheckIn.query.filter_by(
        user_id=user.id, month=prev_month, year=prev_year,
    ).first()
    if prev_checkin is not None:
        return None

    most_recent = CheckIn.query.filter_by(
        user_id=user.id,
    ).order_by(CheckIn.year.desc(), CheckIn.month.desc()).first()

    if most_recent is None:
        # Brand-new-ish user with no check-in history. Only show
        # forgiveness if they were genuinely nudged a while ago — the
        # 14-day floor keeps "just signed up, not yet hit a window"
        # users out of the flow.
        anchor = getattr(user, "payday_notification_last_sent", None)
        if anchor is None:
            return None
        if (today - anchor).days < 14:
            return None
        return (prev_year, prev_month)

    # User has a check-in history. Forgiveness only triggers when the
    # latest entry is older than the previous calendar month — i.e.
    # they actually skipped the most recent cycle.
    most_recent_key = (most_recent.year, most_recent.month)
    prev_key = (prev_year, prev_month)
    if most_recent_key >= prev_key:
        return None

    return (prev_year, prev_month)


def is_within_retroactive_window(
    target_year: int,
    target_month: int,
    today: date | None = None,
) -> bool:
    """Reject submissions older than RETROACTIVE_WINDOW_DAYS. Used on
    POST to defend against stale forms left open across cycles."""
    if today is None:
        today = date.today()
    try:
        target_date = date(target_year, target_month, 1)
    except ValueError:
        return False
    days = (today - target_date).days
    return 0 <= days <= RETROACTIVE_WINDOW_DAYS
