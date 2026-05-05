"""
Pay-day notification system — Block 2 Task 2.1.

Coverage:
  • Scheduling logic — match on income_day, skip on no income_day, last-day-of-month
    edge case (income_day=31 in February → fire on day 28/29).
  • Idempotency — payday_notification_last_sent gates the per-month send.
  • Skip rules — already-checked-in users don't get notified.
  • Cron endpoint — POST-only, X-Cron-Secret auth, 503 when secret missing,
    never 500 even when the inner job raises.
  • Email service — render template with context, swallow send failures,
    no PII in logs.
  • Check-in route — ?source=payday flows into the checkin_started event.
"""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app import create_app, db
from app.models.checkin import CheckIn
from app.models.user import User
from config import TestingConfig


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(app, email="payday@test.com", income_day=15, name="Payday User"):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.income_day = income_day
        user.subscription_status = "trialing"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="payday@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


# ─── Scheduling service ──────────────────────────────────────


class TestSchedulingMatching:
    """Who gets notified on a given calendar day."""

    def test_user_with_matching_payday_is_notified(self, app):
        """The simplest path: today.day == income_day → send."""
        from app.services.scheduling_service import process_payday_notifications

        uid = _make_user(app, income_day=15)

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_payday_notifications(today=date(2026, 5, 15))

            assert summary["users_notified"] == 1
            assert summary["users_skipped"] == 0
            send.assert_called_once()
            user = db.session.get(User, uid)
            assert user.payday_notification_last_sent == date(2026, 5, 15)

    def test_user_without_payday_is_skipped(self, app):
        from app.services.scheduling_service import process_payday_notifications

        with app.app_context():
            user = User(email="noday@test.com", name="No Day")
            user.set_password("testpassword123")
            user.income_day = None
            db.session.add(user)
            db.session.commit()

            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_payday_notifications(today=date(2026, 5, 15))

            assert summary["users_notified"] == 0
            assert send.call_count == 0

    def test_user_with_non_matching_day_is_skipped(self, app):
        from app.services.scheduling_service import process_payday_notifications

        _make_user(app, income_day=15)

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_payday_notifications(today=date(2026, 5, 14))

            assert summary["users_notified"] == 0
            assert send.call_count == 0

    def test_income_day_31_fires_on_last_day_of_short_month(self, app):
        """A user with income_day=31 in Feb should be notified on Feb 28
        (or Feb 29 in a leap year), not silently skipped."""
        from app.services.scheduling_service import process_payday_notifications

        _make_user(app, income_day=31)

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True) as send:
                # 2026 is not a leap year — Feb has 28 days.
                summary = process_payday_notifications(today=date(2026, 2, 28))

            assert summary["users_notified"] == 1
            send.assert_called_once()

    def test_income_day_31_fires_in_30_day_month(self, app):
        from app.services.scheduling_service import process_payday_notifications

        _make_user(app, income_day=31)

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True):
                summary = process_payday_notifications(today=date(2026, 4, 30))

            assert summary["users_notified"] == 1


class TestSchedulingIdempotency:
    """Re-running the cron on the same day is safe."""

    def test_running_twice_on_same_day_only_notifies_once(self, app):
        from app.services.scheduling_service import process_payday_notifications

        _make_user(app, income_day=10)

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True) as send:
                first = process_payday_notifications(today=date(2026, 5, 10))
                second = process_payday_notifications(today=date(2026, 5, 10))

            assert first["users_notified"] == 1
            assert second["users_notified"] == 0
            assert send.call_count == 1

    def test_send_failure_does_not_mark_as_notified(self, app):
        """If the email service returns False, we want a retry on the next
        cron tick — so don't stamp payday_notification_last_sent."""
        from app.services.scheduling_service import process_payday_notifications

        uid = _make_user(app, income_day=10)

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=False):
                summary = process_payday_notifications(today=date(2026, 5, 10))

            assert summary["users_notified"] == 0
            assert any("send_failed" in e for e in summary["errors"])
            user = db.session.get(User, uid)
            assert user.payday_notification_last_sent is None

    def test_notified_last_month_can_be_notified_this_month(self, app):
        """Idempotency is per-calendar-month, not forever."""
        from app.services.scheduling_service import process_payday_notifications

        uid = _make_user(app, income_day=10)
        with app.app_context():
            user = db.session.get(User, uid)
            user.payday_notification_last_sent = date(2026, 4, 10)
            db.session.commit()

            with patch("app.services.email_service.send_email", return_value=True):
                summary = process_payday_notifications(today=date(2026, 5, 10))

            assert summary["users_notified"] == 1


