"""
Scheduling service — home for cron-driven logic in Block 2.

Block 2 entrypoints:
  • process_payday_notifications(today=None)
    Called daily by the /cron/payday-notifications endpoint.
    Finds users whose effective pay day is today, sends them the
    pay-day notification email, marks them notified for this month.

  • process_checkin_reminders(today=None)
    Called daily by the /cron/checkin-reminders endpoint.
    For each user who got a pay-day notification 3, 7, or 14 days ago
    and hasn't filed their check-in yet, sends the corresponding
    reminder. Each reminder is at most once per pay-day cycle.

Idempotency
-----------
Pay-day: a user is only ever notified once per calendar month. The
payday_notification_last_sent column anchors the decision.

Reminders: each of the three reminders is at most once per pay-day
cycle. The cycle anchor is payday_notification_last_sent itself, and
checkin_reminder_{1,2,3}_sent gate per-reminder idempotency. When a
new pay-day notification fires, the three reminder fields are reset
to None so the next cycle's ladder runs fresh.

Edge case: a user whose income_day is 31 in a 30-day month (or 28-day
February) gets notified on the last day of that month rather than
being silently skipped — a user who set 31 wants "end of month",
not "skip this month".

Scale
-----
At <5,000 users this completes in well under 30 seconds even with
the worst-case 100-user pay day (10 emails/sec rate-limit on Resend
free tier means ~10 seconds of sleeping if we hit that ceiling).
"""

from __future__ import annotations

import calendar
import logging
import time
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)


# Resend free tier permits ~10 emails/sec. Stay safely under it once the
# batch grows large; tiny batches (<= threshold) skip the sleep entirely.
_RATE_LIMIT_BATCH_THRESHOLD = 100
_RATE_LIMIT_SLEEP_SECONDS = 0.1


def _effective_payday(user_income_day: int, today: date) -> int:
    """Cap the user's pay day at the last day of the current month so a
    user with income_day=31 still gets notified in February."""
    last_day = calendar.monthrange(today.year, today.month)[1]
    return min(user_income_day, last_day)


def _already_notified_this_month(user, today: date) -> bool:
    last_sent = getattr(user, "payday_notification_last_sent", None)
    if last_sent is None:
        return False
    return last_sent.year == today.year and last_sent.month == today.month


def _checkin_already_done(user, today: date) -> bool:
    """The check-in shown on a given calendar day covers the previous
    month (see _checkin_view_state in page_routes.py). If the user has
    already filed that check-in, we don't badger them with a pay-day
    nudge."""
    from app.models.checkin import CheckIn

    if today.month == 1:
        target_month, target_year = 12, today.year - 1
    else:
        target_month, target_year = today.month - 1, today.year

    return CheckIn.query.filter_by(
        user_id=user.id,
        month=target_month,
        year=target_year,
    ).first() is not None


