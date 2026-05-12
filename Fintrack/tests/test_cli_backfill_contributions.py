"""
backfill-recurring-contributions CLI command tests.

Migration for the RecurringContribution refactor. For each user
with a non-zero rolled-up scalar but no per-source rows, creates a
single "Legacy contributions" row preserving the amount.

Tests cover:
  • Affected user (non-zero scalar, no rows) gets a Legacy row.
  • User with rows already present is skipped for that source.
  • Mixed case: user has rows for one source, not the other.
  • Zero / NULL scalars are skipped (no spurious zero rows).
  • Required-flag enforcement matches the pattern of the other CLI
    commands (--confirm needed; --dry-run also accepted; bare call
    aborts).
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models.recurring_contribution import RecurringContribution
from app.models.user import User


def _make_user(
    app,
    *,
    email,
    subscriptions_total=None,
    other_commitments=None,
):
    with app.app_context():
        user = User(email=email, name="Backfill User")
        user.set_password("testpassword123")
        user.factfind_completed = True
        user.plan_wizard_complete = True
        user.monthly_income = Decimal("2500")
        if subscriptions_total is not None:
            user.subscriptions_total = Decimal(str(subscriptions_total))
        if other_commitments is not None:
            user.other_commitments = Decimal(str(other_commitments))
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


class TestBackfillCommand:

    def test_aborts_without_flag(self, app):
        runner = app.test_cli_runner()
        result = runner.invoke(args=["backfill-recurring-contributions"])
        assert result.exit_code != 0
        assert "Refusing to run" in result.output

    def test_dry_run_does_not_write(self, app):
        uid = _make_user(app, email="dry@test.com", other_commitments=200)
        runner = app.test_cli_runner()
        result = runner.invoke(
            args=["backfill-recurring-contributions", "--dry-run"],
        )
        assert result.exit_code == 0
        assert f"user_id={uid}" in result.output
        assert "would write" in result.output

        with app.app_context():
            assert RecurringContribution.query.filter_by(user_id=uid).count() == 0

    def test_confirm_creates_legacy_row_for_non_zero_scalar(self, app):
        uid = _make_user(
            app, email="confirm@test.com",
            other_commitments=200,
        )
        runner = app.test_cli_runner()
        result = runner.invoke(
            args=["backfill-recurring-contributions", "--confirm"],
        )
        assert result.exit_code == 0
        assert "1 Legacy row(s) created" in result.output

        with app.app_context():
            rows = RecurringContribution.query.filter_by(user_id=uid).all()
            assert len(rows) == 1
            assert rows[0].source == "other_commitments"
            assert rows[0].chip_id is None
            assert "Legacy contributions" in rows[0].label
            assert Decimal(str(rows[0].amount)) == Decimal("200")

    def test_mixed_case_user_with_one_source_already_synced(self, app):
        """User has subscriptions rows already (post-refactor sync)
        but their other_commitments scalar predates that sync. Only
        the other_commitments source gets backfilled."""
        uid = _make_user(
            app, email="mixed@test.com",
            subscriptions_total=11,
            other_commitments=200,
        )
        with app.app_context():
            # Pre-existing subscriptions row.
            db.session.add(RecurringContribution(
                user_id=uid,
                source="subscriptions",
                chip_id="netflix",
                label="Netflix",
                amount=Decimal("11"),
                linked_goal_id=None,
            ))
            db.session.commit()

        runner = app.test_cli_runner()
        result = runner.invoke(
            args=["backfill-recurring-contributions", "--confirm"],
        )
        assert result.exit_code == 0
        # Only the other_commitments backfill should happen.
        assert "1 Legacy row(s) created" in result.output

        with app.app_context():
            subs = RecurringContribution.query.filter_by(
                user_id=uid, source="subscriptions",
            ).all()
            others = RecurringContribution.query.filter_by(
                user_id=uid, source="other_commitments",
            ).all()
            assert len(subs) == 1
            assert subs[0].chip_id == "netflix"  # untouched
            assert len(others) == 1
            assert others[0].chip_id is None
            assert "Legacy" in others[0].label

    def test_user_with_zero_or_null_scalar_is_skipped(self, app):
        """Pre-launch founder accounts typically have no factfind
        commitments. They must not get spurious zero-amount Legacy
        rows."""
        _make_user(app, email="zero@test.com", other_commitments=0)
        _make_user(app, email="null@test.com")  # both None

        runner = app.test_cli_runner()
        result = runner.invoke(
            args=["backfill-recurring-contributions", "--confirm"],
        )
        assert result.exit_code == 0
        assert "No users to backfill" in result.output

        with app.app_context():
            assert RecurringContribution.query.count() == 0

    def test_second_run_is_idempotent(self, app):
        """Re-running after the first --confirm finds zero users to
        backfill (the rows it created in run 1 satisfy the
        'already-has-rows' skip)."""
        uid = _make_user(app, email="idem@test.com", other_commitments=200)
        runner = app.test_cli_runner()
        first = runner.invoke(
            args=["backfill-recurring-contributions", "--confirm"],
        )
        second = runner.invoke(
            args=["backfill-recurring-contributions", "--confirm"],
        )
        assert first.exit_code == 0
        assert "1 Legacy row(s) created" in first.output

        assert second.exit_code == 0
        assert "No users to backfill" in second.output

        with app.app_context():
            # Still only one row.
            assert RecurringContribution.query.filter_by(user_id=uid).count() == 1
