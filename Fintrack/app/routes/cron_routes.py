"""
Cron endpoints — server-to-server triggers, never browser-facing.

Auth model: every cron route requires X-Cron-Secret to match the
CRON_SECRET env var. No login_required, no user session — these are
hit by Render's scheduled-job runner (or any future external scheduler).

Operational rules:
  • POST only. A GET request returns 405 — prevents accidental
    triggering by browsers, prefetchers, or link scanners.
  • If CRON_SECRET is not configured on the server, return 503. We
    don't run the job in that state; we'd rather silently skip a day
    than process the world without auth.
  • The job itself never causes a 500. Per-user errors get rolled into
    the JSON summary so a single bad row doesn't lock out the rest of
    the run.
"""

from __future__ import annotations

import logging
import time

from flask import Blueprint, current_app, jsonify, request

from app import csrf, limiter

logger = logging.getLogger(__name__)

cron_bp = Blueprint("cron", __name__, url_prefix="/cron")


def _resolve_cron_secret() -> str | None:
    """Source of truth is Flask config — config.py already reads CRON_SECRET
    from env at construction time. Reading env here too would let a stray
    shell var leak into tests that explicitly set config to None."""
    return current_app.config.get("CRON_SECRET")


@csrf.exempt
@limiter.exempt
@cron_bp.route("/payday-notifications", methods=["POST"])
def payday_notifications():
    secret = _resolve_cron_secret()
    if not secret:
        logger.error("Cron rejected: CRON_SECRET not configured on server")
        return jsonify({"error": "cron_not_configured"}), 503

    provided = request.headers.get("X-Cron-Secret", "")
    if provided != secret:
        logger.warning(
            "Cron rejected: bad X-Cron-Secret (remote=%s)",
            request.remote_addr,
        )
        return jsonify({"error": "unauthorized"}), 401

    started = time.time()
    logger.info("Cron started: payday-notifications")

    try:
        from app.services.scheduling_service import process_payday_notifications
        summary = process_payday_notifications()
    except Exception as exc:  # noqa: BLE001
        # The scheduling service is built to swallow per-user errors,
        # but a top-level crash (DB connection drop, import error after
        # a deploy) shouldn't return 500 either — that would make the
        # external runner retry and could amplify the failure.
        logger.exception("Cron payday-notifications crashed: %s", exc)
        return jsonify({
            "users_notified": 0,
            "users_skipped": 0,
            "errors": [f"top_level: {exc!s}"],
        }), 200

    elapsed_ms = int((time.time() - started) * 1000)
    logger.info(
        "Cron completed: payday-notifications notified=%d skipped=%d errors=%d elapsed_ms=%d",
        summary.get("users_notified", 0),
        summary.get("users_skipped", 0),
        len(summary.get("errors", [])),
        elapsed_ms,
    )

    return jsonify({**summary, "elapsed_ms": elapsed_ms}), 200