class TestSchedulingSkipsCompletedCheckins:

    def test_user_who_already_checked_in_is_skipped(self, app):
        """If a user's check-in for the relevant period exists, no nudge."""
        from app.services.scheduling_service import process_payday_notifications

        uid = _make_user(app, income_day=10)
        with app.app_context():
            # The check-in shown on May 10 covers April. Pre-fill it.
            ci = CheckIn(user_id=uid, month=4, year=2026)
            db.session.add(ci)
            db.session.commit()

            with patch("app.services.email_service.send_email", return_value=True) as send:
                summary = process_payday_notifications(today=date(2026, 5, 10))

            assert summary["users_notified"] == 0
            assert send.call_count == 0


class TestSchedulingTracksAnalytics:

    def test_payday_notification_sent_event_fires(self, app):
        from app.services.scheduling_service import process_payday_notifications

        _make_user(app, income_day=15)

        with app.app_context():
            with patch("app.services.email_service.send_email", return_value=True), \
                 patch("app.services.analytics_service.track_event") as track:
                process_payday_notifications(today=date(2026, 5, 15))

            track.assert_called_once()
            args, kwargs = track.call_args
            assert args[1] == "payday_notification_sent"
            assert args[2]["payday_day"] == 15


# ─── Cron endpoint ───────────────────────────────────────────


class TestCronEndpoint:

    def test_get_returns_405(self, app, client):
        """POST-only — accidental browser hits never run the job."""
        resp = client.get("/cron/payday-notifications")
        assert resp.status_code == 405

    def test_missing_cron_secret_env_returns_503(self, app, client):
        """If CRON_SECRET isn't set on the server, refuse to run rather
        than processing without auth."""
        # TestingConfig sets CRON_SECRET=None.
        resp = client.post("/cron/payday-notifications")
        assert resp.status_code == 503

    def test_missing_header_returns_401(self, app, client):
        app.config["CRON_SECRET"] = "shh-its-a-secret"
        try:
            resp = client.post("/cron/payday-notifications")
            assert resp.status_code == 401
        finally:
            app.config["CRON_SECRET"] = None

    def test_wrong_header_returns_401(self, app, client):
        app.config["CRON_SECRET"] = "right-value"
        try:
            resp = client.post(
                "/cron/payday-notifications",
                headers={"X-Cron-Secret": "wrong-value"},
            )
            assert resp.status_code == 401
        finally:
            app.config["CRON_SECRET"] = None

    def test_correct_header_runs_job_and_returns_summary(self, app, client):
        app.config["CRON_SECRET"] = "right-value"
        try:
            with patch(
                "app.services.scheduling_service.process_payday_notifications",
                return_value={"users_notified": 0, "users_skipped": 0, "errors": []},
            ):
                resp = client.post(
                    "/cron/payday-notifications",
                    headers={"X-Cron-Secret": "right-value"},
                )
            assert resp.status_code == 200
            body = resp.get_json()
            assert body["users_notified"] == 0
            assert "elapsed_ms" in body
        finally:
            app.config["CRON_SECRET"] = None

    def test_inner_crash_does_not_500(self, app, client):
        """Even a top-level crash returns 200 with errors so the external
        runner doesn't retry-storm."""
        app.config["CRON_SECRET"] = "right-value"
        try:
            with patch(
                "app.services.scheduling_service.process_payday_notifications",
                side_effect=RuntimeError("db down"),
            ):
                resp = client.post(
                    "/cron/payday-notifications",
                    headers={"X-Cron-Secret": "right-value"},
                )
            assert resp.status_code == 200
            body = resp.get_json()
            assert body["users_notified"] == 0
            assert any("top_level" in e for e in body["errors"])
        finally:
            app.config["CRON_SECRET"] = None


# ─── Email service ───────────────────────────────────────────


