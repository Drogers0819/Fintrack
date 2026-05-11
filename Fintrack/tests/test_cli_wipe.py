"""
wipe-users-by-email CLI command tests.

Destructive command — every test verifies a safety property:
  • Missing --confirm aborts (dry-run path doesn't write).
  • Missing --email aborts before any DB read.
  • With --confirm, the listed users are deleted along with related rows.
  • Non-listed users are untouched.
  • Re-running after partial completion is idempotent: missing emails
    are skipped, present emails still get deleted.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import db
from app.models.checkin import CheckIn
from app.models.goal import Goal
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.user import User


def _make_user(app, email, name="Wipe User"):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.factfind_completed = True
        user.monthly_income = Decimal("2500")
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _add_goal(app, user_id, name="Holiday"):
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            target_amount=Decimal("2000"),
            current_amount=Decimal("100"),
            monthly_allocation=Decimal("100"),
            status="active",
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


def _add_checkin(app, user_id, month=5, year=2026):
    with app.app_context():
        ci = CheckIn(user_id=user_id, month=month, year=year)
        db.session.add(ci)
        db.session.commit()
        return ci.id


def _add_transaction(app, user_id, amount=50):
    """Add a transaction. Picks an existing category from the seed list
    (which conftest already seeds for the test DB)."""
    with app.app_context():
        cat = Category.query.first()
        if cat is None:
            cat = Category(name="Other")
            db.session.add(cat)
            db.session.commit()
        txn = Transaction(
            user_id=user_id,
            amount=Decimal(str(amount)),
            description="test",
            category_id=cat.id,
            type="expense",
            date=datetime.utcnow().date(),
        )
        db.session.add(txn)
        db.session.commit()
        return txn.id


class TestWipeCommand:

    def test_aborts_when_no_email_provided(self, app):
        runner = app.test_cli_runner()
        result = runner.invoke(args=["wipe-users-by-email", "--confirm"])
        assert result.exit_code != 0
        assert "No emails provided" in result.output

    def test_aborts_when_email_is_blank(self, app):
        """A whitespace-only --email value should not silently pass through."""
        runner = app.test_cli_runner()
        result = runner.invoke(
            args=["wipe-users-by-email", "--email", "   ", "--confirm"],
        )
        assert result.exit_code != 0
        assert "blank after trimming" in result.output

    def test_dry_run_when_confirm_missing_does_not_delete(self, app):
        """Without --confirm, the command prints the plan and exits."""
        uid = _make_user(app, email="target@test.com")
        runner = app.test_cli_runner()
        result = runner.invoke(
            args=["wipe-users-by-email", "--email", "target@test.com"],
        )
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "will be deleted" in result.output
        assert "Re-run with --confirm" in result.output
        # User still present.
        with app.app_context():
            assert db.session.get(User, uid) is not None

    def test_confirm_deletes_listed_user(self, app):
        uid = _make_user(app, email="target@test.com")
        runner = app.test_cli_runner()
        with patch("app.services.account_service.init_stripe", return_value=False), \
             patch("app.services.account_service.track_event"):
            result = runner.invoke(
                args=[
                    "wipe-users-by-email",
                    "--email", "target@test.com",
                    "--confirm",
                ],
            )
        assert result.exit_code == 0
        assert "DELETED" in result.output
        assert "1 user(s) deleted" in result.output
        with app.app_context():
            assert db.session.get(User, uid) is None

    def test_preserves_non_listed_users(self, app):
        """Users not in the email list must remain untouched."""
        uid_target = _make_user(app, email="target@test.com")
        uid_preserve_a = _make_user(app, email="founder.a@test.com")
        uid_preserve_b = _make_user(app, email="founder.b@test.com")

        runner = app.test_cli_runner()
        with patch("app.services.account_service.init_stripe", return_value=False), \
             patch("app.services.account_service.track_event"):
            result = runner.invoke(
                args=[
                    "wipe-users-by-email",
                    "--email", "target@test.com",
                    "--confirm",
                ],
            )
        assert result.exit_code == 0
        with app.app_context():
            assert db.session.get(User, uid_target) is None
            assert db.session.get(User, uid_preserve_a) is not None
            assert db.session.get(User, uid_preserve_b) is not None

    def test_cleans_up_related_records(self, app):
        """Deleting a user must cascade-delete their goals, check-ins,
        and transactions. The existing FK CASCADE handles this in
        Postgres; the SQLite test DB has the FK pragma on (set in
        app/__init__) so the same cascade fires here."""
        uid = _make_user(app, email="rich@test.com")
        _add_goal(app, uid, name="Holiday")
        _add_goal(app, uid, name="Emergency fund")
        _add_checkin(app, uid)
        _add_transaction(app, uid, amount=99)

        with app.app_context():
            assert Goal.query.filter_by(user_id=uid).count() == 2
            assert CheckIn.query.filter_by(user_id=uid).count() == 1
            assert Transaction.query.filter_by(user_id=uid).count() == 1

        runner = app.test_cli_runner()
        with patch("app.services.account_service.init_stripe", return_value=False), \
             patch("app.services.account_service.track_event"):
            result = runner.invoke(
                args=[
                    "wipe-users-by-email",
                    "--email", "rich@test.com",
                    "--confirm",
                ],
            )
        assert result.exit_code == 0
        with app.app_context():
            assert db.session.get(User, uid) is None
            assert Goal.query.filter_by(user_id=uid).count() == 0
            assert CheckIn.query.filter_by(user_id=uid).count() == 0
            assert Transaction.query.filter_by(user_id=uid).count() == 0

    def test_idempotent_rerun_skips_already_deleted(self, app):
        """A second run with the same emails finds nothing to delete
        and reports cleanly. The 'not found, skipping' line proves the
        idempotency contract."""
        uid = _make_user(app, email="ghost@test.com")
        _make_user(app, email="other@test.com")  # preserved across both runs

        runner = app.test_cli_runner()
        with patch("app.services.account_service.init_stripe", return_value=False), \
             patch("app.services.account_service.track_event"):
            first = runner.invoke(
                args=[
                    "wipe-users-by-email",
                    "--email", "ghost@test.com",
                    "--confirm",
                ],
            )
            second = runner.invoke(
                args=[
                    "wipe-users-by-email",
                    "--email", "ghost@test.com",
                    "--confirm",
                ],
            )

        assert first.exit_code == 0
        assert "1 user(s) deleted" in first.output

        assert second.exit_code == 0
        assert "not found, skipping" in second.output
        assert "0 user(s) deleted" in second.output

        with app.app_context():
            assert db.session.get(User, uid) is None

    def test_multiple_emails_in_one_run(self, app):
        """The real-world invocation passes multiple --email flags."""
        uid_a = _make_user(app, email="a@test.com")
        uid_b = _make_user(app, email="b@test.com")
        uid_keep = _make_user(app, email="keep@test.com")

        runner = app.test_cli_runner()
        with patch("app.services.account_service.init_stripe", return_value=False), \
             patch("app.services.account_service.track_event"):
            result = runner.invoke(
                args=[
                    "wipe-users-by-email",
                    "--email", "a@test.com",
                    "--email", "b@test.com",
                    "--confirm",
                ],
            )
        assert result.exit_code == 0
        assert "2 user(s) deleted" in result.output

        with app.app_context():
            assert db.session.get(User, uid_a) is None
            assert db.session.get(User, uid_b) is None
            assert db.session.get(User, uid_keep) is not None

    def test_dedupes_repeated_emails_in_input(self, app):
        """Same email passed twice (or once with different case) is
        normalised to one deletion."""
        uid = _make_user(app, email="dup@test.com")
        runner = app.test_cli_runner()
        with patch("app.services.account_service.init_stripe", return_value=False), \
             patch("app.services.account_service.track_event"):
            result = runner.invoke(
                args=[
                    "wipe-users-by-email",
                    "--email", "dup@test.com",
                    "--email", "DUP@test.com",
                    "--confirm",
                ],
            )
        assert result.exit_code == 0
        # Only one deletion, no second-pass "not found" because dedupe
        # happens before the lookup loop.
        assert "1 user(s) deleted" in result.output
        with app.app_context():
            assert db.session.get(User, uid) is None
