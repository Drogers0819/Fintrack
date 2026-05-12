"""
Factfind route — chip-level contributions integration.

Covers the form contract introduced in Commit 2 of the
RecurringContribution refactor:

  • POST with the new JSON chip payload persists per-chip rows AND
    updates the cached aggregate column on User.
  • POST with the legacy scalar-only shape (no JSON, just the rolled-
    up total) creates a single "Legacy contributions" row so no data
    is lost from older clients.
  • POST with garbage JSON falls back to the legacy scalar path.
  • POST with no chip data and zero scalar creates no rows.
  • GET (and POST-with-errors re-render) exposes the user's prior
    chip state on the page so the JS can restore selections.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import json

import pytest

from app import db
from app.models.recurring_contribution import RecurringContribution
from app.models.user import User


def _make_user(app, email="ff@test.com"):
    with app.app_context():
        user = User(email=email, name="Factfind User")
        user.set_password("testpassword123")
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="ff@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


def _factfind_post_data(**overrides):
    """A complete-enough factfind POST. Override any field with kwargs."""
    base = {
        "monthly_income": "2500",
        "rent_amount": "800",
        "bills_amount": "200",
        "groceries_estimate": "0",
        "transport_estimate": "0",
        "subscriptions_total": "0",
        "other_commitments": "0",
        "income_day": "25",
        "employment_type": "full_time",
    }
    base.update(overrides)
    return base


# ─── New JSON chip shape ─────────────────────────────────────


class TestChipJsonShape:

    def test_post_with_chip_json_creates_rows_and_updates_cache(self, app, client):
        uid = _make_user(app)
        _login(client)

        chip_payload = json.dumps({
            "chips": [
                {"chip_id": "lisa", "label": "LISA contributions", "amount": 200},
                {"chip_id": "pension", "label": "Pension (additional)", "amount": 150},
            ],
            "custom": [{"label": "Niche payment", "amount": 25}],
        })
        resp = client.post("/factfind", data=_factfind_post_data(
            other_commitments="375",  # 200 + 150 + 25
            other_commitments_chip_data=chip_payload,
        ), follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            user = db.session.get(User, uid)
            rows = RecurringContribution.query.filter_by(
                user_id=uid, source="other_commitments",
            ).order_by(RecurringContribution.amount.desc()).all()
            assert [r.chip_id for r in rows] == ["lisa", "pension", None]
            assert [r.label for r in rows] == [
                "LISA contributions", "Pension (additional)", "Niche payment",
            ]
            assert Decimal(str(user.other_commitments)) == Decimal("375.00")

    def test_post_with_both_sources_keeps_them_separate(self, app, client):
        uid = _make_user(app)
        _login(client)

        subs_payload = json.dumps({
            "chips": [{"chip_id": "netflix", "label": "Netflix", "amount": 10.99}],
            "custom": [],
        })
        other_payload = json.dumps({
            "chips": [{"chip_id": "lisa", "label": "LISA contributions", "amount": 200}],
            "custom": [],
        })
        resp = client.post("/factfind", data=_factfind_post_data(
            subscriptions_total="10.99",
            subscriptions_chip_data=subs_payload,
            other_commitments="200",
            other_commitments_chip_data=other_payload,
        ), follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            subs = RecurringContribution.query.filter_by(
                user_id=uid, source="subscriptions",
            ).all()
            others = RecurringContribution.query.filter_by(
                user_id=uid, source="other_commitments",
            ).all()
            assert [r.chip_id for r in subs] == ["netflix"]
            assert [r.chip_id for r in others] == ["lisa"]

    def test_resync_replaces_chips_on_second_post(self, app, client):
        uid = _make_user(app)
        _login(client)

        first = json.dumps({
            "chips": [{"chip_id": "netflix", "label": "Netflix", "amount": 10.99}],
            "custom": [],
        })
        client.post("/factfind", data=_factfind_post_data(
            subscriptions_total="10.99", subscriptions_chip_data=first,
        ))

        second = json.dumps({
            "chips": [{"chip_id": "spotify", "label": "Spotify", "amount": 11}],
            "custom": [],
        })
        client.post("/factfind", data=_factfind_post_data(
            subscriptions_total="11", subscriptions_chip_data=second,
        ))

        with app.app_context():
            rows = RecurringContribution.query.filter_by(
                user_id=uid, source="subscriptions",
            ).all()
            assert len(rows) == 1
            assert rows[0].chip_id == "spotify"


# ─── Legacy / fallback paths ─────────────────────────────────


class TestLegacyFallback:

    def test_post_without_json_with_scalar_creates_legacy_row(self, app, client):
        """Older client posts only the rolled-up scalar. We must not
        drop the user's data — create a Legacy contributions row."""
        uid = _make_user(app)
        _login(client)
        resp = client.post("/factfind", data=_factfind_post_data(
            subscriptions_total="42",
            # subscriptions_chip_data deliberately absent
        ), follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            rows = RecurringContribution.query.filter_by(
                user_id=uid, source="subscriptions",
            ).all()
            assert len(rows) == 1
            assert rows[0].chip_id is None
            assert rows[0].label.lower().startswith("legacy contributions")
            assert Decimal(str(rows[0].amount)) == Decimal("42.00")

    def test_post_with_garbage_json_falls_back_to_scalar(self, app, client):
        uid = _make_user(app)
        _login(client)
        resp = client.post("/factfind", data=_factfind_post_data(
            other_commitments="100",
            other_commitments_chip_data="not valid json{",
        ), follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            rows = RecurringContribution.query.filter_by(
                user_id=uid, source="other_commitments",
            ).all()
            assert len(rows) == 1
            assert rows[0].chip_id is None
            assert Decimal(str(rows[0].amount)) == Decimal("100.00")

    def test_post_with_zero_scalar_and_no_json_writes_no_rows(self, app, client):
        """User who fills the rest of factfind but ticks no chips gets
        zero rows and a zero cached aggregate."""
        uid = _make_user(app)
        _login(client)
        resp = client.post("/factfind", data=_factfind_post_data())
        assert resp.status_code == 302

        with app.app_context():
            assert RecurringContribution.query.filter_by(user_id=uid).count() == 0
            user = db.session.get(User, uid)
            assert (
                user.subscriptions_total is None
                or Decimal(str(user.subscriptions_total)) == Decimal("0")
            )


# ─── Edit-time chip state restoration ────────────────────────


class TestChipStateRestoration:

    def test_factfind_get_includes_chip_state_for_existing_contributions(
        self, app, client,
    ):
        """After a user has filed contributions, opening factfind again
        must expose their prior chip selection in the rendered HTML so
        the JS can restore the checkboxes + amounts."""
        uid = _make_user(app)
        _login(client)

        chip_payload = json.dumps({
            "chips": [
                {"chip_id": "lisa", "label": "LISA contributions", "amount": 200},
            ],
            "custom": [],
        })
        client.post("/factfind", data=_factfind_post_data(
            other_commitments="200",
            other_commitments_chip_data=chip_payload,
        ))

        # Now GET. Chip state should be embedded.
        resp = client.get("/factfind")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "other_commitments_chip_state" in body
        # The JSON inside the script tag should mention our chip.
        assert '"chip_id": "lisa"' in body or "'chip_id': 'lisa'" in body or '"lisa"' in body
        assert "LISA contributions" in body

    def test_factfind_get_passes_empty_state_for_new_user(self, app, client):
        """A brand-new user (no contributions yet) gets an empty-array
        chip state, not a missing variable, so the template renders
        cleanly without an UndefinedError."""
        _make_user(app)
        _login(client)
        resp = client.get("/factfind")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "subscriptions_chip_state" in body
        assert "other_commitments_chip_state" in body
