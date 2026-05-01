"""
Account deletion service — UK GDPR Article 17 (right to erasure).

User-initiated deletion is irreversible and immediate. Once the request is
confirmed in the UI, this module:

  1. Cancels any active Stripe subscription (immediate, not at period end).
  2. Fires a PostHog `account_deleted` event before the row is removed,
     so the user_id still resolves in PostHog's identify table at fire time.
  3. Deletes the User row. Database-level ON DELETE CASCADE removes related
     records on Postgres; SQLAlchemy ORM-level cascade handles SQLite dev.
  4. Logs user_id + reason. Never logs email or other PII.

Stripe failures are caught and logged but do not abort the deletion —
data erasure is the GDPR obligation, an orphaned subscription is recoverable
(Stripe support / dashboard) and a much smaller harm.
"""

from __future__ import annotations

import logging

import stripe

from app import db
from app.models.user import User
from app.services.analytics_service import track_event
from app.services.stripe_service import init_stripe


logger = logging.getLogger(__name__)


def delete_user_account(user_id: int, reason: str | None = None) -> bool:
    """Permanently delete a user account and all associated data.

    Returns True on success, False on failure. Idempotent: calling on a
    non-existent user_id returns True (treated as already deleted).
    """
    user = db.session.get(User, user_id)
    if user is None:
        logger.info("delete_user_account: user_id=%s already absent", user_id)
        return True

    subscription_id = user.stripe_subscription_id
    if subscription_id:
        try:
            if init_stripe():
                stripe.Subscription.delete(subscription_id)
                logger.info(
                    "delete_user_account: cancelled Stripe sub for user_id=%s",
                    user_id,
                )
            else:
                logger.warning(
                    "delete_user_account: Stripe key not configured; "
                    "subscription %s for user_id=%s NOT cancelled",
                    subscription_id, user_id,
                )
        except stripe.error.StripeError as exc:
            logger.exception(
                "delete_user_account: Stripe cancel failed for user_id=%s sub=%s: %s",
                user_id, subscription_id, exc,
            )

    track_event(user_id, "account_deleted", {"reason": reason})

    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception(
            "delete_user_account: DB delete failed for user_id=%s: %s",
            user_id, exc,
        )
        return False

    logger.info(
        "delete_user_account: user_id=%s deleted (reason=%s)",
        user_id, reason or "<none>",
    )
    return True
