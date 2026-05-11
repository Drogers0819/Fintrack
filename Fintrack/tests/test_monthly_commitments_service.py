"""
Monthly commitments panel — service-layer + render coverage.

Source-of-truth rules under test:
  • Profile estimates (groceries, transport, other_commitments) are
    NOT commitments — they're factfind estimates, the ring chart
    surfaces actual spend instead.
  • Profile fields with a value (rent, bills, subscriptions) DO count.
  • Active goals contribute one row each.
  • Debt-shaped goals are listed before non-debt goals.
  • Inactive / archived goals are skipped.
  • Zero-allocation goals are skipped.
  • Total matches the sum of items.
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
    email="commit@test.com",
    rent=None,
    bills=None,
    subscriptions=None,
    groceries=None,
    transport=None,
    other=None,
):
    """Make a user with explicit profile commitment values. Anything
    not passed stays None so the test asserts on the precise data."""
    with app.app_context():
        user = User(email=email, name="Commit User")
        user.set_password("testpassword123")
        user.factfind_completed = True
        user.monthly_income = Decimal("2500")
        user.rent_amount = Decimal(str(rent)) if rent is not None else None
        user.bills_amount = Decimal(str(bills)) if bills is not None else None
        user.subscriptions_total = (
            Decimal(str(subscriptions)) if subscriptions is not None else None
        )
        user.groceries_estimate = (
            Decimal(str(groceries)) if groceries is not None else None
        )
        user.transport_estimate = (
            Decimal(str(transport)) if transport is not None else None
        )
        user.other_commitments = (
            Decimal(str(other)) if other is not None else None
        )
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
    monthly_allocation=200,
    status="active",
    priority_rank=1,
):
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            target_amount=Decimal("5000"),
            current_amount=Decimal("100"),
            monthly_allocation=Decimal(str(monthly_allocation)),
            status=status,
            priority_rank=priority_rank,
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


def _login(client, email="commit@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


# ─── Empty state ─────────────────────────────────────────────


class TestEmptyState:

    def test_user_with_no_commitments_returns_empty(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app)  # No rent/bills/subs/goals.
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            assert result["items"] == []
            assert result["total_committed"] == 0.0


# ─── Profile fields ──────────────────────────────────────────


class TestProfileFields:

    def test_rent_bills_subscriptions_render_in_order(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, rent=900, bills=180, subscriptions=45)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [item["name"] for item in result["items"]]
            assert names == ["Rent / mortgage", "Bills", "Subscriptions"]

    def test_zero_value_profile_fields_are_skipped(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, rent=900, bills=0)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [item["name"] for item in result["items"]]
            assert "Rent / mortgage" in names
            assert "Bills" not in names

    def test_estimates_are_excluded(self, app):
        """groceries / transport / other_commitments are estimates,
        not commitments — they must NOT appear on the panel."""
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(
            app, rent=900, groceries=240, transport=120, other=60,
        )
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [item["name"] for item in result["items"]]
            # Only rent counts; the three estimates are dropped.
            assert names == ["Rent / mortgage"]


# ─── Goals ───────────────────────────────────────────────────


class TestGoalCommitments:

    def test_goal_contributions_sorted_by_amount_descending(self, app):
        """The panel orders goal contributions by amount (largest first)
        so visual weight matches numeric weight. Debt vs non-debt
        category no longer influences order — that was the old
        contract under the flat-items shape."""
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app)
        _add_goal(app, uid, "Holiday fund", monthly_allocation=150)
        _add_goal(app, uid, "Pay off credit card", monthly_allocation=200)
        _add_goal(app, uid, "House deposit", monthly_allocation=300)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [item["name"] for item in result["items"]]
            # Items list is obligations (none here) + goal_contributions
            # in descending-amount order.
            assert names == ["House deposit", "Pay off credit card", "Holiday fund"]

    def test_inactive_goals_are_skipped(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app)
        _add_goal(app, uid, "Active goal", monthly_allocation=100)
        _add_goal(app, uid, "Archived goal", monthly_allocation=500,
                  status="archived")
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [item["name"] for item in result["items"]]
            assert "Archived goal" not in names
            assert "Active goal" in names

    def test_zero_allocation_goal_is_skipped(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app)
        _add_goal(app, uid, "Paused goal", monthly_allocation=0)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            assert result["items"] == []


# ─── Total ───────────────────────────────────────────────────


class TestTotal:

    def test_total_matches_sum_of_items(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, rent=900, bills=180)
        _add_goal(app, uid, "Holiday", monthly_allocation=150)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            expected = sum(item["amount"] for item in result["items"])
            assert result["total_committed"] == round(expected, 2)
            assert result["total_committed"] == 1230.0


# ─── Overview render integration ─────────────────────────────


class TestOverviewRender:

    def test_overview_renders_commitments_panel(self, app, client):
        uid = _make_user(app, rent=900, bills=180)
        _add_goal(app, uid, "Holiday", monthly_allocation=150)
        _login(client)

        resp = client.get("/overview")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "THIS MONTH'S COMMITMENTS" in body
        assert "Rent / mortgage" in body
        assert "Holiday" in body
        assert "Total committed" in body

    def test_overview_renders_commitments_empty_state(self, app, client):
        _make_user(app)  # No profile commitments, no goals.
        _login(client)

        resp = client.get("/overview")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "THIS MONTH'S COMMITMENTS" in body
        assert "No commitments tracked yet" in body

    def test_overview_renders_ring_chart_section(self, app, client):
        """Sanity check that Commit A's section also still renders."""
        _make_user(app)
        _login(client)

        resp = client.get("/overview")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "THIS MONTH" in body
        # Empty state copy from Commit A (no transactions yet).
        assert "No spending tracked this month" in body


