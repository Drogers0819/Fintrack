"""
Signposting library — Block 2 Task 2.7.

Coverage:
  • Library structure — IDs unique, URLs https, categories valid,
    every resource has the required fields, every category in the
    enum has at least one resource (except the relationships
    placeholder).
  • Lookups — get_resource by id, get_resources_for_category,
    get_resources_for_categories deduplicates.
  • Template integration — crisis flow pages render resource lists
    with proper external-link hardening.
  • Admin gate — founder email gets through, anyone else gets 404.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models.user import User


# ─── Library structure ───────────────────────────────────────


class TestLibraryStructure:

    def test_all_ids_are_unique(self):
        from app.services.signposting_library import SIGNPOSTING_RESOURCES
        ids = [r["id"] for r in SIGNPOSTING_RESOURCES]
        assert len(ids) == len(set(ids)), f"duplicate ids: {ids}"

    def test_all_urls_are_https(self):
        from app.services.signposting_library import SIGNPOSTING_RESOURCES
        for resource in SIGNPOSTING_RESOURCES:
            assert resource["url"].startswith("https://"), (
                f"{resource['id']} has non-https URL: {resource['url']}"
            )

    def test_all_categories_are_in_enum(self):
        from app.services.signposting_library import (
            CATEGORIES, SIGNPOSTING_RESOURCES,
        )
        for resource in SIGNPOSTING_RESOURCES:
            for cat in resource["categories"]:
                assert cat in CATEGORIES, (
                    f"{resource['id']} references unknown category {cat}"
                )

    def test_required_fields_present(self):
        from app.services.signposting_library import SIGNPOSTING_RESOURCES
        required = {"id", "name", "url", "description", "categories", "free"}
        for resource in SIGNPOSTING_RESOURCES:
            missing = required - set(resource.keys())
            assert not missing, f"{resource.get('id')} missing fields: {missing}"

    def test_every_real_category_has_at_least_one_resource(self):
        """relationships is the placeholder; everything else must have
        at least one resource so the lookup never returns []
        unexpectedly in production."""
        from app.services.signposting_library import (
            CATEGORIES, get_resources_for_category,
        )
        for cat in CATEGORIES:
            if cat == "relationships":
                continue
            assert get_resources_for_category(cat), (
                f"category {cat!r} has no resources"
            )

    def test_all_resources_are_free(self):
        """Hard rule: nothing paid in the library, ever."""
        from app.services.signposting_library import SIGNPOSTING_RESOURCES
        for resource in SIGNPOSTING_RESOURCES:
            assert resource["free"] is True, (
                f"{resource['id']} is not marked free"
            )

    def test_eight_starting_resources(self):
        """Sanity check on the starting set size — guards against
        accidental deletions."""
        from app.services.signposting_library import SIGNPOSTING_RESOURCES
        assert len(SIGNPOSTING_RESOURCES) >= 8


# ─── Lookups ─────────────────────────────────────────────────


class TestLookups:

    def test_get_resource_returns_match(self):
        from app.services.signposting_library import get_resource
        r = get_resource("stepchange")
        assert r is not None
        assert r["name"] == "StepChange"

    def test_get_resource_returns_none_for_unknown(self):
        from app.services.signposting_library import get_resource
        assert get_resource("does_not_exist") is None

    def test_get_resources_for_category_returns_debt_set(self):
        from app.services.signposting_library import get_resources_for_category
        names = [r["id"] for r in get_resources_for_category("debt")]
        assert "stepchange" in names
        assert "national_debtline" in names

    def test_get_resources_for_category_unknown_returns_empty(self):
        from app.services.signposting_library import get_resources_for_category
        assert get_resources_for_category("not_a_category") == []

    def test_get_resources_for_categories_dedupes(self):
        """gamcare is tagged with both gambling and mental_health — it
        should only appear once when both categories are queried."""
        from app.services.signposting_library import get_resources_for_categories
        results = get_resources_for_categories(["gambling", "mental_health"])
        ids = [r["id"] for r in results]
        assert ids.count("gamcare") == 1


# ─── Template integration ────────────────────────────────────


def _make_user(app, email="signpost@test.com", name="Signpost User",
               *, monthly_income=2000):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.monthly_income = Decimal(str(monthly_income))
        user.rent_amount = Decimal("800")
        user.bills_amount = Decimal("200")
        user.factfind_completed = True
        user.subscription_status = "trialing"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="signpost@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


class TestTemplateIntegration:

    def test_crisis_pause_renders_library_resources(self, app, client):
        _make_user(app)
        _login(client)
        resp = client.get("/crisis/pause")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # Pause page surfaces mental_health + debt categories.
        assert "Samaritans" in body
        assert "Mind" in body
        assert "StepChange" in body
        # External-link hardening from the partial.
        assert 'rel="noopener noreferrer"' in body
        assert 'target="_blank"' in body

    def test_crisis_income_response_renders_library_resources(self, app, client):
        from datetime import date
        _make_user(app, monthly_income=2400)
        _login(client)
        resp = client.post("/crisis/income", data={
            "change_type": "reduced_hours",
            "new_monthly_income": "2200",  # small drop, no survival mode
            "occurred_on": date.today().isoformat(),
        })
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # debt/general/benefits set should surface StepChange + MoneyHelper + Citizens Advice
        assert "StepChange" in body
        assert "MoneyHelper" in body
        assert "Citizens Advice" in body

    def test_partial_renders_phone_when_present(self, app):
        """Samaritans has both a phone and an email; the partial must
        render both as clickable links."""
        from app.services.signposting_library import get_resource
        with app.test_request_context():
            from flask import render_template
            samaritans = get_resource("samaritans")
            html = render_template(
                "_partials/signposting_list.html",
                resources=[samaritans],
            )
            assert 'tel:116123' in html
            assert "mailto:jo@samaritans.org" in html


# ─── Admin gate ──────────────────────────────────────────────


class TestAdminAuditPage:

    def test_founder_email_can_access(self, app, client):
        with app.app_context():
            user = User(email="daniel.rogers19@hotmail.com",
                        name="Daniel Rogers")
            user.set_password("testpassword123")
            user.subscription_status = "active"
            user.subscription_tier = "pro_plus"
            user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
            db.session.add(user)
            db.session.commit()

        client.post("/api/auth/login", json={
            "email": "daniel.rogers19@hotmail.com",
            "password": "testpassword123",
        })
        resp = client.get("/admin/signposting")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Signposting library" in body
        assert "StepChange" in body
        assert "Samaritans" in body

    def test_non_founder_gets_404(self, app, client):
        """Civilian logged-in user shouldn't even know the route exists."""
        _make_user(app, email="civilian@test.com")
        _login(client, email="civilian@test.com")
        resp = client.get("/admin/signposting")
        assert resp.status_code == 404

    def test_anonymous_user_gets_redirected_or_404(self, app, client):
        """Either login_required redirects, or the founder gate 404s.
        Both are acceptable; what's not acceptable is 200."""
        resp = client.get("/admin/signposting", follow_redirects=False)
        assert resp.status_code in (302, 401, 404)
