"""
APScheduler setup for Claro background jobs.

Jobs registered here:
  - weekly_digest: every Friday at 08:00 UTC
    Sends personalised weekly email to every user with transaction data.
    No-ops silently if Resend is not yet configured (stub mode).

To initialise: call init_scheduler(app) from create_app() after blueprints
are registered.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = None


def init_scheduler(app):
    global _scheduler

    if _scheduler is not None:
        return  # already running (e.g. Flask reloader double-init guard)

    _scheduler = BackgroundScheduler(timezone="UTC")

    _scheduler.add_job(
        func=_run_weekly_digest,
        trigger=CronTrigger(day_of_week="fri", hour=8, minute=0),
        args=[app],
        id="weekly_digest",
        name="Weekly digest email",
        replace_existing=True,
        misfire_grace_time=3600,  # fire within 1hr if server was down at 8am
    )

    _scheduler.start()
    logger.info("Scheduler started — weekly digest fires every Friday 08:00 UTC")


def _run_weekly_digest(app):
    """Wrapper so APScheduler can call the email service inside app context."""
    try:
        from app.services.email_service import send_digest_to_all_users
        send_digest_to_all_users(app)
    except Exception as e:
        logger.error("Weekly digest job failed: %s", e)


def shutdown_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