# ─── Estimated spend (Tier 2 follow-up) ──────────────────────


class TestEstimates:

    def test_all_three_estimates_set_returns_three_rows_in_order(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, groceries=240, transport=120, other=60)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [e["name"] for e in result["estimates"]]
            assert names == [
                "Groceries (estimate)",
                "Transport (estimate)",
                "Other (estimate)",
            ]
            assert result["total_estimated"] == 420.0

    def test_only_groceries_set_returns_one_row(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, groceries=240)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [e["name"] for e in result["estimates"]]
            assert names == ["Groceries (estimate)"]
            assert result["total_estimated"] == 240.0

    def test_no_estimates_returns_empty_list_and_zero_total(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app)  # No estimate fields set.
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            assert result["estimates"] == []
            assert result["total_estimated"] == 0.0

    def test_estimates_distinct_from_commitments(self, app):
        """A user with both rent (commitment) and groceries (estimate)
        gets one row in `items` and one row in `estimates`. The
        estimate must NOT contaminate the items list."""
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, rent=900, groceries=240)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            item_names = [i["name"] for i in result["items"]]
            estimate_names = [e["name"] for e in result["estimates"]]
            assert "Rent / mortgage" in item_names
            assert "Groceries (estimate)" not in item_names
            assert "Groceries (estimate)" in estimate_names
            assert "Rent / mortgage" not in estimate_names
            # And the totals stay separate.
            assert result["total_committed"] == 900.0
            assert result["total_estimated"] == 240.0

    def test_overview_renders_both_sections_when_both_have_data(self, app, client):
        uid = _make_user(app, rent=900, bills=200, subscriptions=50,
                         groceries=400, transport=150)
        _login(client)
        resp = client.get("/overview")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # Commitments section.
        assert "THIS MONTH'S COMMITMENTS" in body
        assert "Rent / mortgage" in body
        assert "Total committed" in body
        # Estimates section.
        assert "ESTIMATED SPEND" in body
        assert "Groceries (estimate)" in body
        assert "Transport (estimate)" in body
        assert "Total estimated" in body


# ─── Obligations vs goal contributions (clarity follow-up) ──


