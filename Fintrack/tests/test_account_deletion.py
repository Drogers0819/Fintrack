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
from app.models.transaction import Transaction
from app.models.category import Category
from app.services import account_service, analytics_service
from sqlalchemy.exc import IntegrityError


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


class TestDeleteUserAccountSilentFailureRegression:
    """Regression tests for the May 2026 silent-failure incident.

    Production observation (11 May 2026): the wipe-users-by-email CLI was
    invoked with 8 emails and --confirm. The command reported
    "Wiped 8 user(s)" and printed "→ DELETED" for each user. Two days
    later a backfill revealed all 8 users still existed in the database.

    The EXACT upstream trigger (Stripe network blip leaving the session
    in a deactivated state; non-StripeError exception path; transaction
    abort whose COMMIT silently rolled back at the Postgres layer; or
    an identity-map state issue) was NOT pinpointed from code inspection
    alone — production logs would be needed for that. What IS provable
    from the code is that delete_user_account had no post-condition
    verification: it returned True whenever commit() did not raise,
    without confirming the User row was actually absent from the
    database.

    These tests simulate that production SYMPTOM directly — commit
    returns success but the User row remains — and pin the contract
    that delete_user_account returns True ONLY when the row is
    verifiably gone. They do not claim to reproduce the exact upstream
    trigger; they prove the function's defense against any silent-
    failure path that lands in the same state.
    """

    def test_silent_commit_without_persisted_delete_is_caught(self, app):
        """Simulate the production symptom: session.commit() returns
        successfully but the User row remains in the database (because
        the DELETE was never queued for whatever reason — session in
        deactivated state, autoflush race, transaction abort masked
        as COMMIT, etc.). The function must NOT report success in
        that case.

        After the fix, the function must return False (or otherwise
        signal failure) when a post-delete verification finds the row
        still present.
        """
        with app.app_context():
            user = _make_user(email="silent@test.com", subscription_id="sub_x")
            uid = user.id

            # Add some realistic related state so cascade exposure is
            # representative.
            db.session.add(Goal(user_id=uid, name="Emergency Fund",
                                type="savings", target_amount=1000,
                                current_amount=0))
            db.session.add(ChatMessage(user_id=uid, role="user", content="hi"))
            db.session.commit()

            # Neutralise the DELETE: session.delete becomes a no-op,
            # so the subsequent commit() completes without persisting
            # any row removal. This is the production symptom — commit
            # reports success, row remains.
            with patch.object(db.session, "delete", lambda obj: None), \
                 patch.object(account_service, "init_stripe", return_value=False):
                ok = account_service.delete_user_account(uid, reason="cli-wipe")

            # Independent verification against the database, bypassing
            # session identity-map cache.
            db.session.expire_all()
            still_there = User.query.filter_by(id=uid).count() == 1

            assert still_there, (
                "Test setup invariant: simulated silent-failure should leave "
                "the row in place. If this fires, the patch did not behave."
            )
            # CONTRACT: function must NOT report True when the row
            # remains. This is the line that fails on the buggy code
            # (the function trusts a non-raising commit) and must pass
            # after the fix.
            assert ok is False, (
                "delete_user_account reported True while the User row "
                "is still present in the database — the exact silent "
                "failure observed in production on 11 May 2026."
            )

    def test_returns_false_when_user_actually_persists_via_any_path(self, app):
        """Defence-in-depth: regardless of which internal path was
        taken, the function's return value must reflect ground truth
        — the row is gone, or it is not.

        Here we simulate a different upstream trigger: commit() itself
        is patched to a no-op (the rare Postgres edge case where a
        deactivated transaction's COMMIT silently rolls back). The
        contract is identical to the test above — return False, not
        True — but the failure mode is different to prove the fix
        covers more than one mechanism.
        """
        with app.app_context():
            user = _make_user(email="silent2@test.com")
            uid = user.id

            with patch.object(db.session, "commit", lambda: None), \
                 patch.object(account_service, "init_stripe", return_value=False):
                ok = account_service.delete_user_account(uid)

            db.session.rollback()  # clear any pending state from the no-op commit
            db.session.expire_all()
            still_there = User.query.filter_by(id=uid).count() == 1

            assert still_there
            assert ok is False, (
                "Commit returned without raising but the row was not "
                "persisted as deleted — function must report False."
            )

    def test_early_exit_verifies_absence_with_fresh_query(self, app):
        """The `if user is None: return True` early-exit must not
        trust the session's identity-map view alone. A stale/expired
        session can return None for an existing row. The function
        must confirm absence via a fresh database query before
        treating the call as a no-op success.
        """
        with app.app_context():
            user = _make_user(email="ghost@test.com")
            uid = user.id

            # Force db.session.get to return None even though the row
            # exists — mirrors the identity-map issue described in B7.
            with patch.object(db.session, "get", return_value=None):
                ok = account_service.delete_user_account(uid)

            # Row genuinely exists at the database layer.
            db.session.expire_all()
            assert User.query.filter_by(id=uid).count() == 1

            # After fix: function must return False because the fresh
            # query proves the row is still there. Pre-fix, the
            # function returns True from the early-exit path.
            assert ok is False, (
                "Early-exit path returned True while the user row "
                "actually exists — fresh-query verification is missing."
            )


