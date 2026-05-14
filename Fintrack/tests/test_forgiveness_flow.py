"""
Forgiveness flow for missed check-ins — Block 2 Task 2.3.

Coverage:
  • Detection logic — get_forgiveness_target returns the right
    (year, month) only when the user actually qualifies, and None
    everywhere else.
  • Route rendering — GET shows the forgiveness state and tracks
    forgiveness_state_shown; without a forgiveness target the
    existing scheduled/form/complete states still render.
  • Submission handling — POST writes the CheckIn to the targeted
    month, validates against fresh detection (re-runs on submit),
    rejects submissions outside the 60-day catch-up window,
    fires checkin_completed with was_late: True, and redirects to
    /overview.
"""

from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest

from app import db
from app.models.checkin import CheckIn, CheckInEntry
from app.models.goal import Goal
from app.models.user import User


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(
    app,
    email="forgive@test.com",
    name="Forgive User",
    *,
    payday_sent=None,
    reminder_1=None,
    reminder_2=None,
    reminder_3=None,
    factfind=True,
):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.income_day = 15
        user.payday_notification_last_sent = payday_sent
        user.checkin_reminder_1_sent = reminder_1
        user.checkin_reminder_2_sent = reminder_2
        user.checkin_reminder_3_sent = reminder_3
        user.factfind_completed = factfind
        user.monthly_income = 2000
        user.rent_amount = 800
        user.bills_amount = 200
        user.subscription_status = "trialing"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _add_checkin(app, user_id, month, year):
    with app.app_context():
        ci = CheckIn(user_id=user_id, month=month, year=year)
        db.session.add(ci)
        db.session.commit()
        return ci.id


def _login(client, email="forgive@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


# ─── Detection logic ─────────────────────────────────────────


class TestForgivenessDetection:
    """Pure-function tests for get_forgiveness_target."""

    def test_in_window_returns_none(self, app):
        """Inside the last 3 days of the month, the standard form
        already targets the previous month — no forgiveness needed."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app, payday_sent=date(2026, 4, 15),
                         reminder_1=date(2026, 4, 18))
        with app.app_context():
            user = db.session.get(User, uid)
            # May 30 is in the standard window (29-31).
            assert get_forgiveness_target(user, date(2026, 5, 30)) is None

    def test_no_reminders_ever_returns_none(self, app):
        """A user who never got a reminder shouldn't see forgiveness —
        they're not the audience."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app, payday_sent=date(2026, 4, 15))
        with app.app_context():
            user = db.session.get(User, uid)
            assert get_forgiveness_target(user, date(2026, 5, 7)) is None

    def test_brand_new_user_returns_none(self, app):
        """Never had a pay-day notification, no reminders. Closed
        state is correct, not forgiveness."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            assert get_forgiveness_target(user, date(2026, 5, 7)) is None

    def test_history_with_april_filed_returns_none(self, app):
        """User filed April. May 7, no reminders for May yet — closed
        state."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app, payday_sent=date(2026, 4, 15),
                         reminder_1=date(2026, 4, 18))
        _add_checkin(app, uid, month=4, year=2026)
        with app.app_context():
            user = db.session.get(User, uid)
            assert get_forgiveness_target(user, date(2026, 5, 7)) is None

    def test_missed_april_with_reminder_returns_april(self, app):
        """User got reminder 1 for April, never filed. May 7 → forgive
        for April."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app, payday_sent=date(2026, 4, 15),
                         reminder_1=date(2026, 4, 18))
        # March was filed but April was missed.
        _add_checkin(app, uid, month=3, year=2026)
        with app.app_context():
            user = db.session.get(User, uid)
            assert get_forgiveness_target(user, date(2026, 5, 7)) == (2026, 4)

    def test_missed_april_no_history_payday_old_returns_april(self, app):
        """No CheckIn ever, but payday was 22 days ago and reminders
        fired. Forgiveness applies."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app, payday_sent=date(2026, 4, 15),
                         reminder_3=date(2026, 4, 29))
        with app.app_context():
            user = db.session.get(User, uid)
            assert get_forgiveness_target(user, date(2026, 5, 7)) == (2026, 4)

    def test_missed_april_no_history_payday_recent_returns_none(self, app):
        """No CheckIn ever, payday was only 6 days ago — too soon.
        The user is just early; let the closed state guide them."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app, payday_sent=date(2026, 5, 1),
                         reminder_1=date(2026, 5, 4))
        with app.app_context():
            user = db.session.get(User, uid)
            # Payday May 1, today May 7 — only 6 days. The 14-day floor
            # for the no-history branch keeps fresh users out.
            assert get_forgiveness_target(user, date(2026, 5, 7)) is None

    def test_multiple_missed_months_returns_only_most_recent(self, app):
        """User last checked in for January. Today is May 7. Forgiveness
        only surfaces April — older misses stay missed."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app, payday_sent=date(2026, 4, 15),
                         reminder_1=date(2026, 4, 18),
                         reminder_2=date(2026, 4, 22),
                         reminder_3=date(2026, 4, 29))
        _add_checkin(app, uid, month=1, year=2026)
        with app.app_context():
            user = db.session.get(User, uid)
            assert get_forgiveness_target(user, date(2026, 5, 7)) == (2026, 4)

    def test_january_wraps_to_december_previous_year(self, app):
        """today=Jan 7, previous month is Dec of last year."""
        from app.services.checkin_service import get_forgiveness_target

        uid = _make_user(app, payday_sent=date(2025, 12, 15),
                         reminder_1=date(2025, 12, 18))
        with app.app_context():
            user = db.session.get(User, uid)
            assert get_forgiveness_target(user, date(2026, 1, 7)) == (2025, 12)


