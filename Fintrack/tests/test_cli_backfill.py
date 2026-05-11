"""
backfill-net-worth CLI command tests.

Covers:
  • Affected user (plan_wizard_complete=True, starting_net_worth=NULL)
    gets backfilled with their current net worth.
  • Idempotent — a second --confirm run is a no-op for users whose
    snapshot is already set.
  • Mid-onboarding users (plan_wizard_complete=False) are skipped.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models.goal import Goal
from app.models.user import User


def _make_user(
    app,
    *,
    email,
    plan_wizard_complete=True,
    starting_net_worth=None,
):
    with app.app_context():
        user = User(email=email, name="Backfill User")
        user.set_password("testpassword123")
        user.factfind_completed = True
        user.plan_wizard_complete = plan_wizard_complete
        user.monthly_income = Decimal("2500")
        if starting_net_worth is not None:
            user.starting_net_worth = Decimal(str(starting_net_worth))
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _add_goal(app, user_id, name, *, target=2000, current=0):
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            target_amount=Decimal(str(target)),
            current_amount=Decimal(str(current)),
            monthly_allocation=Decimal("0"),
            status="active",
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


class TestBackfillCommand:

    def test_affected_user_gets_starting_net_worth_written(self, app):
        """plan_wizard_complete=True + starting_net_worth=NULL → backfilled."""
        uid = _make_user(app, email="affected@test.com")
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)
        _add_goal(app, uid, "Pay off credit card", target=3000, current=0)

        runner = app.test_cli_runner()
        result = runner.invoke(args=["backfill-net-worth", "--confirm"])

        assert result.exit_code == 0
        assert "Backfill complete. 1 user(s) updated." in result.output
        assert f"user_id={uid}" in result.output

        with app.app_context():
            user = db.session.get(User, uid)
            # 500 saved - 3000 debt remaining = -2500.
            assert Decimal(str(user.starting_net_worth)) == Decimal("-2500")

    def test_second_confirm_run_is_no_op(self, app):
        """Idempotency — a second --confirm run finds no affected users
        and does not overwrite the existing snapshot."""
        uid = _make_user(app, email="idem@test.com")
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)

        runner = app.test_cli_runner()
        first = runner.invoke(args=["backfill-net-worth", "--confirm"])
        assert first.exit_code == 0
        assert "1 user(s) updated" in first.output

        with app.app_context():
            user = db.session.get(User, uid)
            original = Decimal(str(user.starting_net_worth))

        # Mutate the user's current net worth after backfill — the
        # second run still must not overwrite.
        _add_goal(app, uid, "Holiday", target=2000, current=200)

        second = runner.invoke(args=["backfill-net-worth", "--confirm"])
        assert second.exit_code == 0
        assert "No users to backfill" in second.output

        with app.app_context():
            user = db.session.get(User, uid)
            assert Decimal(str(user.starting_net_worth)) == original

    def test_skips_users_who_never_completed_onboarding(self, app):
        """plan_wizard_complete=False users are not in scope for the
        backfill — they'll get their snapshot the normal way when they
        finish onboarding."""
        uid_done = _make_user(app, email="done@test.com",
                              plan_wizard_complete=True)
        uid_pending = _make_user(app, email="pending@test.com",
                                 plan_wizard_complete=False)
        _add_goal(app, uid_done, "Emergency fund", target=5000, current=300)
        _add_goal(app, uid_pending, "Emergency fund", target=5000, current=900)

        runner = app.test_cli_runner()
        result = runner.invoke(args=["backfill-net-worth", "--confirm"])

        assert result.exit_code == 0
        assert f"user_id={uid_done}" in result.output
        assert f"user_id={uid_pending}" not in result.output

        with app.app_context():
            done_user = db.session.get(User, uid_done)
            pending_user = db.session.get(User, uid_pending)
            assert done_user.starting_net_worth is not None
            assert pending_user.starting_net_worth is None

    def test_dry_run_does_not_write(self, app):
        """Sanity: --dry-run reports the same users but leaves the
        snapshot column unchanged."""
        uid = _make_user(app, email="dry@test.com")
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)

        runner = app.test_cli_runner()
        result = runner.invoke(args=["backfill-net-worth", "--dry-run"])

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert f"user_id={uid}" in result.output

        with app.app_context():
            user = db.session.get(User, uid)
            assert user.starting_net_worth is None

    def test_refuses_to_run_without_a_flag(self, app):
        """Passing no flag aborts — we never want a quiet write."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=["backfill-net-worth"])
        assert result.exit_code != 0
        assert "Refusing to run" in result.output
