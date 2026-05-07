"""
Hardship subscription pause — Block 2 Task 2.6.

The first version of self-service pause for users in financial
distress. Uses Stripe's `pause_collection` mechanism: the
subscription stays active (the user keeps app access) but Stripe
stops collecting payment. Auto-resumes at the user-selected
resumes_at timestamp via webhook.

Discipline
----------
- Every Stripe call is wrapped. We never propagate Stripe errors to
  the route — the user sees "couldn't pause right now, try again".
- Every state mutation writes a SubscriptionEvent row. The audit
  trail answers "why am I paused" or "why was I charged" without
  trawling Stripe.
- Webhook handler is idempotent: SubscriptionEvent.stripe_event_id
  has a unique constraint, duplicate deliveries hit IntegrityError
  and we treat that as "already processed".
- Eligibility gate covers four real abuse / safety cases (no
  subscription, trial, dunning, recently-paused). The 6-month rate
  limit is calibrated to discourage rolling pauses while leaving
  room for a second pause in genuine extended hardship.
- Test mode discipline: Stripe API calls are mocked end-to-end in
  the test suite via patch("stripe.Subscription.modify", ...). No
  real network traffic from tests.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# Hard limits and rate limits.
ALLOWED_DURATIONS_DAYS: tuple[int, ...] = (30, 60)
PAUSE_RATE_LIMIT_DAYS = 180  # ~6 months between pauses
ACTIVE_PAID_TIERS: frozenset[str] = frozenset({"pro", "pro_plus", "joint"})
ACTIVE_PAID_STATUSES: frozenset[str] = frozenset({"active"})


def calculate_resume_date(start_date: datetime, duration_days: int) -> datetime:
    """End of the last day of the pause, in UTC. We resume at 23:59:59
    on the final day so the user gets the full duration they picked
    rather than something off-by-eight-hours from a midday submission."""
    end_day = (start_date + timedelta(days=duration_days)).date()
    return datetime(end_day.year, end_day.month, end_day.day, 23, 59, 59)


def is_pause_eligible(user) -> tuple[bool, str | None]:
    """Returns (eligible, reason_if_not).

    Reasons in priority order:
      1. no_subscription — no Stripe subscription on file or canceled
      2. free_tier — explicitly on the free tier
      3. trial — trialing (we don't pause a trial; the user can
         simply not enter a card before trial ends)
      4. in_dunning — subscription has a payment problem; that's a
         different conversation (handled in billing portal)
      5. already_paused — subscription is currently paused
      6. recently_paused — paused in the last 6 months
    """
    if not user.stripe_subscription_id or user.subscription_status == "canceled":
        return False, "no_subscription"
    if (user.subscription_tier or "free") == "free":
        return False, "free_tier"
    if user.subscription_status == "trialing":
        return False, "trial"
    if user.subscription_status == "past_due":
        return False, "in_dunning"
    if user.subscription_paused_until is not None:
        return False, "already_paused"

    last_paused = user.last_pause_started_at
    if last_paused is not None:
        days_since = (datetime.utcnow() - last_paused).days
        if days_since < PAUSE_RATE_LIMIT_DAYS:
            return False, "recently_paused"

    if (user.subscription_tier or "free") not in ACTIVE_PAID_TIERS:
        return False, "no_subscription"
    if (user.subscription_status or "") not in ACTIVE_PAID_STATUSES:
        return False, "no_subscription"

    return True, None


def next_pause_available_date(user) -> datetime | None:
    """For the recently-paused ineligible page: when can the user pause
    again. Returns None if they have no last_pause_started_at."""
    if user.last_pause_started_at is None:
        return None
    return user.last_pause_started_at + timedelta(days=PAUSE_RATE_LIMIT_DAYS)


def initiate_pause(user, duration_days: int) -> dict[str, Any]:
    """Pause the user's Stripe subscription for `duration_days`. Writes
    a SubscriptionEvent on success or failure. Never raises.

    Returns a dict:
      {success: bool, error: str | None, resume_date: datetime | None}
    """
    from app import db
    from app.models.subscription_event import SubscriptionEvent
    from app.services.analytics_service import track_event

    if duration_days not in ALLOWED_DURATIONS_DAYS:
        return {
            "success": False,
            "error": "invalid_duration",
            "resume_date": None,
        }

    eligible, reason = is_pause_eligible(user)
    if not eligible:
        return {
            "success": False,
            "error": reason or "ineligible",
            "resume_date": None,
        }

    started_at = datetime.utcnow()
    resume_date = calculate_resume_date(started_at, duration_days)
    resume_unix = int(resume_date.timestamp())

    try:
        import stripe
        from app.services.stripe_service import init_stripe
        if not init_stripe():
            logger.warning("Stripe not configured for pause user=%s", user.id)
            _write_event(
                db, SubscriptionEvent,
                user_id=user.id,
                event_type="pause_failed",
                stripe_subscription_id=user.stripe_subscription_id,
                metadata_json=json.dumps({"reason": "stripe_not_configured"}),
            )
            return {
                "success": False,
                "error": "stripe_unavailable",
                "resume_date": None,
            }

        stripe.Subscription.modify(
            user.stripe_subscription_id,
            pause_collection={
                "behavior": "void",
                "resumes_at": resume_unix,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stripe pause failed for user %s", user.id)
        _write_event(
            db, SubscriptionEvent,
            user_id=user.id,
            event_type="pause_failed",
            stripe_subscription_id=user.stripe_subscription_id,
            metadata_json=json.dumps({"reason": "stripe_error", "detail": str(exc)[:200]}),
        )
        return {
            "success": False,
            "error": "stripe_error",
            "resume_date": None,
        }

    user.subscription_paused_until = resume_date
    user.last_pause_started_at = started_at

    _write_event(
        db, SubscriptionEvent,
        user_id=user.id,
        event_type="paused",
        stripe_subscription_id=user.stripe_subscription_id,
        pause_duration_days=duration_days,
        pause_started_at=started_at,
        pause_ends_at=resume_date,
    )
    db.session.commit()

    track_event(user.id, "subscription_paused", {
        "duration_days": duration_days,
        "resumes_at": resume_date.isoformat(),
    })

    return {
        "success": True,
        "error": None,
        "resume_date": resume_date,
    }


def manually_resume_pause(user) -> dict[str, Any]:
    """Clear the pause early. Writes a SubscriptionEvent. Never raises.

    Returns {success: bool, error: str | None}.
    """
    from app import db
    from app.models.subscription_event import SubscriptionEvent
    from app.services.analytics_service import track_event

    if user.subscription_paused_until is None:
        return {"success": False, "error": "not_paused"}
    if not user.stripe_subscription_id:
        return {"success": False, "error": "no_subscription"}

    try:
        import stripe
        from app.services.stripe_service import init_stripe
        if not init_stripe():
            logger.warning("Stripe not configured for resume user=%s", user.id)
            return {"success": False, "error": "stripe_unavailable"}

        # Empty string is the documented way to clear pause_collection
        # via the Python SDK.
        stripe.Subscription.modify(
            user.stripe_subscription_id,
            pause_collection="",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Stripe manual resume failed for user %s", user.id)
        return {"success": False, "error": "stripe_error"}

    user.subscription_paused_until = None

    _write_event(
        db, SubscriptionEvent,
        user_id=user.id,
        event_type="resumed_manual",
        stripe_subscription_id=user.stripe_subscription_id,
    )
    db.session.commit()

    track_event(user.id, "subscription_resumed", {"reason": "manual"})

    return {"success": True, "error": None}


def handle_scheduled_resume_webhook(user, stripe_event_id: str) -> bool:
    """Called from the webhook dispatcher when Stripe auto-resumes the
    subscription at the end of the pause. Idempotent: a duplicate
    delivery (same stripe_event_id) is silently swallowed via the
    SubscriptionEvent unique constraint.

    Returns True if state was updated, False if already processed or
    if there's nothing to do.
    """
    from app import db
    from app.models.subscription_event import SubscriptionEvent
    from app.services.analytics_service import track_event
    from sqlalchemy.exc import IntegrityError

    # Idempotency check: if we've already written an event for this
    # delivery, do nothing. The unique constraint catches races, but
    # an explicit check avoids hitting the DB on the happy path.
    if stripe_event_id:
        existing = SubscriptionEvent.query.filter_by(
            stripe_event_id=stripe_event_id,
        ).first()
        if existing is not None:
            return False

    if user.subscription_paused_until is None:
        # Nothing to clear; webhook arrived for a user who's already
        # been resumed (manually, perhaps). Still record the event so
        # the audit trail is consistent.
        try:
            db.session.add(SubscriptionEvent(
                user_id=user.id,
                event_type="resumed_scheduled",
                stripe_subscription_id=user.stripe_subscription_id,
                stripe_event_id=stripe_event_id,
                metadata_json=json.dumps({"note": "user_already_resumed"}),
            ))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return False

    user.subscription_paused_until = None
    try:
        db.session.add(SubscriptionEvent(
            user_id=user.id,
            event_type="resumed_scheduled",
            stripe_subscription_id=user.stripe_subscription_id,
            stripe_event_id=stripe_event_id,
        ))
        db.session.commit()
    except IntegrityError:
        # Race: parallel webhook delivery wrote it first. Roll back
        # and bail without re-mutating the user.
        db.session.rollback()
        return False

    track_event(user.id, "subscription_resumed", {"reason": "scheduled"})
    return True


# ─── Internal ────────────────────────────────────────────────


def _write_event(db, SubscriptionEvent, **fields):
    """Helper to write a SubscriptionEvent row. Caller is responsible
    for the surrounding commit (we batch with the user-state update so
    the row and the flag flip stay consistent)."""
    db.session.add(SubscriptionEvent(**fields))
