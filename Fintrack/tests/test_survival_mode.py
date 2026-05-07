"""
Survival mode — Block 2 Task 2.5.

Coverage:
  • Service logic — should_auto_activate threshold, activate /
    deactivate state transitions, get_survival_floor formula.
  • Planner integration — survival branch returns the same output
    schema as the standard plan, filters non-essentials, sets
    lifestyle to the survival floor, and standard mode falls
    through unchanged.
  • Auto-activation — record_lost_income flips the flag for a
    >=25% drop, leaves it alone for smaller drops or unknown income.
  • Manual toggle routes — POST /settings/survival-mode/activate
    and /deactivate flip the flag, redirect, and require login.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import db
from app.models.crisis_event import CrisisEvent
from app.models.goal import Goal
from app.models.user import User


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(
    app,
    email="survive@test.com",
    name="Survive User",
    *,
    monthly_income=2000,
    survival_active=False,
    factfind=True,
):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.monthly_income = Decimal(str(monthly_income))
        user.rent_amount = Decimal("800")
        user.bills_amount = Decimal("200")
        user.factfind_completed = factfind
        user.survival_mode_active = survival_active
        if survival_active:
            user.survival_mode_started_at = datetime.utcnow()
        user.subscription_status = "trialing"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="survive@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


def _add_goal(app, user_id, name, *, monthly_allocation=200, target=5000,
              current=500, is_essential=False):
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            target_amount=Decimal(str(target)),
            current_amount=Decimal(str(current)),
            monthly_allocation=Decimal(str(monthly_allocation)),
            is_essential=is_essential,
            status="active",
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


# ─── Service: should_auto_activate ───────────────────────────


class TestShouldAutoActivate:

    def test_thirty_percent_drop_returns_true(self, app):
        from app.services.survival_mode_service import should_auto_activate
        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            assert should_auto_activate(user, 1400) is True  # 30% drop

    def test_ten_percent_drop_returns_false(self, app):
        from app.services.survival_mode_service import should_auto_activate
        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            assert should_auto_activate(user, 1800) is False  # 10% drop

    def test_exactly_25_percent_drop_returns_true(self, app):
        from app.services.survival_mode_service import should_auto_activate
        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            assert should_auto_activate(user, 1500) is True  # exactly 25%

    def test_no_previous_income_returns_false(self, app):
        from app.services.survival_mode_service import should_auto_activate
        with app.app_context():
            user = User(email="noincome@test.com", name="No Income")
            user.set_password("testpassword123")
            user.monthly_income = None
            db.session.add(user)
            db.session.commit()
            assert should_auto_activate(user, 1500) is False

    def test_unknown_new_income_returns_false(self, app):
        """new_monthly_income=None is the 'I don't know yet' branch — never auto-activate."""
        from app.services.survival_mode_service import should_auto_activate
        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            assert should_auto_activate(user, None) is False

    def test_already_active_returns_false(self, app):
        """No double-fire if survival mode is already on."""
        from app.services.survival_mode_service import should_auto_activate
        uid = _make_user(app, monthly_income=2000, survival_active=True)
        with app.app_context():
            user = db.session.get(User, uid)
            assert should_auto_activate(user, 500) is False  # huge drop, but already on


# ─── Service: activate / deactivate ──────────────────────────


class TestActivateDeactivate:

    def test_activate_sets_flag_and_timestamp(self, app):
        from app.services.survival_mode_service import activate_survival_mode
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.survival_mode_active is False
            assert user.survival_mode_started_at is None

            activate_survival_mode(user, reason="manual")

            user = db.session.get(User, uid)
            assert user.survival_mode_active is True
            assert user.survival_mode_started_at is not None

    def test_deactivate_clears_flag_keeps_timestamp(self, app):
        """The timestamp is the historical record of when survival mode
        was last activated. Don't clear it on deactivation."""
        from app.services.survival_mode_service import deactivate_survival_mode
        uid = _make_user(app, survival_active=True)
        with app.app_context():
            user = db.session.get(User, uid)
            stamped_at = user.survival_mode_started_at
            assert stamped_at is not None

            deactivate_survival_mode(user)

            user = db.session.get(User, uid)
            assert user.survival_mode_active is False
            assert user.survival_mode_started_at == stamped_at

    def test_activate_fires_analytics_event(self, app):
        from app.services.survival_mode_service import activate_survival_mode
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("app.services.analytics_service.track_event") as track:
                activate_survival_mode(user, reason="income_drop")

            calls = [c for c in track.call_args_list
                     if len(c.args) >= 2 and c.args[1] == "survival_mode_activated"]
            assert len(calls) == 1
            assert calls[0].args[2]["reason"] == "income_drop"