def process_payday_notifications(today: date | None = None) -> dict[str, Any]:
    """Run one pay-day notification pass.

    Returns a summary dict:
      {users_notified: int, users_skipped: int, errors: list[str]}

    Never raises. Per-user failures are caught, logged with the user_id,
    and surfaced in the errors list. The caller (cron route) returns 200
    even when the errors list is non-empty — that's by design so a single
    bad row doesn't lock out the rest of the run.
    """
    from app import db
    from app.models.user import User
    from app.services.analytics_service import track_event
    from app.services.email_service import send_email
    from flask import url_for

    if today is None:
        today = date.today()

    summary: dict[str, Any] = {
        "users_notified": 0,
        "users_skipped": 0,
        "errors": [],
    }

    try:
        candidates = User.query.filter(User.income_day.isnot(None)).all()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load users for pay-day cron: %s", exc)
        summary["errors"].append(f"user_query_failed: {exc!s}")
        return summary

    # Resolve the check-in URL once — Flask url_for is cheap but reading
    # it inside a loop is wasteful and the value never varies per user.
    try:
        checkin_url = url_for("pages.checkin", source="payday", _external=True)
    except Exception:  # noqa: BLE001 — url_for needs a request context
        checkin_url = "/check-in?source=payday"

    notified_in_batch = 0

    for user in candidates:
        try:
            if user.income_day is None:
                summary["users_skipped"] += 1
                continue

            payday = _effective_payday(int(user.income_day), today)
            if today.day != payday:
                summary["users_skipped"] += 1
                continue

            if _already_notified_this_month(user, today):
                summary["users_skipped"] += 1
                continue

            if _checkin_already_done(user, today):
                summary["users_skipped"] += 1
                continue

            first_name = (user.name or "").split()[0] if user.name else "there"

            sent_ok = send_email(
                to_email=user.email,
                subject="Pay day. Time for your Claro check-in.",
                template_name="payday_notification",
                template_context={
                    "first_name": first_name,
                    "checkin_url": checkin_url,
                },
            )

            if not sent_ok:
                # Send returned False (no API key, render fail, SDK error).
                # Don't mark the user as notified — we want a retry on the
                # next cron tick if the underlying issue clears.
                summary["users_skipped"] += 1
                summary["errors"].append(f"send_failed_user_{user.id}")
                logger.warning("Pay-day send failed for user %s", user.id)
                continue

            user.payday_notification_last_sent = today
            # Reset the reminder ladder so the next cycle runs fresh.
            # Without this, a stamp from last cycle's day-7 reminder would
            # block reminder 2 from ever firing again.
            user.checkin_reminder_1_sent = None
            user.checkin_reminder_2_sent = None
            user.checkin_reminder_3_sent = None
            db.session.commit()

            track_event(user.id, "payday_notification_sent", {
                "payday_day": int(user.income_day),
                "effective_day": payday,
            })

            summary["users_notified"] += 1
            notified_in_batch += 1

            if notified_in_batch > _RATE_LIMIT_BATCH_THRESHOLD:
                time.sleep(_RATE_LIMIT_SLEEP_SECONDS)

        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            logger.exception("Pay-day notification crashed for user %s", user.id)
            summary["errors"].append(f"user_{user.id}: {exc!s}")
            summary["users_skipped"] += 1

    logger.info(
        "Pay-day cron complete: notified=%d skipped=%d errors=%d",
        summary["users_notified"], summary["users_skipped"], len(summary["errors"]),
    )
    return summary


# ─── Missed check-in reminder ladder ─────────────────────────────────
#
# Three reminders fire at decreasing-urgency intervals after a missed
# check-in. The ladder is calibrated for warmth and patience: each
# reminder is softer than the last, and at day +14 we stop entirely.
# Re-engaging late is fine; nagging drives churn faster than silence.

_REMINDER_SCHEDULE: tuple[tuple[int, int], ...] = (
    # (days_since_payday, reminder_number) — ordered for deterministic
    # output in the per-reminder summary breakdown.
    (3, 1),
    (7, 2),
    (14, 3),
)

_REMINDER_TEMPLATES: dict[int, tuple[str, str]] = {
    # reminder_number → (template_name, subject)
    1: ("checkin_reminder_1", "Quick nudge for your check-in"),
    2: ("checkin_reminder_2", "Your plan is still here when you are"),
    3: ("checkin_reminder_3", "We will stop here"),
}

_REMINDER_FIELD: dict[int, str] = {
    1: "checkin_reminder_1_sent",
    2: "checkin_reminder_2_sent",
    3: "checkin_reminder_3_sent",
}


def _reminder_already_sent(user, reminder_number: int) -> bool:
    return getattr(user, _REMINDER_FIELD[reminder_number], None) is not None


