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

Contract (post May 2026 silent-failure incident):
    delete_user_account returns True ONLY when a fresh database query
    confirms the User row is absent. Any path where the commit returned
    without raising but the row remained — the production symptom on
    11 May 2026 — now returns False.
"""

from __future__ import annotations

import logging

import stripe

from app import db
from app.models.user import User
from app.services.analytics_service import track_event
from app.services.stripe_service import init_stripe


logger = logging.getLogger(__name__)


def _user_row_is_absent(user_id: int) -> bool:
    """Verify the user row is gone from the database.

    Contract: returns True only when a query has confirmed the row is
    absent. Returns False both when the row is present AND when the
    verifying query itself raised — "could not confirm absence" must
    never be reported as success.

    Bypasses pending session state via no_autoflush so an unflushed
    delete (the silent-rollback edge case) is not pushed to the DB
    mid-check and made to look like a success. On any exception, the
    rollback restores the session so the caller can keep going safely.
    """
    try:
        with db.session.no_autoflush:
            return User.query.filter_by(id=user_id).count() == 0
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "delete_user_account: verification query failed for user_id=%s "
            "(%s): %s — treating as unverified, not absent",
            user_id, type(exc).__name__, exc,
        )
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass
        return False


def delete_user_account(user_id: int, reason: str | None = None) -> bool:
    """Permanently delete a user account and all associated data.

    Returns True ONLY when a fresh query confirms the User row is
    absent from the database. Returns False on any failure path —
    Stripe or analytics exceptions that interrupt the flow, DB
    errors during delete/commit, and silent-rollback commits that
    leave the row in place.

    Idempotent: a user_id confirmed absent by the fresh query
    returns True without raising.
    """
    user = db.session.get(User, user_id)
    if user is None:
        # Don't trust the session's identity-map view in isolation —
        # a deactivated transaction or expired-instance edge case can
        # report None for a row that still exists. Verify against the DB.
        if _user_row_is_absent(user_id):
            logger.info(
                "delete_user_account: user_id=%s already absent (verified)",
                user_id,
            )
            return True
        logger.warning(
            "delete_user_account: session returned None for user_id=%s "
            "but the row exists at the DB layer; re-fetching",
            user_id,
        )
        user = db.session.get(User, user_id)
        if user is None:
            logger.error(
                "delete_user_account: user_id=%s unresolvable after refresh; "
                "aborting without delete",
                user_id,
            )
            return False

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
        except Exception as exc:  # noqa: BLE001
            # Broadened from stripe.error.StripeError. A non-Stripe
            # exception (urllib3.MaxRetryError, requests.Timeout, an
            # SDK regression) must NOT propagate out of this function
            # or leave the session in a state that silently rolls back
            # the subsequent DB delete.
            logger.exception(
                "delete_user_account: Stripe cancel failed for "
                "user_id=%s sub=%s (%s): %s",
                user_id, subscription_id, type(exc).__name__, exc,
            )

    try:
        track_event(user_id, "account_deleted", {"reason": reason})
    except Exception as exc:  # noqa: BLE001
        # track_event swallows internally today; this is defence in
        # depth against a future refactor that lets it raise.
        logger.exception(
            "delete_user_account: track_event raised for user_id=%s (%s): %s",
            user_id, type(exc).__name__, exc,
        )

    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        logger.exception(
            "delete_user_account: DB delete failed for user_id=%s (%s): %s",
            user_id, type(exc).__name__, exc,
        )
        return False

    # Post-condition: trust the database, not the session. commit() can
    # return without raising while the row remains — the 11 May 2026
    # silent-failure scenario. Any True returned past this point is
    # backed by a fresh query.
    if not _user_row_is_absent(user_id):
        logger.error(
            "delete_user_account: post-commit verification did not confirm "
            "user_id=%s absent from database; reporting failure",
            user_id,
        )
        return False

    logger.info(
        "delete_user_account: user_id=%s deleted (reason=%s)",
        user_id, reason or "<none>",
    )
    return True
