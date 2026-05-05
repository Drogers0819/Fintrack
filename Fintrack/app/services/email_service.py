"""
Email sending via Resend.

Two callers:
  • send_email(to_email, subject, template_name, template_context)
    The general-purpose entrypoint used by pay-day notifications, missed-
    check-in reminders, and any future transactional mail. Renders an HTML
    Jinja template (under app/templates/emails/<template_name>.html) plus a
    plain-text variant (.txt) and ships both.

  • send_weekly_digest / send_digest_to_all_users
    The pre-existing weekly-digest path. Now lives behind the same Resend
    SDK call as send_email, but keeps its hand-built HTML render via
    digest_service.render_digest_html — that template was already written
    inline, no need to migrate it.

Critical invariants:
  • If RESEND_API_KEY is missing, log a warning and return silently.
    Never raise. A failed welcome email must not break registration; a
    failed pay-day notification must not break the cron.
  • Never log the recipient email address (PII rule). Log user IDs when
    available; otherwise log a sha8 of the email so operators can
    correlate without exposing PII.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _redact_email(email: str | None) -> str:
    if not email:
        return "<none>"
    digest = hashlib.sha256(email.encode("utf-8")).hexdigest()[:8]
    return f"sha8:{digest}"


def _strip_html(html: str) -> str:
    """Crude HTML→text fallback used only when no .txt template exists."""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


def _resolve_from(app=None) -> tuple[str | None, str | None, str | None]:
    """Return (api_key, from_address, from_name) from Flask config.

    config.py is the single source of truth — it already reads each of
    these from the environment at construction time. Reading env again
    here would let a stray shell var leak past TestingConfig, which
    explicitly sets all three to None to keep tests hermetic.
    """
    import os
    if app is None:
        try:
            from flask import current_app
            cfg = current_app.config
        except RuntimeError:
            # No app context (rare — CLI tools, tests). Fall back to env
            # directly so the function is still usable.
            return (
                os.environ.get("RESEND_API_KEY"),
                os.environ.get("EMAIL_FROM"),
                os.environ.get("EMAIL_FROM_NAME"),
            )
    else:
        cfg = app.config
    return (
        cfg.get("RESEND_API_KEY"),
        cfg.get("EMAIL_FROM"),
        cfg.get("EMAIL_FROM_NAME"),
    )


def send_email(
    to_email: str,
    subject: str,
    template_name: str,
    template_context: dict[str, Any] | None = None,
) -> bool:
    """Render <template_name>.html (and .txt if present) under
    app/templates/emails/ with the given context, send via Resend.

    Returns True if the send appeared to succeed, False if the message
    was dropped (no API key, render failure, or SDK exception). Never
    raises — callers can ignore the return value when they have nothing
    sensible to do with a failure (the cron does this).
    """
    if not to_email:
        return False

    api_key, from_addr, from_name = _resolve_from()
    if not api_key:
        logger.warning(
            "Email skipped (no RESEND_API_KEY): template=%s recipient=%s",
            template_name, _redact_email(to_email),
        )
        return False
    if not from_addr:
        logger.warning(
            "Email skipped (no EMAIL_FROM): template=%s recipient=%s",
            template_name, _redact_email(to_email),
        )
        return False

    try:
        from flask import current_app, has_request_context, render_template
        ctx = dict(template_context or {})

        # Some context processors in app/__init__.py reach for `request`,
        # so render_template needs a request context. Cron requests have
        # one already; future CLI/APScheduler callers may not.
        if has_request_context():
            html_body = render_template(f"emails/{template_name}.html", **ctx)
            try:
                text_body = render_template(f"emails/{template_name}.txt", **ctx)
            except Exception:  # noqa: BLE001 — .txt is optional
                text_body = _strip_html(html_body)
        else:
            with current_app.test_request_context():
                html_body = render_template(f"emails/{template_name}.html", **ctx)
                try:
                    text_body = render_template(f"emails/{template_name}.txt", **ctx)
                except Exception:  # noqa: BLE001 — .txt is optional
                    text_body = _strip_html(html_body)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Email render failed: template=%s recipient=%s err=%s",
            template_name, _redact_email(to_email), exc,
        )
        return False

    sender = f"{from_name} <{from_addr}>" if from_name else from_addr

    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": sender,
            "to": to_email,
            "subject": subject,
            "html": html_body,
            "text": text_body,
        })
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Email send failed: template=%s recipient=%s err=%s",
            template_name, _redact_email(to_email), exc,
        )
        return False


def send_weekly_digest(app, user, whisper_data):
    """Build and send the weekly digest for a single user. Safe inside an
    APScheduler job with app context. Returns True if sent, False if
    skipped (no data, render failure, send failure)."""
    from app.services.digest_service import build_weekly_digest, render_digest_html

    txn_count = whisper_data.get("total_transactions", 0)
    if txn_count == 0:
        logger.debug("Skipping digest for user %s — no transaction data", user.id)
        return False

    digest = build_weekly_digest(user, [], whisper_data)
    if not digest:
        return False

    html_body = render_digest_html(digest)
    if not html_body:
        return False

    api_key, from_addr, from_name = _resolve_from(app)
    if not api_key or not from_addr:
        logger.info(
            "[DIGEST] Skipped — Resend not configured. user=%s subject=%s",
            user.id, digest["subject"],
        )
        return False

    sender = f"{from_name} <{from_addr}>" if from_name else from_addr

    try:
        import resend
        resend.api_key = api_key
        resend.Emails.send({
            "from": sender,
            "to": user.email,
            "subject": digest["subject"],
            "html": html_body,
        })
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Digest send failed for user %s: %s", user.id, exc)
        return False


def send_digest_to_all_users(app):
    """Run the weekly digest for every user with transaction data.
    Called by the APScheduler job in scheduler.py."""
    with app.app_context():
        from app.models.user import User
        from app.models.transaction import Transaction
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
                if send_weekly_digest(app, user, whisper_data):
                    sent += 1
                else:
                    skipped += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Digest failed for user %s: %s", user.id, exc)
                skipped += 1

        logger.info("Weekly digest complete: %d sent, %d skipped", sent, skipped)