class TestRetroactiveWindow:

    def test_recent_target_accepted(self, app):
        from app.services.checkin_service import is_within_retroactive_window
        with app.app_context():
            assert is_within_retroactive_window(2026, 4, today=date(2026, 5, 7))

    def test_target_beyond_60_days_rejected(self, app):
        from app.services.checkin_service import is_within_retroactive_window
        with app.app_context():
            # Feb 1 → May 7 is ~95 days, beyond the 60-day cap.
            assert is_within_retroactive_window(2026, 2, today=date(2026, 5, 7)) is False

    def test_invalid_month_rejected(self, app):
        from app.services.checkin_service import is_within_retroactive_window
        with app.app_context():
            assert is_within_retroactive_window(2026, 13, today=date(2026, 5, 7)) is False


# ─── Route rendering ─────────────────────────────────────────


class TestForgivenessRouteRendering:

    def test_get_renders_forgiveness_state_and_tracks_event(self, app, client):
        from app.routes import page_routes

        uid = _make_user(
            app, payday_sent=date(2026, 4, 15),
            reminder_1=date(2026, 4, 18),
        )

        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 7)

        with patch.object(page_routes, "date", _FixedDate), \
             patch("app.routes.page_routes.track_event") as track:
            resp = client.get("/check-in?source=reminder")

        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "You missed last month's check-in. That's fine." in body
        assert "Catch up my plan" in body
        assert 'name="target_year" value="2026"' in body
        assert 'name="target_month" value="4"' in body

        events = [c.args[1] for c in track.call_args_list if len(c.args) >= 2]
        assert "forgiveness_state_shown" in events

    def test_forgiveness_state_shown_event_carries_target(self, app, client):
        from app.routes import page_routes

        _make_user(
            app, payday_sent=date(2026, 4, 15),
            reminder_1=date(2026, 4, 18),
        )
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 7)

        with patch.object(page_routes, "date", _FixedDate), \
             patch("app.routes.page_routes.track_event") as track:
            client.get("/check-in")

        forgiveness_calls = [
            c for c in track.call_args_list
            if len(c.args) >= 2 and c.args[1] == "forgiveness_state_shown"
        ]
        assert len(forgiveness_calls) == 1
        props = forgiveness_calls[0].args[2]
        assert props["target_year"] == 2026
        assert props["target_month"] == 4

    def test_get_without_forgiveness_renders_scheduled_state(self, app, client):
        """Without reminders, the existing closed state still renders."""
        from app.routes import page_routes

        _make_user(app)  # No payday, no reminders.
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 7)

        with patch.object(page_routes, "date", _FixedDate):
            resp = client.get("/check-in")

        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "You missed last month's check-in" not in body
        # c060aae dropped the "on" preposition — next_checkin_str is
        # now built as "{day} {month}" (e.g. "15 May") and the
        # template reads "Your next check-in is 15 May".
        assert "Your next check-in is" in body

    def test_get_in_window_does_not_show_forgiveness(self, app, client):
        """Even a user who qualifies for forgiveness sees the standard
        form when we're inside the window — the form already targets
        the previous month, no need for a special header."""
        from app.routes import page_routes

        _make_user(
            app, payday_sent=date(2026, 4, 15),
            reminder_1=date(2026, 4, 18),
        )
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 30)  # in window (last 3 days)

        with patch.object(page_routes, "date", _FixedDate):
            resp = client.get("/check-in")

        body = resp.get_data(as_text=True)
        assert "You missed last month's check-in" not in body
        assert "Confirm check-in" in body


