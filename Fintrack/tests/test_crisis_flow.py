"""
Crisis flow — Block 2 Task 2.4.

Coverage:
  • Routes — landing renders, sub-routes render the right templates,
    each form requires authentication, validation rejects nonsense.
  • Service logic — record_lost_income updates monthly_income or
    leaves it alone for the unknown branch, record_unexpected_cost
    leaves user state untouched, calculate_cost_absorption reuses
    can_i_afford and adds the signposting flag, record_pause_request
    captures the row.
  • Analytics — landing, income submission, cost submission, pause
    request, and contextual-link click each fire the right event.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import db
from app.models.crisis_event import CrisisEvent
from app.models.user import User


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(
    app,
    email="crisis@test.com",
    name="Crisis User",
    *,
    monthly_income=2000,
    factfind=True,
):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.monthly_income = Decimal(str(monthly_income))
        user.rent_amount = Decimal("800")
        user.bills_amount = Decimal("200")
        user.factfind_completed = factfind
        user.subscription_status = "trialing"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="crisis@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


# ─── Service: record_lost_income ─────────────────────────────


class TestRecordLostIncome:

    def test_updates_monthly_income_when_value_provided(self, app):
        from app.services.crisis_service import record_lost_income

        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            event = record_lost_income(
                user,
                change_type="reduced_hours",
                new_monthly_income=1200,
                occurred_on=date(2026, 5, 1),
            )
            assert event.id is not None
            assert event.event_type == "lost_income"
            assert event.income_change_type == "reduced_hours"
            assert float(event.new_monthly_income) == 1200.0

            user = db.session.get(User, uid)
            assert float(user.monthly_income) == 1200.0

    def test_unknown_branch_does_not_change_monthly_income(self, app):
        """`I don't know yet` writes the event but leaves monthly_income
        alone so the plan keeps using the previous figure."""
        from app.services.crisis_service import record_lost_income

        uid = _make_user(app, monthly_income=2400)
        with app.app_context():
            user = db.session.get(User, uid)
            event = record_lost_income(
                user,
                change_type="job_loss",
                new_monthly_income=None,
                income_unknown=True,
                occurred_on=date(2026, 5, 1),
            )
            assert event.income_unknown is True
            assert event.new_monthly_income is None

            user = db.session.get(User, uid)
            assert float(user.monthly_income) == 2400.0


# ─── Service: record_unexpected_cost ─────────────────────────


class TestRecordUnexpectedCost:

    def test_creates_event_without_mutating_user(self, app):
        from app.services.crisis_service import record_unexpected_cost

        uid = _make_user(app, monthly_income=2000)
        with app.app_context():
            user = db.session.get(User, uid)
            event = record_unexpected_cost(
                user,
                description="boiler repair",
                amount=320,
                already_paid=False,
                occurred_on=date(2026, 5, 1),
            )
            assert event.event_type == "unexpected_cost"
            assert event.cost_description == "boiler repair"
            assert float(event.cost_amount) == 320.0
            assert event.cost_already_paid is False

            user = db.session.get(User, uid)
            assert float(user.monthly_income) == 2000.0


# ─── Service: record_pause_request ───────────────────────────


class TestRecordPauseRequest:

    def test_creates_event_with_correct_type(self, app):
        from app.services.crisis_service import record_pause_request

        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            event = record_pause_request(user)
            assert event.event_type == "pause_requested"
            # All the optional fields stay None.
            assert event.cost_amount is None
            assert event.income_change_type is None


# ─── Service: calculate_cost_absorption ──────────────────────


class TestCalculateCostAbsorption:

    def test_absorbable_cost_returns_affordable(self, app):
        """A small cost against a healthy plan should come back
        affordable from the lifestyle pot."""
        from app.services.crisis_service import calculate_cost_absorption

        uid = _make_user(app, monthly_income=3000)
        with app.app_context():
            user = db.session.get(User, uid)
            result = calculate_cost_absorption(user, 50)
            assert result["affordable"] is True
            assert "surplus" in result
            assert "show_signposting" in result
            assert result["show_signposting"] is False

    def test_large_cost_triggers_signposting(self, app):
        """Cost over £500 surfaces the free-resource links regardless
        of whether the plan can absorb it."""
        from app.services.crisis_service import calculate_cost_absorption

        uid = _make_user(app, monthly_income=3000)
        with app.app_context():
            user = db.session.get(User, uid)
            result = calculate_cost_absorption(user, 800)
            assert result["show_signposting"] is True

    def test_cost_over_half_surplus_triggers_signposting(self, app):
        """Even small absolute amounts trigger signposting if they're
        more than half the user's monthly surplus."""
        from app.services.crisis_service import calculate_cost_absorption

        uid = _make_user(app, monthly_income=1100)  # surplus is small
        with app.app_context():
            user = db.session.get(User, uid)
            result = calculate_cost_absorption(user, 80)
            assert result["show_signposting"] is True