class TestDeleteUserAccountPostFix:
    """Post-fix contract tests covering each branch of delete_user_account.

    Sits alongside the regression class to keep the regression tests
    focused on the silent-failure incident, while these prove the
    rest of the contract — idempotency, real cascade, Stripe error
    tolerance, DB error handling, analytics resilience, and the
    overarching "True ⇒ verifiably gone" invariant.
    """

    def test_idempotent_on_genuinely_missing_user_returns_true(self, app):
        """A user_id that does not exist in the database (fresh-query
        verified) must return True without raising — the GDPR delete
        is idempotent, so a retry after a successful first run is a
        clean no-op."""
        with app.app_context():
            # No user created. Fresh-query check confirms absence.
            assert User.query.filter_by(id=777_777).count() == 0
            ok = account_service.delete_user_account(777_777, reason="retry")
            assert ok is True

    def test_successful_deletion_removes_user_and_cascades_related(self, app):
        """A complete success path: User row gone, all related rows
        cleaned up via cascade. Exercises every model that has a
        user_id FK so any future cascade regression surfaces here."""
        with app.app_context():
            user = _make_user(email="full-cascade@test.com")
            uid = user.id

            goal = Goal(user_id=uid, name="Holiday", type="savings",
                        target_amount=2000, current_amount=100,
                        monthly_allocation=50)
            db.session.add(goal)
            db.session.flush()

            checkin = CheckIn(user_id=uid, month=5, year=2026)
            db.session.add(checkin)
            db.session.flush()

            db.session.add(CheckInEntry(
                checkin_id=checkin.id, goal_id=goal.id,
                pot_name="Holiday", planned_amount=50, actual_amount=50,
            ))
            db.session.add(ChatMessage(user_id=uid, role="user", content="hi"))
            db.session.add(LifeCheckIn(user_id=uid, checkin_type="payday"))

            cat = Category.query.first()
            db.session.add(Transaction(
                user_id=uid, amount=42, description="coffee",
                category_id=cat.id, type="expense", date=date.today(),
            ))
            db.session.commit()

            ok = account_service.delete_user_account(uid, reason="ok")

            assert ok is True
            # Direct DB checks — every related row must be gone.
            assert User.query.filter_by(id=uid).count() == 0
            assert Goal.query.filter_by(user_id=uid).count() == 0
            assert CheckIn.query.filter_by(user_id=uid).count() == 0
            assert ChatMessage.query.filter_by(user_id=uid).count() == 0
            assert LifeCheckIn.query.filter_by(user_id=uid).count() == 0
            assert Transaction.query.filter_by(user_id=uid).count() == 0
            assert CheckInEntry.query.count() == 0

    def test_non_stripeerror_exception_during_cancel_does_not_block_delete(self, app):
        """Stripe call raises a non-StripeError (network library
        exception, SDK regression, etc.). The broadened exception
        handler must swallow it and let the delete proceed. The
        function returns True because the row is verifiably gone."""
        with app.app_context():
            user = _make_user(email="netfail@test.com", subscription_id="sub_x")
            uid = user.id

            import requests
            with patch.object(account_service, "init_stripe", return_value=True), \
                 patch.object(
                     stripe.Subscription, "delete",
                     side_effect=requests.exceptions.ConnectionError("network down"),
                 ):
                ok = account_service.delete_user_account(uid)

            assert ok is True
            assert User.query.filter_by(id=uid).count() == 0

    def test_db_error_during_commit_rolls_back_and_returns_false(self, app):
        """A DB error during commit (constraint violation, deadlock,
        connection drop) must result in: (1) rollback, (2) False
        return, (3) user row preserved. No silent data loss, no
        false success."""
        with app.app_context():
            user = _make_user(email="dberr@test.com")
            uid = user.id

            fake_err = IntegrityError("synthetic", params=None, orig=Exception("boom"))
            with patch.object(account_service, "init_stripe", return_value=False), \
                 patch.object(db.session, "commit", side_effect=fake_err):
                ok = account_service.delete_user_account(uid)

            assert ok is False
            # Row preserved — rollback undid the pending delete.
            db.session.rollback()
            assert User.query.filter_by(id=uid).count() == 1

    def test_track_event_failure_does_not_block_delete(self, app):
        """Analytics tracking must never block the GDPR delete.
        track_event swallows internally today; this guards against a
        future refactor that lets it raise."""
        with app.app_context():
            user = _make_user(email="analytics@test.com")
            uid = user.id

            with patch.object(
                account_service, "track_event",
                side_effect=RuntimeError("posthog SDK regression"),
            ):
                ok = account_service.delete_user_account(uid, reason="bye")

            assert ok is True
            assert User.query.filter_by(id=uid).count() == 0

    def test_core_invariant_true_only_when_row_verifiably_absent(self, app):
        """The over-arching contract. For each of several
        silent-failure simulations, assert the invariant:

            return is True  ⇒  fresh DB query confirms the row is gone

        Equivalently: the function never reports True while the row
        is still in the database. Any future regression that breaks
        this invariant — in any branch — trips this test.
        """
        with app.app_context():
            user_a = _make_user(email="inv_a@test.com")
            user_b = _make_user(email="inv_b@test.com")
            user_c = _make_user(email="inv_c@test.com",
                                subscription_id="sub_inv")
            uid_a, uid_b, uid_c = user_a.id, user_b.id, user_c.id

            scenarios = [
                # (label, context_manager_factory, target_uid)
                (
                    "delete is a no-op",
                    lambda: patch.object(db.session, "delete", lambda obj: None),
                    uid_a,
                ),
                (
                    "commit is a no-op",
                    lambda: patch.object(db.session, "commit", lambda: None),
                    uid_b,
                ),
                (
                    "session.get returns None despite row existing",
                    lambda: patch.object(db.session, "get", return_value=None),
                    uid_c,
                ),
            ]

            for label, ctx_factory, uid in scenarios:
                with patch.object(account_service, "init_stripe",
                                  return_value=False), ctx_factory():
                    result = account_service.delete_user_account(uid)

                db.session.rollback()
                db.session.expire_all()
                row_still_present = User.query.filter_by(id=uid).count() == 1

                # The invariant: True ⇒ row gone.
                if result is True:
                    assert not row_still_present, (
                        f"INVARIANT VIOLATED ({label}): function returned "
                        f"True while user_id={uid} still in database."
                    )
                else:
                    # False is acceptable in any of these scenarios.
                    assert result is False


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
