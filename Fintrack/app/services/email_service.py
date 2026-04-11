"""
Email sending via Resend.

The send step is stubbed until Daniel confirms:
  1. Resend API key is in config (RESEND_API_KEY)
  2. SPF + DKIM records are set on getclaro.co.uk
  3. The sending domain is verified in the Resend dashboard

To activate: uncomment the resend.Emails.send() call below and
remove the stub log line. Nothing else needs to change.
"""

import logging
from app.services.digest_service import build_weekly_digest, render_digest_html

logger = logging.getLogger(__name__)


def send_weekly_digest(app, user, whisper_data):
    """
    Builds and sends the weekly digest email for a single user.
    Safe to call inside an APScheduler job with app context.

    Returns True if sent (or stubbed), False if skipped.
    """
    txn_count = whisper_data.get("total_transactions", 0)
    if txn_count == 0:
        logger.debug("Skipping digest for %s — no transaction data", user.email)
        return False

    digest = build_weekly_digest(user, [], whisper_data)
    if not digest:
        return False

    html_body = render_digest_html(digest)
    if not html_body:
        return False

    # ── STUB: replace this block with the live send once Resend is configured ──
    #
    # import resend
    # resend.api_key = app.config["RESEND_API_KEY"]
    # resend.Emails.send({
    #     "from": "Daniel at Claro <daniel@getclaro.co.uk>",
    #     "to": user.email,
    #     "subject": digest["subject"],
    #     "html": html_body,
    # })
    #
    # ── END STUB ──────────────────────────────────────────────────────────────

    logger.info(
        "[DIGEST STUB] Would send to %s | Subject: %s",
        user.email,
        digest["subject"],
    )
    return True


def send_digest_to_all_users(app):
    """
    Runs the weekly digest for every user who has transaction data.
    Called by the APScheduler job in scheduler.py.
    """
    with app.app_context():
        from app.models.user import User
        from app.models.transaction import Transaction
        from app.models.goal import Goal
        from app.routes.page_routes import _build_whisper_data_for_user

        users = User.query.all()
        sent = 0
        skipped = 0

        for user in users:
            try:
                txn_count = Transaction.query.filter_by(user_id=user.id).count()
                if txn_count == 0:
                    skipped += 1
                    continue

                whisper_data = _build_whisper_data_for_user(user)
                result = send_weekly_digest(app, user, whisper_data)
                if result:
                    sent += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error("Digest failed for user %s: %s", user.id, e)
                skipped += 1

        logger.info("Weekly digest complete: %d sent, %d skipped", sent, skipped)