# ─── Routes: GET ─────────────────────────────────────────────


class TestCrisisRoutesRequireAuth:

    def test_landing_redirects_when_anonymous(self, app, client):
        resp = client.get("/crisis/", follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_income_post_redirects_when_anonymous(self, app, client):
        resp = client.post("/crisis/income", data={}, follow_redirects=False)
        assert resp.status_code in (302, 401)


class TestCrisisLandingPage:

    def test_get_renders_three_options(self, app, client):
        _make_user(app)
        _login(client)
        resp = client.get("/crisis/")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Something's changed?" in body
        assert "I've lost income" in body
        assert "I have an unexpected cost" in body
        assert "I just need to pause" in body

    def test_get_fires_landing_viewed_event(self, app, client):
        _make_user(app)
        _login(client)
        with patch("app.routes.crisis_routes.track_event") as track:
            client.get("/crisis/?source=overview")

        events = [c.args[1] for c in track.call_args_list if len(c.args) >= 2]
        assert "crisis_landing_viewed" in events
        landing_call = next(c for c in track.call_args_list if c.args[1] == "crisis_landing_viewed")
        assert landing_call.args[2]["source"] == "overview"


class TestCrisisIncomeRoute:

    def test_get_renders_form(self, app, client):
        _make_user(app)
        _login(client)
        resp = client.get("/crisis/income")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "What's changed?" in body
        assert "name=\"change_type\" value=\"job_loss\"" in body
        assert "I don't know yet" in body

    def test_post_creates_event_and_updates_monthly_income(self, app, client):
        uid = _make_user(app, monthly_income=2400)
        _login(client)
        with patch("app.routes.crisis_routes.track_event") as track:
            resp = client.post("/crisis/income", data={
                "change_type": "reduced_hours",
                "new_monthly_income": "1500",
                "occurred_on": date.today().isoformat(),
            })

        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Got it." in body  # response page header

        with app.app_context():
            user = db.session.get(User, uid)
            assert float(user.monthly_income) == 1500.0
            event = CrisisEvent.query.filter_by(user_id=uid).first()
            assert event is not None
            assert event.event_type == "lost_income"
            assert float(event.new_monthly_income) == 1500.0

        events = [c.args[1] for c in track.call_args_list if len(c.args) >= 2]
        assert "crisis_income_submitted" in events

    def test_post_with_invalid_change_type_redirects(self, app, client):
        uid = _make_user(app)
        _login(client)
        resp = client.post("/crisis/income", data={
            "change_type": "garbage",
            "new_monthly_income": "1500",
        }, follow_redirects=False)
        assert resp.status_code == 302
        with app.app_context():
            assert CrisisEvent.query.filter_by(user_id=uid).count() == 0

    def test_post_without_income_or_unknown_redirects(self, app, client):
        """At least one of monthly income or income_unknown is required."""
        uid = _make_user(app)
        _login(client)
        resp = client.post("/crisis/income", data={
            "change_type": "job_loss",
        }, follow_redirects=False)
        assert resp.status_code == 302
        with app.app_context():
            assert CrisisEvent.query.filter_by(user_id=uid).count() == 0

    def test_post_with_future_occurred_on_rejected(self, app, client):
        uid = _make_user(app)
        _login(client)
        future = (date.today() + timedelta(days=2)).isoformat()
        resp = client.post("/crisis/income", data={
            "change_type": "reduced_hours",
            "new_monthly_income": "1500",
            "occurred_on": future,
        }, follow_redirects=False)
        assert resp.status_code == 302
        with app.app_context():
            assert CrisisEvent.query.filter_by(user_id=uid).count() == 0


class TestCrisisCostRoute:

    def test_get_renders_form(self, app, client):
        _make_user(app)
        _login(client)
        resp = client.get("/crisis/cost")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "What's the cost for?" in body
        assert "How much?" in body

    def test_post_creates_event_and_renders_response(self, app, client):
        uid = _make_user(app, monthly_income=2500)
        _login(client)
        with patch("app.routes.crisis_routes.track_event") as track:
            resp = client.post("/crisis/cost", data={
                "description": "boiler repair",
                "amount": "320",
                "already_paid": "no",
                "occurred_on": date.today().isoformat(),
            })

        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "boiler repair" in body
        assert "£320.00" in body

        with app.app_context():
            event = CrisisEvent.query.filter_by(user_id=uid).first()
            assert event is not None
            assert event.event_type == "unexpected_cost"
            assert float(event.cost_amount) == 320.0
            assert event.cost_already_paid is False

        submit_calls = [c for c in track.call_args_list
                        if len(c.args) >= 2 and c.args[1] == "crisis_cost_submitted"]
        assert len(submit_calls) == 1
        props = submit_calls[0].args[2]
        assert props["amount"] == 320.0
        assert "absorbable" in props

    def test_post_with_negative_amount_rejected(self, app, client):
        uid = _make_user(app)
        _login(client)
        resp = client.post("/crisis/cost", data={
            "description": "test",
            "amount": "-50",
            "already_paid": "no",
        }, follow_redirects=False)
        assert resp.status_code == 302
        with app.app_context():
            assert CrisisEvent.query.filter_by(user_id=uid).count() == 0

    def test_post_with_blank_description_rejected(self, app, client):
        uid = _make_user(app)
        _login(client)
        resp = client.post("/crisis/cost", data={
            "description": "",
            "amount": "100",
            "already_paid": "yes",
        }, follow_redirects=False)
        assert resp.status_code == 302
        with app.app_context():
            assert CrisisEvent.query.filter_by(user_id=uid).count() == 0


class TestCrisisPauseRoute:

    def test_get_renders_signposting(self, app, client):
        _make_user(app)
        _login(client)
        resp = client.get("/crisis/pause")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Sometimes life needs space" in body
        assert "Samaritans" in body
        assert "mailto:hello@getclaro.co.uk" in body

    def test_post_creates_pause_event(self, app, client):
        uid = _make_user(app)
        _login(client)
        with patch("app.routes.crisis_routes.track_event") as track:
            resp = client.post("/crisis/pause", data={})

        assert resp.status_code == 204
        with app.app_context():
            event = CrisisEvent.query.filter_by(user_id=uid).first()
            assert event is not None
            assert event.event_type == "pause_requested"

        events = [c.args[1] for c in track.call_args_list if len(c.args) >= 2]
        assert "crisis_pause_requested" in events


# ─── Click tracker ───────────────────────────────────────────


class TestCrisisLinkClickedEndpoint:

    def test_post_fires_crisis_link_clicked(self, app, client):
        _make_user(app)
        _login(client)
        with patch("app.routes.crisis_routes.track_event") as track:
            resp = client.post(
                "/crisis/api/link-clicked",
                json={"location": "overview"},
            )
        assert resp.status_code == 204

        clicked = [c for c in track.call_args_list
                   if len(c.args) >= 2 and c.args[1] == "crisis_link_clicked"]
        assert len(clicked) == 1
        assert clicked[0].args[2]["location"] == "overview"

    def test_post_requires_login(self, app, client):
        resp = client.post(
            "/crisis/api/link-clicked",
            json={"location": "overview"},
            follow_redirects=False,
        )
        assert resp.status_code in (302, 401)
