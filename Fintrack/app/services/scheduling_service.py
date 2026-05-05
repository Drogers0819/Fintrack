"""
Scheduling service — home for cron-driven logic in Block 2.

Block 2 entrypoints:
  • process_payday_notifications(today=None)
    Called daily by the /cron/payday-notifications endpoint.
    Finds users whose effective pay day is today, sends them the
    pay-day notification email, marks them notified for this month.

Idempotency
-----------
A user is only ever notified once per calendar month. Re-running the
cron on the same day (or even multiple times) is safe: the
payday_notification_last_sent column anchors the per-user "already
notified for this month" decision.

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
