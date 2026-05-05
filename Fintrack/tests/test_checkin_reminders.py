"""
Missed check-in reminder ladder — Block 2 Task 2.2.

Coverage:
  • Ladder timing — reminders fire on day +3, +7, +14 from
    payday_notification_last_sent and nowhere else.
  • Idempotency — each reminder fires at most once per cycle; running
    the cron twice on the same day is a no-op for the second run.
  • Stop-on-completion — a user who files their check-in mid-ladder
    receives no further reminders.
  • Cycle reset — process_payday_notifications clears the three
    reminder-sent fields when a new pay-day fires, so the next month's
    ladder runs fresh.
  • Cron endpoint security — POST-only, X-Cron-Secret auth, 503 when
    secret missing, never 500 even if the inner job raises.
  • Email render — all three templates pick up first_name and the
    reminder-attributed checkin_url, contain no em-dashes.
  • Analytics — checkin_reminder_sent fires with reminder_number and
    days_since_payday properties.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest

from app import db
from app.models.checkin import CheckIn
from app.models.user import User


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(
    app,
    email="reminder@test.com",
    income_day=15,
    name="Reminder User",
    payday_sent=None,
):
    """Make a user whose pay-day notification has already fired.

    payday_sent — anchor date for the ladder. Defaults to None so callers
    can opt in. Most reminder-ladder tests want this set."""
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.income_day = income_day
        user.payday_notification_last_sent = payday_sent
        user.subscription_status = "trialing"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


# ─── Ladder timing ───────────────────────────────────────────


class TestReminderLadderTiming:
    """Reminders fire on day +3, +7, +14 from the pay-day anchor."""

    def test_day_plus_3_fires_reminder_1(self, app):
        from app.services.scheduling_service import process_checkin_reminders

        uid = _make_user(app, payday_sent=date(2026, 5, 15))

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_checkin_reminders(today=date(2026, 5, 18))

            assert summary["users_notified"] == 1
            assert summary["reminder_breakdown"][1] == 1
            send.assert_called_once()
            kwargs = send.call_args.kwargs
            assert kwargs["template_name"] == "checkin_reminder_1"
            assert kwargs["subject"] == "Quick nudge for your check-in"

            user = db.session.get(User, uid)
            assert user.checkin_reminder_1_sent == date(2026, 5, 18)

    def test_day_plus_7_fires_reminder_2(self, app):
        from app.services.scheduling_service import process_checkin_reminders

        uid = _make_user(app, payday_sent=date(2026, 5, 15))
        # Pretend reminder 1 already fired so the ladder progressed.
        with app.app_context():
            user = db.session.get(User, uid)
            user.checkin_reminder_1_sent = date(2026, 5, 18)
            db.session.commit()

            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_checkin_reminders(today=date(2026, 5, 22))

            assert summary["users_notified"] == 1
            assert summary["reminder_breakdown"][2] == 1
            kwargs = send.call_args.kwargs
            assert kwargs["template_name"] == "checkin_reminder_2"

            user = db.session.get(User, uid)
            assert user.checkin_reminder_2_sent == date(2026, 5, 22)

    def test_day_plus_14_fires_reminder_3(self, app):
        from app.services.scheduling_service import process_checkin_reminders

        uid = _make_user(app, payday_sent=date(2026, 5, 15))
        with app.app_context():
            user = db.session.get(User, uid)
            user.checkin_reminder_1_sent = date(2026, 5, 18)
            user.checkin_reminder_2_sent = date(2026, 5, 22)
            db.session.commit()

            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_checkin_reminders(today=date(2026, 5, 29))

            assert summary["users_notified"] == 1
            assert summary["reminder_breakdown"][3] == 1
            kwargs = send.call_args.kwargs
            assert kwargs["template_name"] == "checkin_reminder_3"
            assert kwargs["subject"] == "We will stop here"

            user = db.session.get(User, uid)
            assert user.checkin_reminder_3_sent == date(2026, 5, 29)

    def test_off_schedule_days_do_not_fire(self, app):
        """Day +1, +2, +4, +8, +13, +15 should all skip."""
        from app.services.scheduling_service import process_checkin_reminders

        _make_user(app, payday_sent=date(2026, 5, 15))

        with app.app_context():
            for off_day in (1, 2, 4, 8, 13, 15):
                with patch("app.services.email_service.send_email", return_value=True) as send:
                    summary = process_checkin_reminders(
                        today=date(2026, 5, 15) + timedelta(days=off_day)
                    )
                assert summary["users_notified"] == 0, f"day +{off_day} should skip"
                assert send.call_count == 0

    def test_user_without_payday_anchor_is_skipped(self, app):
        """A user whose pay-day notification never fired (anchor None)
        is invisible to the ladder."""
        from app.services.scheduling_service import process_checkin_reminders

        _make_user(app, payday_sent=None)

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_checkin_reminders(today=date(2026, 5, 18))

            assert summary["users_notified"] == 0
            assert send.call_count == 0


# ─── Idempotency ─────────────────────────────────────────────


class TestReminderIdempotency:

    def test_same_day_rerun_does_not_double_send(self, app):
        from app.services.scheduling_service import process_checkin_reminders

        _make_user(app, payday_sent=date(2026, 5, 15))

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True) as send:
                first = process_checkin_reminders(today=date(2026, 5, 18))
                second = process_checkin_reminders(today=date(2026, 5, 18))

            assert first["users_notified"] == 1
            assert second["users_notified"] == 0
            assert send.call_count == 1

    def test_send_failure_does_not_stamp_field(self, app):
        """Send returned False → don't stamp, so the next cron retries."""
        from app.services.scheduling_service import process_checkin_reminders

        uid = _make_user(app, payday_sent=date(2026, 5, 15))

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=False):
                summary = process_checkin_reminders(today=date(2026, 5, 18))

            assert summary["users_notified"] == 0
            assert any("send_failed" in e for e in summary["errors"])
            user = db.session.get(User, uid)
            assert user.checkin_reminder_1_sent is None