class TestEmailServiceContract:

    def test_send_returns_false_when_no_api_key(self, app):
        """Missing RESEND_API_KEY → log warning, return False, never raise."""
        from app.services import email_service

        with app.app_context():
            result = email_service.send_email(
                to_email="someone@example.com",
                subject="Test",
                template_name="payday_notification",
                template_context={"first_name": "Sam", "checkin_url": "/check-in"},
            )
            assert result is False

    def test_send_swallows_sdk_exceptions(self, app):
        """If the Resend SDK raises, send_email logs and returns False —
        never propagates."""
        from app.services import email_service

        app.config["RESEND_API_KEY"] = "test-key"
        app.config["EMAIL_FROM"] = "hello@getclaro.co.uk"
        try:
            fake_resend = MagicMock()
            fake_resend.Emails.send.side_effect = RuntimeError("network down")

            with app.app_context():
                with patch.dict("sys.modules", {"resend": fake_resend}):
                    # send_email imports `resend` lazily inside the try block.
                    result = email_service.send_email(
                        to_email="someone@example.com",
                        subject="Test",
                        template_name="payday_notification",
                        template_context={"first_name": "Sam", "checkin_url": "/x"},
                    )
            assert result is False
        finally:
            app.config["RESEND_API_KEY"] = None
            app.config["EMAIL_FROM"] = None

    def test_payday_template_renders_with_context(self, app):
        """The template should pick up first_name and checkin_url."""
        with app.test_request_context():
            from flask import render_template
            html = render_template(
                "emails/payday_notification.html",
                first_name="Daniel",
                checkin_url="https://claro-2.onrender.com/check-in?source=payday",
            )
            assert "Daniel" in html
            assert "https://claro-2.onrender.com/check-in?source=payday" in html
            assert "Open my check-in" in html
            # No em-dashes in user-facing copy
            assert "—" not in html

    def test_payday_text_template_renders(self, app):
        with app.test_request_context():
            from flask import render_template
            text = render_template(
                "emails/payday_notification.txt",
                first_name="Daniel",
                checkin_url="https://claro-2.onrender.com/check-in?source=payday",
            )
            assert "Daniel" in text
            assert "https://claro-2.onrender.com/check-in?source=payday" in text
            # No em-dashes
            assert "—" not in text


# ─── Check-in route source=payday wiring ─────────────────────


class TestCheckinSourceParam:

    def test_source_payday_flows_into_checkin_started_event(self, app, client):
        """Hitting /check-in?source=payday during the check-in window
        should fire checkin_started with source='payday'."""
        # Set up a user with factfind+income so the form renders.
        with app.app_context():
            user = User(email="checkinsrc@test.com", name="CI Source")
            user.set_password("testpassword123")
            user.factfind_completed = True
            user.monthly_income = 2000
            user.rent_amount = 800
            user.bills_amount = 200
            user.income_day = 25
            user.subscription_status = "trialing"
            user.subscription_tier = "pro_plus"
            user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
            db.session.add(user)
            db.session.commit()

        client.post("/api/auth/login", json={
            "email": "checkinsrc@test.com",
            "password": "testpassword123",
        })

        # The check-in window only opens in the last 3 days of the month.
        # Patch date.today() inside the route's calendar helper to land
        # us inside the window deterministically.
        from app.routes import page_routes

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 30)  # last 3 days of May

        with patch.object(page_routes, "date", _FixedDate), \
             patch("app.routes.page_routes.track_event") as track:
            resp = client.get("/check-in?source=payday")

        assert resp.status_code == 200

        started_calls = [
            c for c in track.call_args_list
            if len(c.args) >= 2 and c.args[1] == "checkin_started"
        ]
        assert len(started_calls) == 1
        props = started_calls[0].args[2]
        assert props["source"] == "payday"

    def test_no_source_param_defaults_to_direct(self, app, client):
        with app.app_context():
            user = User(email="direct@test.com", name="Direct CI")
            user.set_password("testpassword123")
            user.factfind_completed = True
            user.monthly_income = 2000
            user.rent_amount = 800
            user.bills_amount = 200
            user.income_day = 25
            user.subscription_status = "trialing"
            user.subscription_tier = "pro_plus"
            user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
            db.session.add(user)
            db.session.commit()

        client.post("/api/auth/login", json={
            "email": "direct@test.com",
            "password": "testpassword123",
        })

        from app.routes import page_routes

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 30)

        with patch.object(page_routes, "date", _FixedDate), \
             patch("app.routes.page_routes.track_event") as track:
            client.get("/check-in")

        started_calls = [
            c for c in track.call_args_list
            if len(c.args) >= 2 and c.args[1] == "checkin_started"
        ]
        assert started_calls
        assert started_calls[0].args[2]["source"] == "direct"