# ─── Service: get_survival_floor ─────────────────────────────


class TestGetSurvivalFloor:

    def test_returns_20_percent_for_high_income(self, app):
        from app.services.survival_mode_service import get_survival_floor
        uid = _make_user(app, monthly_income=4000)
        with app.app_context():
            user = db.session.get(User, uid)
            # 20% of 4000 = 800; max(800, 400) = 800
            assert get_survival_floor(user) == 800.0

    def test_returns_400_floor_for_low_income(self, app):
        from app.services.survival_mode_service import get_survival_floor
        uid = _make_user(app, monthly_income=1500)
        with app.app_context():
            user = db.session.get(User, uid)
            # 20% of 1500 = 300; max(300, 400) = 400
            assert get_survival_floor(user) == 400.0


# ─── Planner integration ────────────────────────────────────


class TestPlannerSurvivalMode:

    def test_standard_mode_returns_survival_mode_false(self, app):
        from app.services.planner_service import generate_financial_plan
        uid = _make_user(app, monthly_income=2500)
        with app.app_context():
            user = db.session.get(User, uid)
            plan = generate_financial_plan(user.profile_dict(), [])
            assert plan.get("survival_mode") is False

    def test_survival_mode_returns_survival_flag(self, app):
        from app.services.planner_service import generate_financial_plan
        uid = _make_user(app, monthly_income=2500, survival_active=True)
        with app.app_context():
            user = db.session.get(User, uid)
            plan = generate_financial_plan(user.profile_dict(), [])
            assert plan["survival_mode"] is True
            assert "survival_floor" in plan

    def test_survival_plan_has_same_top_level_keys(self, app):
        """Schema compatibility: every key the standard planner returns
        must also appear in the survival output."""
        from app.services.planner_service import generate_financial_plan

        uid_std = _make_user(app, email="std@test.com", monthly_income=2500)
        uid_surv = _make_user(app, email="surv@test.com",
                              monthly_income=2500, survival_active=True)

        with app.app_context():
            user_std = db.session.get(User, uid_std)
            user_surv = db.session.get(User, uid_surv)
            std_plan = generate_financial_plan(user_std.profile_dict(), [])
            surv_plan = generate_financial_plan(user_surv.profile_dict(), [])

            std_keys = set(std_plan.keys())
            surv_keys = set(surv_plan.keys())
            # Survival output must include every standard key (it can
            # add survival_mode / survival_floor on top).
            missing = std_keys - surv_keys
            assert not missing, f"Survival plan missing keys: {missing}"

    def test_non_essential_goals_paused(self, app):
        from app.services.planner_service import generate_financial_plan

        uid = _make_user(app, monthly_income=2500, survival_active=True)
        _add_goal(app, uid, "Holiday fund", monthly_allocation=200, is_essential=False)
        _add_goal(app, uid, "Emergency fund", monthly_allocation=300, is_essential=True)

        with app.app_context():
            user = db.session.get(User, uid)
            goals_data = [g.to_dict() for g in Goal.query.filter_by(user_id=uid).all()]
            plan = generate_financial_plan(user.profile_dict(), goals_data)

            holiday = next((p for p in plan["pots"] if p["name"] == "Holiday fund"), None)
            emergency = next((p for p in plan["pots"] if p["name"] == "Emergency fund"), None)
            assert holiday is not None and holiday["monthly_amount"] == 0
            assert holiday.get("paused_for_survival") is True
            assert emergency is not None and emergency["monthly_amount"] > 0

    def test_emergency_goal_essential_by_name(self, app):
        """Even without is_essential set, a goal named 'Emergency fund'
        gets contributions in survival mode (the heuristic backup)."""
        from app.services.planner_service import generate_financial_plan

        uid = _make_user(app, monthly_income=2500, survival_active=True)
        _add_goal(app, uid, "Emergency fund", monthly_allocation=300, is_essential=False)

        with app.app_context():
            user = db.session.get(User, uid)
            goals_data = [g.to_dict() for g in Goal.query.filter_by(user_id=uid).all()]
            plan = generate_financial_plan(user.profile_dict(), goals_data)

            emergency = next((p for p in plan["pots"] if p["name"] == "Emergency fund"), None)
            assert emergency is not None and emergency["monthly_amount"] == 300

    def test_lifestyle_set_to_survival_floor(self, app):
        from app.services.planner_service import generate_financial_plan

        # Income 4000 → 20% = 800 (above the £400 floor)
        uid = _make_user(app, monthly_income=4000, survival_active=True)
        with app.app_context():
            user = db.session.get(User, uid)
            plan = generate_financial_plan(user.profile_dict(), [])
            assert plan["lifestyle_monthly"] == 800.0
            assert plan["survival_floor"] == 800.0
            # Buffer is zero in survival mode.
            assert plan["buffer_monthly"] == 0

    def test_survival_alerts_describes_state(self, app):
        from app.services.planner_service import generate_financial_plan

        uid = _make_user(app, monthly_income=2500, survival_active=True)
        with app.app_context():
            user = db.session.get(User, uid)
            plan = generate_financial_plan(user.profile_dict(), [])
            assert any(a.get("type") == "survival_mode" for a in plan.get("alerts", []))