# ─── Stop on completion ──────────────────────────────────────


class TestStopOnCheckinCompletion:

    def test_user_who_filed_checkin_gets_no_reminder_1(self, app):
        """Same skip rule the pay-day cron uses: if the relevant
        check-in row exists, the ladder stops."""
        from app.services.scheduling_service import process_checkin_reminders

        uid = _make_user(app, payday_sent=date(2026, 5, 15))
        with app.app_context():
            # The check-in shown on May 18 covers April.
            ci = CheckIn(user_id=uid, month=4, year=2026)
            db.session.add(ci)
            db.session.commit()

            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_checkin_reminders(today=date(2026, 5, 18))

            assert summary["users_notified"] == 0
            assert send.call_count == 0

    def test_mid_ladder_checkin_stops_subsequent_reminders(self, app):
        """User got reminder 1, then filed the check-in. Reminder 2
        and 3 must not fire."""
        from app.services.scheduling_service import process_checkin_reminders

        uid = _make_user(app, payday_sent=date(2026, 5, 15))
        with app.app_context():
            user = db.session.get(User, uid)
            user.checkin_reminder_1_sent = date(2026, 5, 18)
            db.session.commit()

            # User files their April check-in on May 20.
            ci = CheckIn(user_id=uid, month=4, year=2026)
            db.session.add(ci)
            db.session.commit()

            # Day +7 cron run: reminder 2 must NOT fire.
            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary_7 = process_checkin_reminders(today=date(2026, 5, 22))

            assert summary_7["users_notified"] == 0
            assert send.call_count == 0

            user = db.session.get(User, uid)
            assert user.checkin_reminder_2_sent is None

            # Day +14 too.
            with patch("app.services.email_service.send_email", return_value=True) as send2:
                summary_14 = process_checkin_reminders(today=date(2026, 5, 29))

            assert summary_14["users_notified"] == 0
            assert send2.call_count == 0


# ─── Cycle reset on new pay-day ──────────────────────────────


class TestCycleResetOnPayday:
    """When a new pay-day notification fires, the three reminder
    fields must reset so the next cycle's ladder runs fresh."""

    def test_payday_resets_all_three_reminder_fields(self, app):
        from app.services.scheduling_service import process_payday_notifications

        with app.app_context():
            user = User(email="cycle@test.com", name="Cycle Reset")
            user.set_password("testpassword123")
            user.income_day = 15
            user.payday_notification_last_sent = date(2026, 4, 15)
            user.checkin_reminder_1_sent = date(2026, 4, 18)
            user.checkin_reminder_2_sent = date(2026, 4, 22)
            user.checkin_reminder_3_sent = date(2026, 4, 29)
            db.session.add(user)
            db.session.commit()
            uid = user.id

            with patch("app.services.email_service.send_email", return_value=True):
                summary = process_payday_notifications(today=date(2026, 5, 15))

            assert summary["users_notified"] == 1

            user = db.session.get(User, uid)
            assert user.payday_notification_last_sent == date(2026, 5, 15)
            assert user.checkin_reminder_1_sent is None
            assert user.checkin_reminder_2_sent is None
            assert user.checkin_reminder_3_sent is None

    def test_post_reset_ladder_fires_in_new_cycle(self, app):
        """End-to-end: April ladder ran, May pay-day fires (which
        resets), May day-3 reminder fires fresh."""
        from app.services.scheduling_service import (
            process_checkin_reminders,
            process_payday_notifications,
        )

        with app.app_context():
            user = User(email="endtoend@test.com", name="End To End")
            user.set_password("testpassword123")
            user.income_day = 15
            user.payday_notification_last_sent = date(2026, 4, 15)
            user.checkin_reminder_1_sent = date(2026, 4, 18)
            db.session.add(user)
            db.session.commit()
            uid = user.id

            with patch("app.services.email_service.send_email", return_value=True):
                process_payday_notifications(today=date(2026, 5, 15))
                summary = process_checkin_reminders(today=date(2026, 5, 18))

            assert summary["users_notified"] == 1
            user = db.session.get(User, uid)
            assert user.checkin_reminder_1_sent == date(2026, 5, 18)