class TestObligationsAndGoalContributions:
    """Tests for the new return shape that separates fixed obligations
    from goal contributions with their own subtotals."""

    def test_no_active_goals_leaves_goal_contributions_empty(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, rent=900, bills=180)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            assert result["goal_contributions"] == []
            assert result["goal_contributions_total"] == 0.0
            # Obligations populated as before.
            assert len(result["obligations"]) == 2
            assert result["obligations_total"] == 1080.0
            # Total equals the obligations subtotal when no goals.
            assert result["total_committed"] == result["obligations_total"]

    def test_active_goals_populate_goal_contributions(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, rent=900, bills=180)
        _add_goal(app, uid, "Car", monthly_allocation=1518)
        _add_goal(app, uid, "Emergency fund", monthly_allocation=202)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [g["name"] for g in result["goal_contributions"]]
            assert set(names) == {"Car", "Emergency fund"}
            assert result["goal_contributions_total"] == 1720.0
            # Grand total = obligations + goals.
            assert result["total_committed"] == 1080.0 + 1720.0

    def test_goal_contributions_sorted_descending_by_amount(self, app):
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app)
        _add_goal(app, uid, "Holiday", monthly_allocation=120)
        _add_goal(app, uid, "Car", monthly_allocation=400)
        _add_goal(app, uid, "Emergency fund", monthly_allocation=250)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [g["name"] for g in result["goal_contributions"]]
            assert names == ["Car", "Emergency fund", "Holiday"]

    def test_completed_or_archived_goals_excluded(self, app):
        """Only active goals contribute. Anything else doesn't appear
        as a current monthly commitment."""
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app)
        _add_goal(app, uid, "Active goal", monthly_allocation=200)
        _add_goal(app, uid, "Archived goal", monthly_allocation=500,
                  status="archived")
        _add_goal(app, uid, "Done goal", monthly_allocation=300,
                  status="completed")

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [g["name"] for g in result["goal_contributions"]]
            assert names == ["Active goal"]
            assert result["goal_contributions_total"] == 200.0

    def test_zero_allocation_goals_excluded(self, app):
        """An active goal with monthly_allocation == 0 isn't a current
        commitment — paused, or never funded."""
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app)
        _add_goal(app, uid, "Funded goal", monthly_allocation=150)
        _add_goal(app, uid, "Paused goal", monthly_allocation=0)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            names = [g["name"] for g in result["goal_contributions"]]
            assert names == ["Funded goal"]

    def test_total_committed_identity_holds(self, app):
        """For any combination of obligations + goals, the grand total
        always equals the sum of the two subtotals."""
        from app.services.spending_breakdown_service import (
            get_monthly_commitments_for_user,
        )
        uid = _make_user(app, rent=900, bills=180, subscriptions=50)
        _add_goal(app, uid, "Car", monthly_allocation=300)
        _add_goal(app, uid, "Emergency fund", monthly_allocation=150)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_monthly_commitments_for_user(user)
            assert (
                result["total_committed"]
                == result["obligations_total"] + result["goal_contributions_total"]
            )

    def test_overview_renders_both_subsections_when_goals_present(self, app, client):
        """Integration: the new subsection labels render on /overview
        when the user has both obligations and goal contributions."""
        uid = _make_user(app, rent=900, bills=180)
        _add_goal(app, uid, "Car", monthly_allocation=300)
        _login(client)

        resp = client.get("/overview")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # Sub-section labels (matched case-insensitively in template).
        assert "Fixed obligations" in body
        assert "Towards your goals" in body
        assert "Obligations subtotal" in body
        assert "Goals subtotal" in body
        assert "Total committed" in body

    def test_overview_hides_goals_subsection_when_no_active_goals(self, app, client):
        """No goals → goals subsection (and its subtotal label) must
        not appear. Obligations + total committed still render."""
        _make_user(app, rent=900, bills=180)
        _login(client)

        resp = client.get("/overview")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Fixed obligations" in body
        assert "Towards your goals" not in body
        assert "Goals subtotal" not in body
        assert "Total committed" in body