def process_checkin_reminders(today: date | None = None) -> dict[str, Any]:
    """Run one missed-check-in reminder pass.

    For each user with payday_notification_last_sent set, calculate
    days since pay-day. If days_since matches one of the ladder rungs
    (3, 7, 14) and the corresponding reminder hasn't been sent yet
    this cycle, send it — unless the user has already filed the
    relevant check-in (in which case the ladder stops immediately).

    Returns:
        {users_notified, users_skipped, errors, reminder_breakdown}

    Never raises. Per-user failures are caught, logged with the user_id,
    and surfaced in the errors list. The caller (cron route) returns 200
    even when the errors list is non-empty.
    """
    from app import db
    from app.models.user import User
    from app.services.analytics_service import track_event
    from app.services.email_service import send_email
    from flask import url_for

    if today is None:
        today = date.today()

    summary: dict[str, Any] = {
        "users_notified": 0,
        "users_skipped": 0,
        "errors": [],
        "reminder_breakdown": {1: 0, 2: 0, 3: 0},
    }

    try:
        candidates = User.query.filter(
            User.payday_notification_last_sent.isnot(None)
        ).all()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to load users for reminder cron: %s", exc)
        summary["errors"].append(f"user_query_failed: {exc!s}")
        return summary

    try:
        checkin_url = url_for("pages.checkin", source="reminder", _external=True)
    except Exception:  # noqa: BLE001 — url_for needs a request context
        checkin_url = "/check-in?source=reminder"

    notified_in_batch = 0

    for user in candidates:
        try:
            anchor = user.payday_notification_last_sent
            if anchor is None:
                summary["users_skipped"] += 1
                continue

            days_since = (today - anchor).days

            # Match this run to at most one ladder rung.
            reminder_number: int | None = None
            for rung_days, rung_number in _REMINDER_SCHEDULE:
                if days_since == rung_days:
                    reminder_number = rung_number
                    break

            if reminder_number is None:
                summary["users_skipped"] += 1
                continue

            if _reminder_already_sent(user, reminder_number):
                summary["users_skipped"] += 1
                continue

            # The ladder stops the moment the user files their check-in.
            # Reuse the same target-month logic the pay-day notification
            # uses: a reminder that fires May 18 is asking about the
            # April check-in (covered by the May cycle).
            if _checkin_already_done(user, today):
                summary["users_skipped"] += 1
                continue

            first_name = (user.name or "").split()[0] if user.name else "there"
            template_name, subject = _REMINDER_TEMPLATES[reminder_number]

            sent_ok = send_email(
                to_email=user.email,
                subject=subject,
                template_name=template_name,
                template_context={
                    "first_name": first_name,
                    "checkin_url": checkin_url,
                },
            )

            if not sent_ok:
                # Don't stamp the reminder — we want the next cron run
                # to retry on the same day if the underlying issue
                # clears within the day_since window.
                summary["users_skipped"] += 1
                summary["errors"].append(f"send_failed_user_{user.id}")
                logger.warning(
                    "Reminder %d send failed for user %s",
                    reminder_number, user.id,
                )
                continue

            setattr(user, _REMINDER_FIELD[reminder_number], today)
            db.session.commit()

            track_event(user.id, "checkin_reminder_sent", {
                "reminder_number": reminder_number,
                "days_since_payday": days_since,
            })

            summary["users_notified"] += 1
            summary["reminder_breakdown"][reminder_number] += 1
            notified_in_batch += 1

            if notified_in_batch > _RATE_LIMIT_BATCH_THRESHOLD:
                time.sleep(_RATE_LIMIT_SLEEP_SECONDS)

        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            logger.exception("Reminder cron crashed for user %s", user.id)
            summary["errors"].append(f"user_{user.id}: {exc!s}")
            summary["users_skipped"] += 1

    logger.info(
        "Reminder cron complete: notified=%d skipped=%d errors=%d breakdown=%s",
        summary["users_notified"], summary["users_skipped"],
        len(summary["errors"]), summary["reminder_breakdown"],
    )
    return summary
