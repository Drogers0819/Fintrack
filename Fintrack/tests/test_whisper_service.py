"""
Today's Whisper — get_todays_whisper service + User helpers.

Coverage:
  • Library priority order (highest-priority match wins)
  • Fallback when no condition matches
  • Defensive: a raising helper doesn't blank the whisper
  • User helper methods given various data shapes
  • Template variable substitution doesn't crash with missing data
  • Whisper rendered on the overview page
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import db
from app.models.checkin import CheckIn, CheckInEntry
from app.models.goal import Goal
from app.models.user import User


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(
    app,
    *,
    email="whisper@test.com",
    name="Whisper User",
    factfind=True,
    monthly_income=2500,
    paid=True,
):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.monthly_income = Decimal(str(monthly_income))
        user.rent_amount = Decimal("800")
        user.bills_amount = Decimal("200")
        user.factfind_completed = factfind
        if paid:
            user.subscription_status = "active"
            user.subscription_tier = "pro_plus"
        else:
            user.subscription_status = "trialing"
            user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _add_goal(app, user_id, name, *, target=2000, current=0,
              monthly_allocation=200, status="active"):
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            target_amount=Decimal(str(target)),
            current_amount=Decimal(str(current)),
            monthly_allocation=Decimal(str(monthly_allocation)),
            status=status,
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


def _add_checkin(app, user_id, *, month, year, planned, actual,
                 completed_at=None):
    with app.app_context():
        ci = CheckIn(user_id=user_id, month=month, year=year)
        if completed_at:
            ci.completed_at = completed_at
        db.session.add(ci)
        db.session.flush()
        entry = CheckInEntry(
            checkin_id=ci.id,
            pot_name="Goal pot",
            planned_amount=Decimal(str(planned)),
            actual_amount=Decimal(str(actual)),
        )
        db.session.add(entry)
        db.session.commit()
        return ci.id


def _login(client, email="whisper@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


# ─── Library priority + fallback ─────────────────────────────


class TestWhisperLibrary:

    def test_factfind_pending_wins_for_brand_new_user(self, app):
        from app.services.whisper_service import get_todays_whisper
        uid = _make_user(app, factfind=False)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_todays_whisper(user)
            assert "four short steps" in result.lower()

    def test_no_goals_yet_wins_when_factfind_done_but_no_goals(self, app):
        from app.services.whisper_service import get_todays_whisper
        uid = _make_user(app, factfind=True)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_todays_whisper(user)
            assert "pick a goal" in result.lower()

    def test_fallback_returned_when_no_conditions_match(self, app):
        """User has factfind done, has a goal, no checkins, no debt
        nearing completion, no streak — falls through to the fallback."""
        from app.services.whisper_service import get_todays_whisper
        uid = _make_user(app)
        _add_goal(app, uid, "Holiday fund", target=5000, current=200,
                  monthly_allocation=100)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_todays_whisper(user)
            assert "quiet today" in result.lower()

    def test_priority_paused_subscription_above_survival(self, app):
        """Subscription paused has priority over survival mode (it's
        listed first in the library)."""
        from app.services.whisper_service import get_todays_whisper
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            user.subscription_paused_until = datetime.utcnow() + timedelta(days=20)
            user.survival_mode_active = True
            db.session.commit()

            user = db.session.get(User, uid)
            result = get_todays_whisper(user)
            assert "subscription is paused" in result.lower()
            assert "survival" not in result.lower()

    def test_credit_card_whisper_renders_when_close_to_completion(self, app):
        from app.services.whisper_service import get_todays_whisper
        uid = _make_user(app)
        # £180 left at £60/mo = 3 months remaining → matches < 6.
        _add_goal(app, uid, "Pay off credit card", target=600, current=420,
                  monthly_allocation=60)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_todays_whisper(user)
            assert "credit card" in result.lower()
            assert "per month" in result

    def test_savings_streak_whisper_renders_when_2_months_ahead(self, app):
        from app.services.whisper_service import get_todays_whisper
        uid = _make_user(app)
        # Goal exists so we don't fall into the "no goals" branch.
        _add_goal(app, uid, "Holiday", target=5000, current=2000,
                  monthly_allocation=300)
        # Two consecutive months with actual >= planned.
        _add_checkin(app, uid, month=4, year=2026, planned=300, actual=350)
        _add_checkin(app, uid, month=3, year=2026, planned=300, actual=320)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_todays_whisper(user)
            assert "ahead of your savings target" in result.lower()

    def test_returns_fallback_when_user_is_none(self, app):
        from app.services.whisper_service import get_todays_whisper
        result = get_todays_whisper(None)
        assert "quiet today" in result.lower()

    def test_raising_helper_does_not_blank_whisper(self, app):
        """If a helper raises, the loop logs and continues to the next."""
        from app.services import whisper_service

        uid = _make_user(app)
        _add_goal(app, uid, "Holiday", target=5000, current=200,
                  monthly_allocation=100)

        def boom(_user):
            raise RuntimeError("synthetic")

        original_lib = list(whisper_service.WHISPER_LIBRARY)
        try:
            whisper_service.WHISPER_LIBRARY = [boom] + original_lib
            with app.app_context():
                user = db.session.get(User, uid)
                result = whisper_service.get_todays_whisper(user)
                # The fallback or another helper should still produce a string.
                assert isinstance(result, str) and result
        finally:
            whisper_service.WHISPER_LIBRARY = original_lib


# ─── User helpers ────────────────────────────────────────────


class TestUserHelpers:

    def test_credit_card_helper_returns_true_when_close(self, app):
        uid = _make_user(app)
        _add_goal(app, uid, "Pay off credit card", target=600, current=420,
                  monthly_allocation=60)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.has_active_credit_card_goal_completing_soon() is True

    def test_credit_card_helper_returns_false_when_not_close(self, app):
        uid = _make_user(app)
        # 24 months remaining > 6 cap → False
        _add_goal(app, uid, "Pay off credit card", target=2400, current=0,
                  monthly_allocation=100)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.has_active_credit_card_goal_completing_soon() is False

    def test_credit_card_helper_returns_false_when_no_credit_card_goal(self, app):
        uid = _make_user(app)
        _add_goal(app, uid, "Holiday fund", target=600, current=420,
                  monthly_allocation=60)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.has_active_credit_card_goal_completing_soon() is False

    def test_credit_card_helper_returns_false_with_zero_allocation(self, app):
        """A paused goal (monthly_allocation=0) shouldn't 'complete' in
        any number of months — guard against div-by-zero."""
        uid = _make_user(app)
        _add_goal(app, uid, "Pay off credit card", target=600, current=420,
                  monthly_allocation=0)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.has_active_credit_card_goal_completing_soon() is False

    def test_savings_streak_two_months_ahead(self, app):
        uid = _make_user(app)
        _add_checkin(app, uid, month=4, year=2026, planned=300, actual=320)
        _add_checkin(app, uid, month=3, year=2026, planned=300, actual=320)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.is_ahead_of_savings_target() is True
            assert user.get_savings_streak_months() >= 2

    def test_savings_streak_breaks_on_first_short_month(self, app):
        uid = _make_user(app)
        # Most recent month under planned breaks the streak.
        _add_checkin(app, uid, month=4, year=2026, planned=300, actual=200)
        _add_checkin(app, uid, month=3, year=2026, planned=300, actual=320)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.is_ahead_of_savings_target() is False

    def test_savings_streak_returns_false_with_one_checkin(self, app):
        uid = _make_user(app)
        _add_checkin(app, uid, month=4, year=2026, planned=300, actual=320)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.is_ahead_of_savings_target() is False

    def test_recent_checkin_within_14_days(self, app):
        uid = _make_user(app)
        recent = datetime.utcnow() - timedelta(days=3)
        _add_checkin(app, uid, month=4, year=2026, planned=300, actual=300,
                     completed_at=recent)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.has_completed_recent_checkin() is True

    def test_recent_checkin_returns_false_when_old(self, app):
        uid = _make_user(app)
        old = datetime.utcnow() - timedelta(days=30)
        _add_checkin(app, uid, month=4, year=2026, planned=300, actual=300,
                     completed_at=old)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.has_completed_recent_checkin() is False

    def test_recent_checkin_returns_false_when_none_exist(self, app):
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.has_completed_recent_checkin() is False


# ─── Overview integration ────────────────────────────────────


class TestOverviewIntegration:

    def test_overview_renders_whisper_card(self, app, client):
        """A user with no goals should land on the 'pick a goal' whisper
        and the top-row chip should render with the section label and
        the whisper text. (May 2026 restructure moved the whisper from
        a right-rail card to a top-row stat chip — the label text
        moved with it.)"""
        _make_user(app)
        _login(client)
        resp = client.get("/overview")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Today's whisper" in body
        # The whisper text itself.
        assert "pick a goal" in body.lower()