# ─── Auto-activation via crisis flow ─────────────────────────


class TestCrisisAutoActivation:

    def test_thirty_percent_drop_activates(self, app):
        from app.services.crisis_service import record_lost_income

        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            event = record_lost_income(
                user,
                change_type="reduced_hours",
                new_monthly_income=1400,  # 30% drop
                occurred_on=date.today(),
            )
            assert event.survival_mode_just_activated is True
            user = db.session.get(User, uid)
            assert user.survival_mode_active is True

    def test_ten_percent_drop_does_not_activate(self, app):
        from app.services.crisis_service import record_lost_income

        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            event = record_lost_income(
                user,
                change_type="reduced_hours",
                new_monthly_income=1800,  # 10% drop
                occurred_on=date.today(),
            )
            assert event.survival_mode_just_activated is False
            user = db.session.get(User, uid)
            assert user.survival_mode_active is False

    def test_unknown_income_does_not_activate(self, app):
        from app.services.crisis_service import record_lost_income

        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            event = record_lost_income(
                user,
                change_type="job_loss",
                new_monthly_income=None,
                income_unknown=True,
                occurred_on=date.today(),
            )
            assert event.survival_mode_just_activated is False
            user = db.session.get(User, uid)
            assert user.survival_mode_active is False

    def test_auto_activation_event_fires_with_income_drop_reason(self, app):
        from app.services.crisis_service import record_lost_income

        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("app.services.analytics_service.track_event") as track:
                record_lost_income(
                    user,
                    change_type="job_loss",
                    new_monthly_income=1200,
                    occurred_on=date.today(),
                )
            calls = [c for c in track.call_args_list
                     if len(c.args) >= 2 and c.args[1] == "survival_mode_activated"]
            assert len(calls) == 1
            assert calls[0].args[2]["reason"] == "income_drop"


# ─── Manual toggle routes ────────────────────────────────────


class TestManualToggleRoutes:

    def test_activate_route_flips_flag_and_redirects(self, app, client):
        uid = _make_user(app)
        _login(client)
        with patch("app.services.analytics_service.track_event"):
            resp = client.post("/settings/survival-mode/activate",
                               follow_redirects=False)
        assert resp.status_code == 302
        assert "/settings" in resp.headers.get("Location", "")
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.survival_mode_active is True

    def test_deactivate_route_clears_flag_and_redirects(self, app, client):
        uid = _make_user(app, survival_active=True)
        _login(client)
        with patch("app.services.analytics_service.track_event"):
            resp = client.post("/settings/survival-mode/deactivate",
                               follow_redirects=False)
        assert resp.status_code == 302
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.survival_mode_active is False

    def test_activate_requires_login(self, app, client):
        resp = client.post("/settings/survival-mode/activate",
                           follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_deactivate_requires_login(self, app, client):
        resp = client.post("/settings/survival-mode/deactivate",
                           follow_redirects=False)
        assert resp.status_code in (302, 401)


# ─── Companion awareness ─────────────────────────────────────


class TestCompanionAwareness:

    def test_user_context_mentions_survival_mode_when_active(self, app):
        from app.services.companion_service import _build_user_context
        uid = _make_user(app, survival_active=True)
        with app.app_context():
            user = db.session.get(User, uid)
            context = _build_user_context(user)
            assert "Survival mode: on" in context

    def test_user_context_omits_survival_when_inactive(self, app):
        from app.services.companion_service import _build_user_context
        uid = _make_user(app, survival_active=False)
        with app.app_context():
            user = db.session.get(User, uid)
            context = _build_user_context(user)
            assert "Survival mode: on" not in context
