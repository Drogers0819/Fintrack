"""
Net worth service tests.

Covers:
  • compute_current_net_worth — mix of savings + debts, debt-only,
    savings-only, completion edge cases.
  • compute_progress — zero immediately after snapshot, positive
    after savings contributions, positive after debt payoff.
  • snapshot_starting_net_worth — captured once, never overwritten.
  • get_net_worth_summary — dict shape, has_started flag, exact
    arithmetic identity (current - starting == progress).
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models.goal import Goal
from app.models.user import User


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(app, *, email="nw@test.com", name="NW User", starting=None):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.factfind_completed = True
        user.monthly_income = Decimal("2500")
        if starting is not None:
            user.starting_net_worth = Decimal(str(starting))
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _add_goal(
    app,
    user_id,
    name,
    *,
    target=2000,
    current=0,
    status="active",
):
    """All goals created in onboarding get type='savings_target' regardless
    of whether they're savings or debt goals. The debt classification is
    by name; this helper mirrors that production reality."""
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            target_amount=Decimal(str(target)),
            current_amount=Decimal(str(current)),
            monthly_allocation=Decimal("0"),
            status=status,
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


# ─── compute_current_net_worth ───────────────────────────────


class TestComputeCurrentNetWorth:

    def test_mix_of_savings_and_debt(self, app):
        """£500 saved minus £3,000 credit card debt = -£2,500."""
        from app.services.net_worth_service import compute_current_net_worth
        uid = _make_user(app)
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)
        _add_goal(app, uid, "Pay off credit card", target=3000, current=0)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_current_net_worth(user) == Decimal("-2500")

    def test_only_debts_returns_negative(self, app):
        from app.services.net_worth_service import compute_current_net_worth
        uid = _make_user(app)
        _add_goal(app, uid, "Pay off credit card", target=2000, current=0)
        _add_goal(app, uid, "Pay off overdraft", target=500, current=0)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_current_net_worth(user) == Decimal("-2500")

    def test_only_savings_returns_positive(self, app):
        from app.services.net_worth_service import compute_current_net_worth
        uid = _make_user(app)
        _add_goal(app, uid, "Emergency fund", target=5000, current=800)
        _add_goal(app, uid, "House deposit", target=20000, current=1200)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_current_net_worth(user) == Decimal("2000")

    def test_zero_balanced(self, app):
        """£1,000 savings + £1,000 debt → net worth zero."""
        from app.services.net_worth_service import compute_current_net_worth
        uid = _make_user(app)
        _add_goal(app, uid, "Emergency fund", target=5000, current=1000)
        _add_goal(app, uid, "Pay off credit card", target=1000, current=0)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_current_net_worth(user) == Decimal("0")

    def test_no_goals_returns_zero(self, app):
        from app.services.net_worth_service import compute_current_net_worth
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_current_net_worth(user) == Decimal("0")

    def test_savings_goal_completed_status_still_counted(self, app):
        """A completed Emergency Fund still holds £3,000 — that's an
        asset and the user still has it. Status filter does NOT apply
        to the asset side."""
        from app.services.net_worth_service import compute_current_net_worth
        uid = _make_user(app)
        _add_goal(
            app, uid, "Emergency fund",
            target=3000, current=3000, status="completed",
        )
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_current_net_worth(user) == Decimal("3000")

    def test_paid_off_debt_drops_out_naturally(self, app):
        """A debt goal where current >= target has remaining = 0 and
        no longer contributes to liabilities. No status filter needed
        on the debt side — the remaining > 0 check handles it."""
        from app.services.net_worth_service import compute_current_net_worth
        uid = _make_user(app)
        _add_goal(
            app, uid, "Pay off credit card",
            target=3000, current=3000,
        )
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)
        with app.app_context():
            user = db.session.get(User, uid)
            # Debt cleared → drops out; savings of 500 remain.
            assert compute_current_net_worth(user) == Decimal("500")

    def test_overpaid_debt_does_not_become_an_asset(self, app):
        """If current_amount on a debt goal somehow exceeds target,
        remaining goes negative and we DON'T let it leak in as an
        asset. The remaining > 0 filter prevents this."""
        from app.services.net_worth_service import compute_current_net_worth
        uid = _make_user(app)
        _add_goal(
            app, uid, "Pay off credit card",
            target=2000, current=2500,  # paid more than owed
        )
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_current_net_worth(user) == Decimal("0")


# ─── compute_progress ────────────────────────────────────────


class TestComputeProgress:

    def test_zero_immediately_after_snapshot(self, app):
        """User who just finished onboarding has progress = 0 (current
        equals starting)."""
        from app.services.net_worth_service import compute_progress
        uid = _make_user(app, starting=-2500)
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)
        _add_goal(app, uid, "Pay off credit card", target=3000, current=0)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_progress(user) == Decimal("0")

    def test_positive_after_savings_contribution(self, app):
        from app.services.net_worth_service import compute_progress
        uid = _make_user(app, starting=-2500)
        # User added £200 to emergency fund since starting (current=700, was 500).
        _add_goal(app, uid, "Emergency fund", target=5000, current=700)
        _add_goal(app, uid, "Pay off credit card", target=3000, current=0)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_progress(user) == Decimal("200")

    def test_positive_after_debt_payoff(self, app):
        """Paying down debt is positive progress: remaining debt
        decreases, liabilities decrease, net worth rises."""
        from app.services.net_worth_service import compute_progress
        uid = _make_user(app, starting=-2500)
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)
        # User has paid off £400 of the credit card since starting.
        _add_goal(app, uid, "Pay off credit card", target=3000, current=400)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_progress(user) == Decimal("400")

    def test_zero_when_starting_not_set(self, app):
        """User mid-onboarding (no snapshot yet) gets progress = 0."""
        from app.services.net_worth_service import compute_progress
        uid = _make_user(app, starting=None)
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)
        with app.app_context():
            user = db.session.get(User, uid)
            assert compute_progress(user) == Decimal("0")


# ─── snapshot_starting_net_worth ─────────────────────────────


class TestSnapshot:

    def test_snapshot_captures_current_net_worth(self, app):
        from app.services.net_worth_service import (
            compute_current_net_worth,
            snapshot_starting_net_worth,
        )
        uid = _make_user(app, starting=None)
        _add_goal(app, uid, "Emergency fund", target=5000, current=500)
        _add_goal(app, uid, "Pay off credit card", target=3000, current=0)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.starting_net_worth is None

            written = snapshot_starting_net_worth(user)
            assert written is True

            user = db.session.get(User, uid)
            assert Decimal(str(user.starting_net_worth)) == Decimal("-2500")
            assert compute_current_net_worth(user) == user.starting_net_worth

    def test_snapshot_idempotent_does_not_overwrite(self, app):
        """A second call must NOT overwrite an existing snapshot — even
        if the user's actual net worth has changed since."""
        from app.services.net_worth_service import snapshot_starting_net_worth
        uid = _make_user(app, starting=-2500)
        _add_goal(app, uid, "Emergency fund", target=5000, current=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            written = snapshot_starting_net_worth(user)
            assert written is False
            user = db.session.get(User, uid)
            # Snapshot stays at the original -2500 value.
            assert Decimal(str(user.starting_net_worth)) == Decimal("-2500")


# ─── get_net_worth_summary ───────────────────────────────────


class TestSummary:

    def test_summary_dict_shape(self, app):
        from app.services.net_worth_service import get_net_worth_summary
        uid = _make_user(app, starting=-2500)
        _add_goal(app, uid, "Emergency fund", target=5000, current=700)
        _add_goal(app, uid, "Pay off credit card", target=3000, current=400)
        with app.app_context():
            user = db.session.get(User, uid)
            summary = get_net_worth_summary(user)
            assert set(summary.keys()) == {
                "current", "starting", "progress", "has_started",
            }
            # current = 700 saved - (3000 - 400) remaining debt = -1900
            assert summary["current"] == Decimal("-1900")
            assert summary["starting"] == Decimal("-2500")
            # progress = current - starting = -1900 - (-2500) = 600
            assert summary["progress"] == Decimal("600")
            assert summary["has_started"] is True

    def test_has_started_false_when_no_snapshot(self, app):
        from app.services.net_worth_service import get_net_worth_summary
        uid = _make_user(app, starting=None)
        with app.app_context():
            user = db.session.get(User, uid)
            summary = get_net_worth_summary(user)
            assert summary["has_started"] is False
            assert summary["progress"] == Decimal("0")

    def test_progress_identity_holds(self, app):
        """current - starting == progress, every time."""
        from app.services.net_worth_service import get_net_worth_summary
        uid = _make_user(app, starting=-5000)
        _add_goal(app, uid, "House deposit", target=20000, current=1500)
        _add_goal(app, uid, "Pay off credit card", target=4000, current=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            summary = get_net_worth_summary(user)
            assert summary["current"] - summary["starting"] == summary["progress"]
