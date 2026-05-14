"""Smoke tests for the library backdrop on emotional onboarding screens.

Pins the routing rule from the May 2026 onboarding background work:

  Emotional onboarding screens (atmospheric, contemplative)
    → /welcome, /plan-reveal — `.onboarding-library-bg` class present.

  Functional onboarding screens (dense input surfaces)
    → /factfind, /goals/choose, /trial — class absent.

The `.onboarding-library-bg` token in the rendered HTML is the marker
the CSS selector hooks into; checking the literal string in the body
is enough to verify wiring without coupling the test to inline styles
or animation timing.

plan_review.html is intentionally not tested here: at HEAD the
/onboarding/plan-review route redirects to /plan-reveal (Victoria's
UI audit c060aae merged the review content into the reveal screen).
The template is dead at HEAD. See the DEVELOPMENT.md note for the
follow-up rule if /plan-review is ever reinstated as a distinct
surface.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app import db
from app.models.user import User
from app.models.goal import Goal


def _make_user(app, email, factfind_completed):
    """Create a user with the requested factfind state. Each
    onboarding route gates on factfind_completed differently, so
    tests use a fresh user per pass rather than flipping the flag
    between requests."""
    with app.app_context():
        user = User(email=email, name="Onboard Test")
        user.set_password("testpassword123")
        user.factfind_completed = factfind_completed
        if factfind_completed:
            user.monthly_income = Decimal("3000")
            user.rent_amount = Decimal("900")
            user.bills_amount = Decimal("200")
        user.subscription_status = "active"
        user.subscription_tier = "pro_plus"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _seed_emergency_goal(app, user_id):
    with app.app_context():
        db.session.add(Goal(
            user_id=user_id,
            name="Emergency fund",
            type="savings_target",
            target_amount=Decimal("1500"),
            current_amount=Decimal("100"),
            monthly_allocation=Decimal("100"),
            priority_rank=1,
            status="active",
        ))
        db.session.commit()


def _login(client, email):
    client.post("/api/auth/login", json={
        "email": email,
        "password": "testpassword123",
    })


def test_emotional_onboarding_screens_have_library_backdrop(app, client):
    """/welcome and /plan-reveal carry the .onboarding-library-bg
    class so the atmospheric backdrop renders behind the content.
    /welcome additionally preloads the desktop WebP via head_extra.
    """
    # /welcome — factfind incomplete (otherwise redirects to /overview).
    _make_user(app, "welcome@test.com", factfind_completed=False)
    _login(client, "welcome@test.com")
    welcome = client.get("/welcome", follow_redirects=False)
    assert welcome.status_code == 200
    welcome_body = welcome.data.decode("utf-8")
    assert "onboarding-library-bg" in welcome_body
    assert "/static/images/onboarding/library-bg.webp" in welcome_body, (
        "welcome.html must preload the desktop WebP via head_extra"
    )

    # /plan-reveal — factfind complete (otherwise redirects to /factfind).
    # Separate user so the session flip cleanly to a factfind-complete
    # account; login on the same client replaces the prior session.
    uid = _make_user(app, "reveal@test.com", factfind_completed=True)
    _seed_emergency_goal(app, uid)
    _login(client, "reveal@test.com")
    reveal = client.get("/plan-reveal", follow_redirects=False)
    assert reveal.status_code == 200
    assert "onboarding-library-bg" in reveal.data.decode("utf-8")


def test_functional_onboarding_screens_do_not_have_library_backdrop(app, client):
    """Dense input surfaces stay flat black — atmospheric imagery
    hurts focus when the user is filling in numbers or making
    deliberate decisions. /factfind, /goals/choose, /trial all
    qualify.
    """
    # /factfind works with factfind incomplete.
    _make_user(app, "factfind@test.com", factfind_completed=False)
    _login(client, "factfind@test.com")
    factfind = client.get("/factfind", follow_redirects=False)
    assert factfind.status_code == 200
    assert "onboarding-library-bg" not in factfind.data.decode("utf-8")

    # /goals/choose and /trial both gate on factfind_completed.
    # Separate user with the right state from the start.
    _make_user(app, "post-factfind@test.com", factfind_completed=True)
    _login(client, "post-factfind@test.com")

    goals = client.get("/goals/choose", follow_redirects=False)
    assert goals.status_code == 200
    assert "onboarding-library-bg" not in goals.data.decode("utf-8")

    trial = client.get("/trial", follow_redirects=False)
    assert trial.status_code == 200
    assert "onboarding-library-bg" not in trial.data.decode("utf-8")


def test_library_background_image_assets_are_served(app, client):
    """The CSS path /static/images/onboarding/library-bg.* must
    actually resolve to the optimised image files. Without this
    test, a missing/misplaced asset or a static-serving path issue
    would slip through the class-rendering smoke tests above —
    the HTML would have the class, the CSS would have the rule,
    and the browser would 404 the image with nothing visible to
    the user. This is the gap that bit us on the first deploy of
    the library backdrop work.

    Asserts the three variants the CSS references are reachable
    with a 200 response and an image content-type. Doesn't try to
    validate the actual image bytes — Pillow would be needed for
    that and we don't carry it as a runtime dep.
    """
    paths_and_types = [
        ("/static/images/onboarding/library-bg.webp", "image/webp"),
        ("/static/images/onboarding/library-bg-mobile.webp", "image/webp"),
        ("/static/images/onboarding/library-bg.jpg", "image/jpeg"),
    ]
    for path, expected_type in paths_and_types:
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"{path} returned {resp.status_code}; the CSS rule "
            f"references this URL and the browser will 404 it"
        )
        content_type = resp.headers.get("Content-Type", "")
        assert content_type.startswith(expected_type), (
            f"{path} served as {content_type!r}; expected "
            f"{expected_type!r}. Wrong mime makes the browser refuse "
            f"to render the image even when bytes are correct."
        )
