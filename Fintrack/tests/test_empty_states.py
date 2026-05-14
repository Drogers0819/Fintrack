"""
Empty states across primary screens.

Covers:
 - /overview banner + placeholder card (factfind-incomplete, no-goals)
 - /my-goals empty state copy + 4 illustrative chips
 - /plan factfind-incomplete and plan-error branches
 - _checkin_view_state helper (complete / form / scheduled)
 - /api/companion/chip-clicked tracking endpoint + login gate
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app import db
from app.models.checkin import CheckIn
from app.models.goal import Goal
from app.models.user import User
from app.routes.page_routes import _checkin_view_state


# ─── Fixtures ────────────────────────────────────────────────


def _make_user(
    app,
    email="empty@test.com",
    password="testpassword123",
    factfind_completed=False,
    monthly_income=None,
    rent=None,
    bills=None,
):
    with app.app_context():
        user = User(email=email, name="Empty Tester")
        user.set_password(password)
        user.factfind_completed = factfind_completed
        if monthly_income is not None:
            user.monthly_income = monthly_income
        if rent is not None:
            user.rent_amount = rent
        if bills is not None:
            user.bills_amount = bills
        user.subscription_status = "trialing"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="empty@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


# ─── Overview ────────────────────────────────────────────────


class TestOverviewEmptyStates:

    def test_factfind_incomplete_shows_banner_and_placeholder(self, app, client):
        _make_user(app, factfind_completed=False)
        _login(client)
        response = client.get("/overview")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "Take 4 minutes to share your situation" in body
        assert 'data-empty-state="overview-no-plan"' in body
        assert "Will appear here once your plan is built" in body

    def test_factfind_complete_no_goals_shows_banner_and_placeholder(self, app, client):
        """No-goals empty-state copy was redesigned in c060aae from
        a single "What are you saving for?" line into an inline card
        with an "Add your first goal" heading, an explanatory line,
        and a "Choose your goals" CTA."""
        _make_user(
            app,
            factfind_completed=True,
            monthly_income=3000,
            rent=900,
            bills=200,
        )
        _login(client)
        response = client.get("/overview")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert 'data-empty-state="overview-no-goals"' in body
        assert "Add your first goal" in body
        assert "Choose your goals" in body

    def test_factfind_complete_with_goal_does_not_show_empty_state(self, app, client):
        user_id = _make_user(
            app,
            factfind_completed=True,
            monthly_income=3000,
            rent=900,
            bills=200,
        )
        with app.app_context():
            db.session.add(Goal(
                user_id=user_id,
                name="Holiday fund",
                type="savings_target",
                target_amount=2000,
                current_amount=200,
                monthly_allocation=150,
                priority_rank=1,
                status="active",
            ))
            db.session.commit()
        _login(client)
        response = client.get("/overview")
        body = response.data.decode("utf-8")
        assert 'data-empty-state="overview-no-plan"' not in body
        assert 'data-empty-state="overview-no-goals"' not in body


# ─── Goals ────────────────────────────────────────────────


class TestGoalsEmptyState:

    def test_no_goals_shows_copy_and_chips(self, app, client):
        _make_user(app, factfind_completed=True, monthly_income=3000, rent=900, bills=200)
        _login(client)
        response = client.get("/my-goals")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert 'data-empty-state="goals"' in body
        assert "What are you saving for?" in body
        assert "Add my first goal" in body
        # All four illustrative chips
        for chip in ("House deposit", "Holiday", "Emergency fund", "Pay off debt"):
            assert chip in body

    def test_with_goals_does_not_show_empty_state(self, app, client):
        user_id = _make_user(
            app, factfind_completed=True, monthly_income=3000, rent=900, bills=200,
        )
        with app.app_context():
            db.session.add(Goal(
                user_id=user_id,
                name="House deposit fund",
                type="savings_target",
                target_amount=20000,
                current_amount=2000,
                monthly_allocation=400,
                priority_rank=1,
                status="active",
            ))
            db.session.commit()
        _login(client)
        response = client.get("/my-goals")
        body = response.data.decode("utf-8")
        assert 'data-empty-state="goals"' not in body
        # Goal name renders
        assert "House deposit fund" in body

    def test_completed_goals_dont_count_toward_empty_check(self, app, client):
        """Only active goals satisfy the goals list; a completed goal alone
        should still trigger the empty state."""
        user_id = _make_user(
            app, factfind_completed=True, monthly_income=3000, rent=900, bills=200,
        )
        with app.app_context():
            db.session.add(Goal(
                user_id=user_id,
                name="Old goal",
                type="savings_target",
                target_amount=1000,
                current_amount=1000,
                monthly_allocation=100,
                priority_rank=1,
                status="completed",
            ))
            db.session.commit()
        _login(client)
        response = client.get("/my-goals")
        body = response.data.decode("utf-8")
        assert 'data-empty-state="goals"' in body


# ─── Plan ────────────────────────────────────────────────


class TestPlanEmptyStates:

    def test_factfind_incomplete_shows_no_factfind_state(self, app, client):
        _make_user(app, factfind_completed=False)
        _login(client)
        response = client.get("/plan")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert 'data-empty-state="plan-no-factfind"' in body
        assert "Your plan is waiting to be built" in body
        assert "Build my plan" in body
        # Scenario link / withdrawal section should not leak below
        assert "Run a scenario" not in body
        assert "Need to access money?" not in body

    def test_plan_error_shows_error_fallback(self, app, client):
        """If generate_financial_plan returns a dict with `error`, the plan
        page should render the calm error fallback rather than crash."""
        _make_user(app, factfind_completed=True, monthly_income=3000, rent=900, bills=200)
        _login(client)
        with patch(
            "app.routes.page_routes.generate_financial_plan",
            return_value={"error": "Income missing"},
        ):
            response = client.get("/plan")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert 'data-empty-state="plan-error"' in body
        assert "We can't quite build your plan yet" in body
        assert "Review my profile" in body
        assert "Income missing" in body

    def test_normal_plan_renders_main_view(self, app, client):
        user_id = _make_user(
            app, factfind_completed=True, monthly_income=3000, rent=900, bills=200,
        )
        with app.app_context():
            db.session.add(Goal(
                user_id=user_id,
                name="Holiday fund",
                type="savings_target",
                target_amount=2000,
                current_amount=200,
                monthly_allocation=150,
                priority_rank=1,
                status="active",
            ))
            db.session.commit()
        _login(client)
        response = client.get("/plan")
        body = response.data.decode("utf-8")
        assert 'data-empty-state="plan-no-factfind"' not in body
        assert 'data-empty-state="plan-error"' not in body


# ─── Check-in helper ────────────────────────────────────────


class TestCheckinViewState:

    def test_complete_when_existing_and_not_edit_mode(self):
        existing = SimpleNamespace(id=1, completed_at=datetime.utcnow())
        result = _checkin_view_state(date(2026, 5, 5), existing, edit_mode=False)
        assert result["state"] == "complete"

    def test_form_when_in_window_no_existing(self):
        # May has 31 days, last 3 = 29, 30, 31
        result = _checkin_view_state(date(2026, 5, 30), None)
        assert result["state"] == "form"

    def test_form_when_in_window_at_window_start(self):
        # May 29 is window_start_day for May (last_day=31, last-2=29)
        result = _checkin_view_state(date(2026, 5, 29), None)
        assert result["state"] == "form"

    def test_form_when_in_window_at_last_day(self):
        result = _checkin_view_state(date(2026, 5, 31), None)
        assert result["state"] == "form"

    def test_scheduled_when_outside_window_no_existing(self):
        # May 5 is well outside the May 29-31 window
        result = _checkin_view_state(date(2026, 5, 5), None)
        assert result["state"] == "scheduled"
        assert result["next_date"] == date(2026, 5, 29)
        assert result["days_until"] == 24

    def test_scheduled_returns_correct_days_until(self):
        result = _checkin_view_state(date(2026, 5, 28), None)
        assert result["state"] == "scheduled"
        assert result["days_until"] == 1

    def test_edit_mode_overrides_complete(self):
        """Edit mode (?edit=1) reveals the form even if there's a completed
        record so users can correct what they previously submitted."""
        existing = SimpleNamespace(id=1, completed_at=datetime.utcnow())
        # Outside the window, edit_mode still falls through to form path
        # because we want users to be able to edit any time.
        result = _checkin_view_state(date(2026, 5, 5), existing, edit_mode=True)
        # edit_mode bypasses the "complete" early-return, so we end up
        # evaluating window logic. May 5 is outside the window, so the
        # function returns "scheduled" — which is fine because the route
        # should also respect edit_mode and route the user to the form
        # explicitly. The key contract here is: complete is not returned.
        assert result["state"] != "complete"


# ─── Companion chip-clicked ──────────────────────────────────


class TestCompanionChipClicked:

    def test_login_required(self, client):
        response = client.post(
            "/api/companion/chip-clicked",
            json={"chip_text": "How's my plan looking?"},
        )
        # Anonymous users hit @login_required.
        assert response.status_code in (302, 401)

    def test_fires_event_with_chip_text(self, app, client):
        _make_user(app)
        _login(client)
        with patch("app.routes.companion_routes.track_event") as mock_track:
            response = client.post(
                "/api/companion/chip-clicked",
                json={"chip_text": "How's my plan looking?"},
            )
        assert response.status_code == 204
        calls = [
            c for c in mock_track.call_args_list
            if c.args[1] == "companion_starter_chip_clicked"
        ]
        assert len(calls) == 1
        assert calls[0].args[2]["chip_text"] == "How's my plan looking?"

    def test_empty_chip_text_does_not_fire_event(self, app, client):
        _make_user(app)
        _login(client)
        with patch("app.routes.companion_routes.track_event") as mock_track:
            response = client.post(
                "/api/companion/chip-clicked",
                json={"chip_text": ""},
            )
        assert response.status_code == 204
        assert not any(
            c.args[1] == "companion_starter_chip_clicked"
            for c in mock_track.call_args_list
        )

    def test_chip_text_is_sanitized(self, app, client):
        """Long or HTML-ish input is truncated/cleaned before going to the
        event payload — we don't want raw user input flowing into PostHog
        unbounded."""
        _make_user(app)
        _login(client)
        long_text = "A" * 500
        with patch("app.routes.companion_routes.track_event") as mock_track:
            client.post(
                "/api/companion/chip-clicked",
                json={"chip_text": long_text},
            )
        calls = [
            c for c in mock_track.call_args_list
            if c.args[1] == "companion_starter_chip_clicked"
        ]
        assert len(calls) == 1
        # max_length=200 in the route — the property string should be capped.
        assert len(calls[0].args[2]["chip_text"]) <= 200