# ─── Submission handling ─────────────────────────────────────


class TestForgivenessSubmission:

    def test_post_writes_checkin_for_target_month(self, app, client):
        """A valid forgiveness POST creates a CheckIn for the target
        month/year, not the current month."""
        from app.routes import page_routes

        uid = _make_user(
            app, payday_sent=date(2026, 4, 15),
            reminder_1=date(2026, 4, 18),
        )
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 7)

        with patch.object(page_routes, "date", _FixedDate):
            resp = client.post("/check-in", data={
                "target_year": "2026",
                "target_month": "4",
            }, follow_redirects=False)

        # Forgiveness submission redirects to /overview.
        assert resp.status_code == 302
        assert "/overview" in resp.headers.get("Location", "")

        with app.app_context():
            ci = CheckIn.query.filter_by(user_id=uid).first()
            assert ci is not None
            assert (ci.year, ci.month) == (2026, 4)

    def test_post_with_was_late_event_property(self, app, client):
        from app.routes import page_routes

        _make_user(
            app, payday_sent=date(2026, 4, 15),
            reminder_1=date(2026, 4, 18),
        )
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 7)

        with patch.object(page_routes, "date", _FixedDate), \
             patch("app.routes.page_routes.track_event") as track:
            client.post("/check-in", data={
                "target_year": "2026",
                "target_month": "4",
            })

        completed = [
            c for c in track.call_args_list
            if len(c.args) >= 2 and c.args[1] == "checkin_completed"
        ]
        assert len(completed) == 1
        assert completed[0].args[2]["was_late"] is True
        assert completed[0].args[2]["month"] == 4
        assert completed[0].args[2]["year"] == 2026

    def test_post_without_target_keeps_was_late_false(self, app, client):
        """Standard in-window submission carries was_late: False."""
        from app.routes import page_routes

        _make_user(app)
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 30)  # in window

        with patch.object(page_routes, "date", _FixedDate), \
             patch("app.routes.page_routes.track_event") as track:
            client.post("/check-in", data={})

        completed = [
            c for c in track.call_args_list
            if len(c.args) >= 2 and c.args[1] == "checkin_completed"
        ]
        assert len(completed) == 1
        assert completed[0].args[2]["was_late"] is False

    def test_post_with_target_user_no_longer_qualifies_redirects(self, app, client):
        """If the user no longer qualifies (e.g. they already filed in
        another tab) the POST is rejected without writing anything."""
        from app.routes import page_routes

        uid = _make_user(app)  # No reminders → no qualification.
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 7)

        with patch.object(page_routes, "date", _FixedDate):
            resp = client.post("/check-in", data={
                "target_year": "2026",
                "target_month": "4",
            }, follow_redirects=False)

        assert resp.status_code == 302
        assert "/check-in" in resp.headers.get("Location", "")

        with app.app_context():
            assert CheckIn.query.filter_by(user_id=uid).count() == 0

    def test_post_with_target_outside_60_day_window_rejected(self, app, client):
        """A stale form left open across cycles must be rejected on
        submit even if the user otherwise qualified."""
        from app.routes import page_routes

        # User qualified for Feb forgiveness back in March, but we're
        # now well past the 60-day catch-up window.
        uid = _make_user(
            app, payday_sent=date(2026, 2, 15),
            reminder_1=date(2026, 2, 18),
        )
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 7)

        with patch.object(page_routes, "date", _FixedDate):
            resp = client.post("/check-in", data={
                "target_year": "2026",
                "target_month": "2",
            }, follow_redirects=False)

        assert resp.status_code == 302
        assert "/check-in" in resp.headers.get("Location", "")

        with app.app_context():
            assert CheckIn.query.filter_by(user_id=uid).count() == 0

    def test_post_with_garbage_target_values_redirects(self, app, client):
        """Non-integer target values are rejected cleanly."""
        from app.routes import page_routes

        uid = _make_user(app)
        _login(client)

        class _FixedDate(date):
            @classmethod
            def today(cls):
                return date(2026, 5, 7)

        with patch.object(page_routes, "date", _FixedDate):
            resp = client.post("/check-in", data={
                "target_year": "abc",
                "target_month": "xyz",
            }, follow_redirects=False)

        assert resp.status_code == 302
        with app.app_context():
            assert CheckIn.query.filter_by(user_id=uid).count() == 0
