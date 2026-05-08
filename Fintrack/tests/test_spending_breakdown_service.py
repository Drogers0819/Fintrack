"""
Spending breakdown ring chart — service-layer coverage.

Goals:
  • Empty state behaves cleanly (no spending → no segments).
  • Segments are sorted descending by amount.
  • Income / Transfer rows are excluded from the ring.
  • Each category gets its harmonised colour, not a rank-based one.
  • SVG arc math: dasharrays sum (visibly) to the full circumference,
    cumulative dashoffset chains adjacent segments.
  • Single-category case fills the ring.
  • Month / year parameters work.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(app, email="ring@test.com", name="Ring User"):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.factfind_completed = True
        user.monthly_income = Decimal("2500")
        user.rent_amount = Decimal("800")
        user.bills_amount = Decimal("200")
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _category_id(app, name):
    with app.app_context():
        cat = Category.query.filter_by(name=name).first()
        if cat is None:
            cat = Category(name=name)
            db.session.add(cat)
            db.session.commit()
        return cat.id


def _add_expense(app, user_id, category_name, amount, *, when=None):
    with app.app_context():
        cat_id = _category_id(app, category_name)
        txn = Transaction(
            user_id=user_id,
            amount=Decimal(str(amount)),
            description=f"{category_name} spend",
            category_id=cat_id,
            type="expense",
            date=when or date.today(),
        )
        db.session.add(txn)
        db.session.commit()
        return txn.id


# ─── Empty state ─────────────────────────────────────────────


class TestEmptyState:

    def test_empty_state_for_user_with_no_spending(self, app):
        from app.services.spending_breakdown_service import (
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user)
            assert result["total_spent"] == 0.0
            assert result["categories"] == []
            assert "month_label" in result and result["month_label"]


# ─── Sort + filter ───────────────────────────────────────────


class TestSortAndFilter:

    def test_categories_sorted_descending_by_amount(self, app):
        from app.services.spending_breakdown_service import (
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        _add_expense(app, uid, "Food", 80)
        _add_expense(app, uid, "Bills", 250)
        _add_expense(app, uid, "Transport", 40)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user)
            names = [c["name"] for c in result["categories"]]
            assert names == ["Bills", "Food", "Transport"]

    def test_income_and_transfer_excluded_from_ring(self, app):
        """The ring is for spending only — Income/Transfer rows are
        out of scope for this visualisation."""
        from app.services.spending_breakdown_service import (
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        _add_expense(app, uid, "Food", 100)
        _add_expense(app, uid, "Transfer", 500)
        # An "Income" row shouldn't normally exist with type=expense,
        # but if a stray one were tagged that way we'd still drop it.
        _add_expense(app, uid, "Income", 200)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user)
            names = [c["name"] for c in result["categories"]]
            assert "Transfer" not in names
            assert "Income" not in names
            assert "Food" in names

    def test_other_month_returns_empty_when_filter_doesnt_match(self, app):
        from app.services.spending_breakdown_service import (
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        # Only a January expense exists.
        _add_expense(app, uid, "Food", 100, when=date(2026, 1, 15))

        with app.app_context():
            user = db.session.get(User, uid)
            # Asking for May 2026 — no rows match.
            result = get_spending_breakdown_for_user(user, month=5, year=2026)
            assert result["total_spent"] == 0.0
            assert result["categories"] == []


# ─── Colour mapping ──────────────────────────────────────────


class TestColourMapping:

    def test_category_gets_harmonised_colour(self, app):
        from app.services.spending_breakdown_service import (
            RING_CATEGORY_COLOURS,
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        _add_expense(app, uid, "Food", 50)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user)
            food = next(c for c in result["categories"] if c["name"] == "Food")
            assert food["colour"] == RING_CATEGORY_COLOURS["Food"]
            # Defensive: it must be the harmonised mapping, not the
            # vivid #E07A5F seed.
            assert food["colour"] != "#E07A5F"

    def test_unknown_category_falls_back_to_neutral(self, app):
        from app.services.spending_breakdown_service import (
            colour_for_category,
        )
        # An unmapped name must return SOMETHING — not raise.
        result = colour_for_category("Made-up category")
        assert isinstance(result, str)
        assert result.startswith("#")


# ─── SVG arc math ────────────────────────────────────────────


class TestArcMath:

    def test_single_category_fills_ring(self, app):
        from app.services.spending_breakdown_service import (
            RING_CIRCUMFERENCE,
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        _add_expense(app, uid, "Food", 100)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user)
            assert len(result["categories"]) == 1
            seg = result["categories"][0]
            # The visible arc should equal the full circumference (gap ~ 0).
            arc_str, gap_str = seg["stroke_dasharray"].split()
            arc = float(arc_str)
            gap = float(gap_str)
            assert abs(arc - RING_CIRCUMFERENCE) < 0.5
            assert abs(gap) < 0.5
            assert seg["percentage"] == 100.0
            # First segment offset is zero.
            assert float(seg["stroke_dashoffset"]) == 0.0

    def test_two_categories_arcs_sum_to_circumference(self, app):
        from app.services.spending_breakdown_service import (
            RING_CIRCUMFERENCE,
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        _add_expense(app, uid, "Food", 60)
        _add_expense(app, uid, "Bills", 40)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user)
            arcs = [
                float(c["stroke_dasharray"].split()[0])
                for c in result["categories"]
            ]
            # The sum of the visible arcs should equal the circumference
            # (within rounding tolerance).
            assert abs(sum(arcs) - RING_CIRCUMFERENCE) < 0.5

    def test_subsequent_segment_dashoffset_chains(self, app):
        from app.services.spending_breakdown_service import (
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        _add_expense(app, uid, "Food", 60)
        _add_expense(app, uid, "Bills", 40)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user)
            first, second = result["categories"]
            first_arc = float(first["stroke_dasharray"].split()[0])
            # Segment 2 is offset by the negative arc length of seg 1.
            second_offset = float(second["stroke_dashoffset"])
            assert abs(second_offset + first_arc) < 0.5

    def test_percentages_round_sensibly(self, app):
        from app.services.spending_breakdown_service import (
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        _add_expense(app, uid, "Food", 75)
        _add_expense(app, uid, "Bills", 25)

        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user)
            food = next(c for c in result["categories"] if c["name"] == "Food")
            bills = next(c for c in result["categories"] if c["name"] == "Bills")
            assert food["percentage"] == 75.0
            assert bills["percentage"] == 25.0


# ─── Month label ─────────────────────────────────────────────


class TestMonthLabel:

    def test_month_label_uses_provided_month_year(self, app):
        from app.services.spending_breakdown_service import (
            get_spending_breakdown_for_user,
        )
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            result = get_spending_breakdown_for_user(user, month=5, year=2026)
            assert result["month_label"] == "May 2026"
