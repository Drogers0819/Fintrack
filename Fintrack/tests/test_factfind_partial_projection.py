"""Regression test for the factfind 'Early estimate' card copy.

The card is a JS-driven preview that updates as the user types income /
rent / bills. Originally it subtracted only rent from income, which
gave an inflated surplus until the user finished the form. Fix landed
on 2026-05-14: subtract rent AND bills, and reword the copy to match.

This test pins the new copy strings so a future refactor that quietly
restores the old "after rent" wording (or removes the explanatory line)
trips the test. It does not parse or execute the JS — that would be
brittle. Behavioural verification is a local-browser concern, not a
test-suite concern.
"""

from app import db
from app.models.user import User


def _make_user(app, email="ff@test.com"):
    with app.app_context():
        user = User(email=email, name="Factfind Test")
        user.set_password("testpassword123")
        user.factfind_completed = False
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="ff@test.com"):
    client.post("/api/auth/login", json={
        "email": email,
        "password": "testpassword123",
    })


def test_factfind_early_estimate_copy_reflects_rent_and_bills(app, client):
    _make_user(app)
    _login(client)
    resp = client.get("/factfind")
    assert resp.status_code == 200
    body = resp.data.decode("utf-8")

    # New trailing label and explanatory line.
    assert "/month after rent and bills" in body
    assert (
        "Based on income, rent, and bills. "
        "Subscriptions and spending still to come."
    ) in body

    # Old strings must be gone — guards against partial reverts.
    assert "/month left after rent" not in body
    assert "before bills and spending" not in body
