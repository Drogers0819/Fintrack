"""
RecurringContribution service tests.

Covers:
  • sync writes rows + maintains the cached aggregate invariant
  • sync wipes prior rows for the same source on re-sync
  • sync leaves OTHER sources alone
  • Custom entries (chip_id=null) persist correctly
  • Empty / zero-amount entries are silently dropped
  • get_contributions_for_user filtering
  • get_contributions_total returns Decimal sum
  • get_contributions_for_goal returns only linked rows
  • Goal deletion sets linked_goal_id to NULL (cascade behaviour)
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models.goal import Goal
from app.models.recurring_contribution import RecurringContribution
from app.models.user import User


def _make_user(app, email="rc@test.com"):
    with app.app_context():
        user = User(email=email, name="RC User")
        user.set_password("testpassword123")
        user.factfind_completed = True
        user.monthly_income = Decimal("2500")
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _make_goal(app, user_id, name="House deposit"):
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            target_amount=Decimal("20000"),
            current_amount=Decimal("500"),
            monthly_allocation=Decimal("200"),
            status="active",
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


class TestSync:

    def test_creates_rows_for_standard_chips(self, app):
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={
                    "lisa": {"label": "LISA contributions", "amount": 200},
                    "pension": {"label": "Pension (additional)", "amount": 150},
                },
                custom_entries=None,
            )
            rows = RecurringContribution.query.filter_by(user_id=uid).all()
            labels = {r.label for r in rows}
            assert labels == {"LISA contributions", "Pension (additional)"}
            for r in rows:
                assert r.source == "other_commitments"
                assert r.chip_id in ("lisa", "pension")

    def test_creates_rows_for_custom_entries(self, app):
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data=None,
                custom_entries=[
                    {"label": "Local gym", "amount": 35},
                    {"label": "Times subscription", "amount": 12.50},
                ],
            )
            rows = RecurringContribution.query.filter_by(user_id=uid).all()
            assert len(rows) == 2
            for r in rows:
                assert r.chip_id is None
                assert r.source == "subscriptions"

    def test_resync_replaces_existing_rows(self, app):
        """A second sync for the same source wipes prior rows. No
        duplicates, no stale data."""
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={"netflix": {"label": "Netflix", "amount": 10.99}},
                custom_entries=None,
            )
            # Re-sync with different chips.
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={"spotify": {"label": "Spotify", "amount": 10.99}},
                custom_entries=None,
            )
            rows = RecurringContribution.query.filter_by(user_id=uid).all()
            assert len(rows) == 1
            assert rows[0].chip_id == "spotify"

    def test_resync_leaves_other_source_alone(self, app):
        """Syncing subscriptions must NOT touch other_commitments rows."""
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={"lisa": {"label": "LISA contributions", "amount": 200}},
                custom_entries=None,
            )
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={"netflix": {"label": "Netflix", "amount": 11}},
                custom_entries=None,
            )
            all_rows = RecurringContribution.query.filter_by(user_id=uid).all()
            sources = {r.source for r in all_rows}
            assert sources == {"other_commitments", "subscriptions"}
            assert len(all_rows) == 2

    def test_zero_and_blank_entries_are_dropped(self, app):
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={
                    "lisa": {"label": "LISA contributions", "amount": 200},
                    "pension": {"label": "Pension", "amount": 0},  # dropped
                    "isa": {"label": "ISA", "amount": -5},          # dropped
                },
                custom_entries=[
                    {"label": "Valid custom", "amount": 50},
                    {"label": "", "amount": 75},                     # dropped (blank label)
                    {"label": "Zero amount", "amount": 0},           # dropped
                ],
            )
            rows = RecurringContribution.query.filter_by(user_id=uid).all()
            labels = {r.label for r in rows}
            assert labels == {"LISA contributions", "Valid custom"}

    def test_empty_sync_clears_rows(self, app):
        """A sync with no entries wipes the source and writes 0 to the cache."""
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={"netflix": {"label": "Netflix", "amount": 11}},
                custom_entries=None,
            )
            # Re-sync with nothing.
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={},
                custom_entries=[],
            )
            rows = RecurringContribution.query.filter_by(
                user_id=uid, source="subscriptions",
            ).all()
            assert rows == []
            user = db.session.get(User, uid)
            assert Decimal(str(user.subscriptions_total)) == Decimal("0")


class TestCachedAggregate:

    def test_aggregate_matches_sum_of_rows(self, app):
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={
                    "netflix": {"label": "Netflix", "amount": 10.99},
                    "spotify": {"label": "Spotify", "amount": 10.99},
                },
                custom_entries=[{"label": "The Times", "amount": 12}],
            )
            user = db.session.get(User, uid)
            # 10.99 + 10.99 + 12 = 33.98
            assert Decimal(str(user.subscriptions_total)) == Decimal("33.98")

    def test_aggregate_is_independent_per_source(self, app):
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={"netflix": {"label": "Netflix", "amount": 11}},
                custom_entries=None,
            )
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={"lisa": {"label": "LISA contributions", "amount": 200}},
                custom_entries=None,
            )
            user = db.session.get(User, uid)
            assert Decimal(str(user.subscriptions_total)) == Decimal("11")
            assert Decimal(str(user.other_commitments)) == Decimal("200")

    def test_recompute_helper_writes_back(self, app):
        """recompute_cached_aggregate forces a recompute from current
        rows. Used by the backfill CLI."""
        from app.services.recurring_contribution_service import (
            recompute_cached_aggregate,
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={"netflix": {"label": "Netflix", "amount": 11}},
                custom_entries=None,
            )
            # Deliberately scribble a wrong value on the cache.
            user.subscriptions_total = Decimal("0")
            db.session.commit()

            total = recompute_cached_aggregate(user, "subscriptions")
            user = db.session.get(User, uid)
            assert total == Decimal("11.00")
            assert Decimal(str(user.subscriptions_total)) == Decimal("11.00")


class TestLookups:

    def test_get_contributions_filters_by_source(self, app):
        from app.services.recurring_contribution_service import (
            get_contributions_for_user,
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={"netflix": {"label": "Netflix", "amount": 11}},
                custom_entries=None,
            )
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={"lisa": {"label": "LISA contributions", "amount": 200}},
                custom_entries=None,
            )
            subs = get_contributions_for_user(user, source="subscriptions")
            others = get_contributions_for_user(user, source="other_commitments")
            all_rows = get_contributions_for_user(user)
            assert [r.chip_id for r in subs] == ["netflix"]
            assert [r.chip_id for r in others] == ["lisa"]
            assert len(all_rows) == 2

    def test_get_contributions_for_goal_returns_only_linked(self, app):
        """Linked contributions vs unlinked must split cleanly."""
        from app.services.recurring_contribution_service import (
            get_contributions_for_goal,
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        gid = _make_goal(app, uid, name="House deposit")
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={
                    "lisa": {"label": "LISA contributions", "amount": 200},
                    "pension": {"label": "Pension", "amount": 150},
                },
                custom_entries=None,
            )
            # Link only the LISA row to the House goal.
            lisa = RecurringContribution.query.filter_by(
                user_id=uid, chip_id="lisa",
            ).first()
            lisa.linked_goal_id = gid
            db.session.commit()

            goal = db.session.get(Goal, gid)
            linked = get_contributions_for_goal(goal)
            assert [r.chip_id for r in linked] == ["lisa"]


class TestCascadeBehaviour:

    def test_deleting_goal_unlinks_contribution(self, app):
        """linked_goal_id is ON DELETE SET NULL. Deleting the linked
        goal must leave the contribution intact with linked_goal_id=NULL."""
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        gid = _make_goal(app, uid)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={"lisa": {"label": "LISA contributions", "amount": 200}},
                custom_entries=None,
            )
            lisa = RecurringContribution.query.filter_by(user_id=uid).first()
            lisa.linked_goal_id = gid
            db.session.commit()

            # Delete the goal.
            goal = db.session.get(Goal, gid)
            db.session.delete(goal)
            db.session.commit()

            # Contribution survives; link cleared.
            lisa = db.session.get(RecurringContribution, lisa.id)
            assert lisa is not None
            assert lisa.linked_goal_id is None

    def test_deleting_user_deletes_contributions(self, app):
        """user_id is ON DELETE CASCADE — deleting the user wipes
        their contributions too."""
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "subscriptions",
                chip_data={"netflix": {"label": "Netflix", "amount": 11}},
                custom_entries=None,
            )
            assert RecurringContribution.query.filter_by(user_id=uid).count() == 1

            db.session.delete(user)
            db.session.commit()

            assert RecurringContribution.query.filter_by(user_id=uid).count() == 0


# ─── Companion context (Commit 3) ────────────────────────────


class TestCompanionContext:
    """Linked contributions surface in the AI companion's per-user
    context block. Without this, the AI would have a different
    mental model of the user's commitments than the UI shows."""

    def test_linked_contribution_appears_in_user_context(self, app):
        from app.services.companion_service import _build_user_context
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        gid = _make_goal(app, uid, name="House deposit")
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={"lisa": {"label": "LISA contributions", "amount": 200}},
                custom_entries=None,
            )
            lisa = RecurringContribution.query.filter_by(user_id=uid).first()
            lisa.linked_goal_id = gid
            db.session.commit()

            context = _build_user_context(user)
            assert "Recurring contributions linked to goals" in context
            assert "LISA contributions" in context
            assert "House deposit" in context

    def test_unlinked_contributions_not_in_linked_summary(self, app):
        """Unlinked contributions are still represented in the
        rolled-up other_commitments scalar line; they should NOT
        appear in the dedicated linked-summary section."""
        from app.services.companion_service import _build_user_context
        from app.services.recurring_contribution_service import (
            sync_contributions_from_factfind,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            sync_contributions_from_factfind(
                user, "other_commitments",
                chip_data={"lisa": {"label": "LISA contributions", "amount": 200}},
                custom_entries=None,
            )
            context = _build_user_context(user)
            assert "Recurring contributions linked to goals" not in context
