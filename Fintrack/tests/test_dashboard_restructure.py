"""Smoke + safety tests for the May 2026 dashboard restructure.

Covers:
  • Combined Net Worth + This Month chip renders both halves on /overview.
  • "Has something changed?" card renders on /plan with the
    /factfind?edit=1 link.
  • plan_summary_html decoration emits a coloured dot before a known
    goal name when the goal is in the active plan.
  • HTML injection via a goal name does NOT escape the markupsafe
    wrapper. A goal called "<script>alert(1)</script>" must be
    rendered as escaped text inside the decorated markup, never as
    live HTML.

The four tests below are explicit about what they prove. They do NOT
attempt to lock down every visual detail — that would couple the test
suite to inline styles and slow future iteration.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models.user import User
from app.models.goal import Goal
from app.routes.page_routes import _decorate_plan_summary_with_goal_dots


def _make_user(
    app,
    email="dash@test.com",
    name="Dashboard User",
    factfind_completed=True,
):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.factfind_completed = factfind_completed
        user.monthly_income = Decimal("3000")
        user.rent_amount = Decimal("900")
        user.bills_amount = Decimal("200")
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _add_goal(app, user_id, name, target=2000, current=200, allocation=150):
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            target_amount=Decimal(str(target)),
            current_amount=Decimal(str(current)),
            monthly_allocation=Decimal(str(allocation)),
            priority_rank=1,
            status="active",
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


def _login(client, email="dash@test.com"):
    client.post("/api/auth/login", json={
        "email": email,
        "password": "testpassword123",
    })


class TestOverviewTopRowChip:

    def test_combined_net_worth_this_month_chip_renders_both_halves(self, app, client):
        """The chip's left half shows the Net Worth label, the right
        half shows the This Month label and its three rows (Saved,
        Spending, Progress). Both must be present in the overview
        markup when a factfind-complete user with at least one active
        goal hits /overview."""
        uid = _make_user(app)
        _add_goal(app, uid, "Emergency fund", target=1000, current=200, allocation=100)
        _login(client)

        response = client.get("/overview")
        assert response.status_code == 200
        body = response.data.decode("utf-8")

        # Left half — Net worth label is shown.
        assert "Net worth" in body
        # Right half — This Month rows are present.
        assert "This month" in body
        assert ">Saved<" in body
        assert ">Spending<" in body
        assert ">Progress<" in body


class TestPlanHasSomethingChangedCard:

    def test_card_renders_with_factfind_edit_link(self, app, client):
        uid = _make_user(app)
        _add_goal(app, uid, "Holiday")
        _login(client)

        response = client.get("/plan")
        assert response.status_code == 200
        body = response.data.decode("utf-8")

        # Card eyebrow + headline question (verbatim).
        assert "Has something changed?" in body
        assert "Salary changed, new bill, lost income, big purchase coming up?" in body
        # The Update button links to the factfind edit flow.
        assert "/factfind?edit=1" in body


class TestPlanSummaryGoalDots:

    def test_active_goal_name_gets_bold_emphasis(self, app):
        """When the plan summary references an active goal, the
        decorated output wraps the goal name in a bold span. The
        helper was originally written to emit a coloured dot prefix
        (--goal-stroke-* CSS variable); c060aae replaced that with
        bold-text emphasis for WCAG colour-contrast reasons. The
        function name retains 'with_goal_dots' for backward
        compatibility — the marker on the goal mention is now
        weight, not colour.
        """
        with app.app_context():
            plan_summary = "Your Emergency fund is closest to completion."
            smart_plan = {
                "pots": [
                    {"goal_id": 7, "name": "Emergency fund",
                     "monthly_amount": 100},
                ],
            }
            decorated = _decorate_plan_summary_with_goal_dots(
                plan_summary, smart_plan,
            )
            assert decorated is not None
            html = str(decorated)
            # Bold span wraps the matched goal name.
            assert 'font-weight:600' in html
            assert '<span style="font-weight:600;">Emergency fund</span>' in html

    def test_no_active_goals_returns_none(self, app):
        """When no active goals match the text, the helper returns
        None so the template falls back to the plain plan_summary
        string. Avoids escaping perfectly normal text unnecessarily.
        """
        with app.app_context():
            decorated = _decorate_plan_summary_with_goal_dots(
                "Some plan text with no matching goal.",
                {"pots": [
                    {"goal_id": 1, "name": "Holiday", "monthly_amount": 50},
                ]},
            )
            assert decorated is None

    def test_html_injection_via_goal_name_is_escaped(self, app):
        """SECURITY: a malicious-looking goal name must not produce
        live HTML in the decorated output. The markupsafe wrapper
        escapes the matched text before emitting it back, and the
        regex pattern is built from the escaped name so the match
        target itself is the safe form.

        Even if a user could persist a goal named
        '<script>alert(1)</script>' (the route would reject it via
        sanitisation; this is belt-and-braces), the dashboard must
        never render it as executable markup.
        """
        with app.app_context():
            evil_name = "<script>alert(1)</script>"
            plan_summary = f"You contributed to {evil_name} this month."
            smart_plan = {
                "pots": [
                    {"goal_id": 99, "name": evil_name,
                     "monthly_amount": 10},
                ],
            }
            decorated = _decorate_plan_summary_with_goal_dots(
                plan_summary, smart_plan,
            )
            html = str(decorated) if decorated is not None else ""
            # The raw <script> tag must not appear — only its escaped form.
            assert "<script>alert(1)</script>" not in html
            assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