# ─── Analytics ───────────────────────────────────────────────


class TestReminderAnalytics:

    def test_checkin_reminder_sent_event_fires_with_correct_props(self, app):
        from app.services.scheduling_service import process_checkin_reminders

        _make_user(app, payday_sent=date(2026, 5, 15))

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True), \
                 patch("app.services.analytics_service.track_event") as track:
                process_checkin_reminders(today=date(2026, 5, 22))

            track.assert_called_once()
            args, _kwargs = track.call_args
            assert args[1] == "checkin_reminder_sent"
            props = args[2]
            assert props["reminder_number"] == 2
            assert props["days_since_payday"] == 7


# ─── Cron endpoint ───────────────────────────────────────────


class TestReminderCronEndpoint:

    def test_get_returns_405(self, app, client):
        resp = client.get("/cron/checkin-reminders")
        assert resp.status_code == 405

    def test_missing_cron_secret_env_returns_503(self, app, client):
        resp = client.post("/cron/checkin-reminders")
        assert resp.status_code == 503

    def test_missing_header_returns_401(self, app, client):
        app.config["CRON_SECRET"] = "shh-its-a-secret"
        try:
            resp = client.post("/cron/checkin-reminders")
            assert resp.status_code == 401
        finally:
            app.config["CRON_SECRET"] = None

    def test_wrong_header_returns_401(self, app, client):
        app.config["CRON_SECRET"] = "right-value"
        try:
            resp = client.post(
                "/cron/checkin-reminders",
                headers={"X-Cron-Secret": "wrong-value"},
            )
            assert resp.status_code == 401
        finally:
            app.config["CRON_SECRET"] = None

    def test_correct_header_runs_job_and_returns_summary(self, app, client):
        app.config["CRON_SECRET"] = "right-value"
        try:
            with patch(
                "app.services.scheduling_service.process_checkin_reminders",
                return_value={
                    "users_notified": 0,
                    "users_skipped": 0,
                    "errors": [],
                    "reminder_breakdown": {1: 0, 2: 0, 3: 0},
                },
            ):
                resp = client.post(
                    "/cron/checkin-reminders",
                    headers={"X-Cron-Secret": "right-value"},
                )
            assert resp.status_code == 200
            body = resp.get_json()
            assert body["users_notified"] == 0
            assert "elapsed_ms" in body
            assert "reminder_breakdown" in body
        finally:
            app.config["CRON_SECRET"] = None

    def test_inner_crash_does_not_500(self, app, client):
        app.config["CRON_SECRET"] = "right-value"
        try:
            with patch(
                "app.services.scheduling_service.process_checkin_reminders",
                side_effect=RuntimeError("db down"),
            ):
                resp = client.post(
                    "/cron/checkin-reminders",
                    headers={"X-Cron-Secret": "right-value"},
                )
            assert resp.status_code == 200
            body = resp.get_json()
            assert body["users_notified"] == 0
            assert any("top_level" in e for e in body["errors"])
        finally:
            app.config["CRON_SECRET"] = None


# ─── Email templates ─────────────────────────────────────────


class TestReminderTemplatesRender:

    @pytest.mark.parametrize("template", [
        "checkin_reminder_1",
        "checkin_reminder_2",
        "checkin_reminder_3",
    ])
    def test_html_template_renders_with_context(self, app, template):
        with app.test_request_context():
            from flask import render_template
            html = render_template(
                f"emails/{template}.html",
                first_name="Daniel",
                checkin_url="https://claro-2.onrender.com/check-in?source=reminder",
            )
            assert "Daniel" in html
            assert "https://claro-2.onrender.com/check-in?source=reminder" in html
            assert "Open my check-in" in html
            # No em-dashes in user-facing copy
            assert "—" not in html

    @pytest.mark.parametrize("template", [
        "checkin_reminder_1",
        "checkin_reminder_2",
        "checkin_reminder_3",
    ])
    def test_txt_template_renders_with_context(self, app, template):
        with app.test_request_context():
            from flask import render_template
            text = render_template(
                f"emails/{template}.txt",
                first_name="Daniel",
                checkin_url="https://claro-2.onrender.com/check-in?source=reminder",
            )
            assert "Daniel" in text
            assert "https://claro-2.onrender.com/check-in?source=reminder" in text
            assert "—" not in text
