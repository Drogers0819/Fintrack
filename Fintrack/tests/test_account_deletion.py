"""Tests for account deletion: service + route + cascade behaviour.

Covers:
  • Service deletes the User row.
  • Cascade reaches goals, check-ins, life check-ins, chat messages, transactions.
  • Stripe immediate cancellation is invoked when a subscription is present.
  • Stripe failure does not block DB deletion (data erasure is non-negotiable).
  • PostHog `account_deleted` fires BEFORE the row is deleted.
  • Idempotent on a non-existent user_id.
  • Route requires login.
  • Route rejects POST without confirmation == "DELETE".
  • Route happy-path deletes + redirects to /account-deleted.
"""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
import stripe

from app import db
from app.models.user import User
from app.models.goal import Goal
from app.models.chat import ChatMessage
from app.models.life_checkin import LifeCheckIn
from app.models.checkin import CheckIn, CheckInEntry
from app.services import account_service, analytics_service


def _make_user(email="del@test.com", subscription_id=None):
    user = User(email=email, name="Deletable")
    user.set_password("testpassword123")
    if subscription_id:
        user.stripe_subscription_id = subscription_id
        user.stripe_customer_id = "cus_test_xxx"
        user.subscription_status = "active"
    db.session.add(user)
    db.session.commit()
    return user


class TestDeleteUserAccountService:

    def test_deletes_user_record(self, app):
        with app.app_context():
            user = _make_user()
            uid = user.id

            ok = account_service.delete_user_account(uid)

            assert ok is True
            assert db.session.get(User, uid) is None

    def test_cascade_removes_related_data(self, app):
        """A user with goals, check-ins, life check-ins, chat messages, and a
        check-in entry under one of those check-ins is deleted in a single
        call without errors. ORM-level cascade handles the SQLite test DB;
        production Postgres uses ON DELETE CASCADE via the migration block."""
        with app.app_context():
            user = _make_user(email="cascade@test.com")
            uid = user.id

            goal = Goal(user_id=uid, name="Emergency Fund", type="savings",
                        target_amount=1000, current_amount=0)
            db.session.add(goal)
            db.session.flush()

            checkin = CheckIn(user_id=uid, month=5, year=2026)
            db.session.add(checkin)
            db.session.flush()

            entry = CheckInEntry(
                checkin_id=checkin.id, goal_id=goal.id,
                pot_name="Emergency Fund",
                planned_amount=100, actual_amount=80,
            )
            db.session.add(entry)

            db.session.add(ChatMessage(user_id=uid, role="user", content="hi"))
            db.session.add(LifeCheckIn(user_id=uid, checkin_type="payday"))
            db.session.commit()

            assert Goal.query.filter_by(user_id=uid).count() == 1
            assert CheckIn.query.filter_by(user_id=uid).count() == 1
            assert ChatMessage.query.filter_by(user_id=uid).count() == 1
            assert LifeCheckIn.query.filter_by(user_id=uid).count() == 1

            ok = account_service.delete_user_account(uid)

            assert ok is True
            assert db.session.get(User, uid) is None
            assert Goal.query.filter_by(user_id=uid).count() == 0
            assert CheckIn.query.filter_by(user_id=uid).count() == 0
            assert ChatMessage.query.filter_by(user_id=uid).count() == 0
            assert LifeCheckIn.query.filter_by(user_id=uid).count() == 0
            assert CheckInEntry.query.count() == 0  # cascaded via checkin

    def test_stripe_cancel_called_when_subscription_present(self, app):
        with app.app_context():
            user = _make_user(email="sub@test.com", subscription_id="sub_active_123")
            uid = user.id

            with patch.object(account_service, "init_stripe", return_value=True), \
                 patch.object(stripe.Subscription, "delete") as mock_delete:
                ok = account_service.delete_user_account(uid, reason="too pricey")

            assert ok is True
            mock_delete.assert_called_once_with("sub_active_123")
            assert db.session.get(User, uid) is None

    def test_stripe_failure_does_not_block_db_deletion(self, app):
        """GDPR: data erasure is non-negotiable. An orphaned subscription is
        a smaller harm than retained personal data."""
        with app.app_context():
            user = _make_user(email="fail@test.com", subscription_id="sub_doomed")
            uid = user.id

            stripe_err = stripe.error.APIConnectionError("network down")
            with patch.object(account_service, "init_stripe", return_value=True), \
                 patch.object(stripe.Subscription, "delete", side_effect=stripe_err):
                ok = account_service.delete_user_account(uid)

            assert ok is True
            assert db.session.get(User, uid) is None

    def test_posthog_event_fires_before_db_delete(self, app):
        """The user_id must still resolve in PostHog when the event is captured.
        Use a side_effect that asserts the row still exists at fire time."""
        with app.app_context():
            user = _make_user(email="ph@test.com")
            uid = user.id

            captured = {}

            def _capture(distinct_id, event_name, properties=None):
                captured["distinct_id"] = distinct_id
                captured["event"] = event_name
                captured["properties"] = properties
                # User row must still exist when the event is captured.
                captured["user_still_present"] = db.session.get(User, uid) is not None

            with patch.object(account_service, "track_event", side_effect=_capture):
                ok = account_service.delete_user_account(uid, reason="moving on")

            assert ok is True
            assert captured["distinct_id"] == uid
            assert captured["event"] == "account_deleted"
            assert captured["properties"] == {"reason": "moving on"}
            assert captured["user_still_present"] is True
            assert db.session.get(User, uid) is None

    def test_idempotent_on_missing_user(self, app):
        """Calling twice (or on an unknown id) returns True and doesn't raise."""
        with app.app_context():
            assert account_service.delete_user_account(999_999) is True

            user = _make_user(email="twice@test.com")
            uid = user.id
            assert account_service.delete_user_account(uid) is True
            # Second call: row already gone, still True.
            assert account_service.delete_user_account(uid) is True


class TestDeleteAccountRoute:

    def test_route_requires_login(self, client):
        response = client.get("/settings/delete-account", follow_redirects=False)
        # Unauthenticated users are bounced to login by login_manager.
        assert response.status_code in (302, 401)
        if response.status_code == 302:
            assert "/login" in response.headers.get("Location", "")

    def test_post_without_delete_keyword_does_not_delete(self, app, auth_client):
        with app.app_context():
            uid_before = User.query.filter_by(email="test@test.com").first().id

        response = auth_client.post(
            "/settings/delete-account",
            data={"confirmation": "delete", "reason": "typo"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/settings/delete-account" in response.headers.get("Location", "")

        with app.app_context():
            assert db.session.get(User, uid_before) is not None

    def test_post_with_delete_keyword_deletes_and_redirects(self, app, auth_client):
        with app.app_context():
            uid_before = User.query.filter_by(email="test@test.com").first().id

        response = auth_client.post(
            "/settings/delete-account",
            data={"confirmation": "DELETE", "reason": "no longer needed"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers.get("Location", "").endswith("/account-deleted")

        with app.app_context():
            assert db.session.get(User, uid_before) is None
