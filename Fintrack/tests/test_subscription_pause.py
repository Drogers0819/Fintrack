"""
Hardship subscription pause — Block 2 Task 2.6.

Stripe testing discipline: every Stripe SDK call is mocked
(stripe.Subscription.modify, stripe.Webhook.construct_event). No
real network traffic from this suite.

Coverage:
  • Eligibility — every path through is_pause_eligible.
  • Initiation — duration validation, success path, Stripe error
    handling, audit row + user state mutations.
  • Manual resume — clears flag, writes audit, handles Stripe error,
    handles already-resumed.
  • Webhook — auto-resume detection from previous_attributes,
    duplicate delivery idempotency, unknown user, non-pause update.
  • Routes — eligible vs ineligible rendering, confirmation step,
    successful POST flow, manual resume from settings, login gating.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import db
from app.models.subscription_event import SubscriptionEvent
from app.models.user import User


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(
    app,
    email="pauser@test.com",
    name="Pauser",
    *,
    tier="pro_plus",
    status="active",
    stripe_subscription_id="sub_test_abc",
    stripe_customer_id="cus_test_xyz",
    paused_until=None,
    last_paused=None,
):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.monthly_income = Decimal("2500")
        user.rent_amount = Decimal("800")
        user.bills_amount = Decimal("200")
        user.factfind_completed = True
        user.subscription_tier = tier
        user.subscription_status = status
        user.stripe_subscription_id = stripe_subscription_id
        user.stripe_customer_id = stripe_customer_id
        user.subscription_paused_until = paused_until
        user.last_pause_started_at = last_paused
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _login(client, email="pauser@test.com", password="testpassword123"):
    client.post("/api/auth/login", json={"email": email, "password": password})


# ─── Eligibility ─────────────────────────────────────────────


class TestPauseEligibility:

    def test_active_paid_user_is_eligible(self, app):
        from app.services.pause_service import is_pause_eligible
        uid = _make_user(app, tier="pro_plus", status="active")
        with app.app_context():
            user = db.session.get(User, uid)
            eligible, reason = is_pause_eligible(user)
            assert eligible is True
            assert reason is None

    def test_trial_user_not_eligible(self, app):
        from app.services.pause_service import is_pause_eligible
        uid = _make_user(app, tier="pro_plus", status="trialing")
        with app.app_context():
            user = db.session.get(User, uid)
            eligible, reason = is_pause_eligible(user)
            assert eligible is False
            assert reason == "trial"

    def test_free_tier_not_eligible(self, app):
        from app.services.pause_service import is_pause_eligible
        uid = _make_user(app, tier="free", status="active",
                         stripe_subscription_id=None)
        with app.app_context():
            user = db.session.get(User, uid)
            eligible, reason = is_pause_eligible(user)
            assert eligible is False
            # No subscription wins over free_tier in priority order.
            assert reason in ("no_subscription", "free_tier")

    def test_canceled_subscription_not_eligible(self, app):
        from app.services.pause_service import is_pause_eligible
        uid = _make_user(app, tier="pro_plus", status="canceled")
        with app.app_context():
            user = db.session.get(User, uid)
            eligible, reason = is_pause_eligible(user)
            assert eligible is False
            assert reason == "no_subscription"

    def test_recently_paused_not_eligible(self, app):
        from app.services.pause_service import is_pause_eligible
        three_months_ago = datetime.utcnow() - timedelta(days=90)
        uid = _make_user(app, last_paused=three_months_ago)
        with app.app_context():
            user = db.session.get(User, uid)
            eligible, reason = is_pause_eligible(user)
            assert eligible is False
            assert reason == "recently_paused"

    def test_paused_seven_months_ago_is_eligible(self, app):
        from app.services.pause_service import is_pause_eligible
        seven_months_ago = datetime.utcnow() - timedelta(days=210)
        uid = _make_user(app, last_paused=seven_months_ago)
        with app.app_context():
            user = db.session.get(User, uid)
            eligible, reason = is_pause_eligible(user)
            assert eligible is True

    def test_in_dunning_not_eligible(self, app):
        from app.services.pause_service import is_pause_eligible
        uid = _make_user(app, status="past_due")
        with app.app_context():
            user = db.session.get(User, uid)
            eligible, reason = is_pause_eligible(user)
            assert eligible is False
            assert reason == "in_dunning"

    def test_currently_paused_not_eligible(self, app):
        from app.services.pause_service import is_pause_eligible
        future = datetime.utcnow() + timedelta(days=30)
        uid = _make_user(app, paused_until=future)
        with app.app_context():
            user = db.session.get(User, uid)
            eligible, reason = is_pause_eligible(user)
            assert eligible is False
            assert reason == "already_paused"


# ─── Initiation ──────────────────────────────────────────────


class TestPauseInitiation:

    def test_30_day_pause_sets_resume_date(self, app):
        from app.services.pause_service import initiate_pause
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify") as modify, \
                 patch("app.services.stripe_service.init_stripe", return_value=True), \
                 patch("app.services.analytics_service.track_event"):
                result = initiate_pause(user, 30)

            assert result["success"] is True
            assert result["resume_date"] is not None
            user = db.session.get(User, uid)
            expected_end = (datetime.utcnow() + timedelta(days=30)).date()
            assert user.subscription_paused_until.date() == expected_end
            modify.assert_called_once()
            kwargs = modify.call_args.kwargs
            assert kwargs["pause_collection"]["behavior"] == "void"
            assert isinstance(kwargs["pause_collection"]["resumes_at"], int)

    def test_60_day_pause_sets_resume_date(self, app):
        from app.services.pause_service import initiate_pause
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify"), \
                 patch("app.services.stripe_service.init_stripe", return_value=True), \
                 patch("app.services.analytics_service.track_event"):
                result = initiate_pause(user, 60)

            assert result["success"] is True
            user = db.session.get(User, uid)
            expected_end = (datetime.utcnow() + timedelta(days=60)).date()
            assert user.subscription_paused_until.date() == expected_end

    def test_invalid_duration_rejected(self, app):
        from app.services.pause_service import initiate_pause
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify") as modify:
                result = initiate_pause(user, 45)

            assert result["success"] is False
            assert result["error"] == "invalid_duration"
            assert modify.call_count == 0
            assert SubscriptionEvent.query.filter_by(user_id=uid).count() == 0

    def test_successful_pause_writes_audit_row(self, app):
        from app.services.pause_service import initiate_pause
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify"), \
                 patch("app.services.stripe_service.init_stripe", return_value=True), \
                 patch("app.services.analytics_service.track_event"):
                initiate_pause(user, 30)

            event = SubscriptionEvent.query.filter_by(
                user_id=uid, event_type="paused"
            ).first()
            assert event is not None
            assert event.pause_duration_days == 30
            assert event.pause_started_at is not None
            assert event.pause_ends_at is not None

    def test_stripe_failure_no_audit_paused_row(self, app):
        """Stripe API failure must NOT mark the user as paused, but
        SHOULD write a pause_failed audit row."""
        from app.services.pause_service import initiate_pause
        import stripe as stripe_sdk
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify",
                       side_effect=stripe_sdk.error.APIConnectionError("boom")), \
                 patch("app.services.stripe_service.init_stripe", return_value=True):
                result = initiate_pause(user, 30)

            assert result["success"] is False
            assert result["error"] == "stripe_error"
            user = db.session.get(User, uid)
            assert user.subscription_paused_until is None
            assert user.last_pause_started_at is None
            paused_rows = SubscriptionEvent.query.filter_by(
                user_id=uid, event_type="paused"
            ).count()
            failed_rows = SubscriptionEvent.query.filter_by(
                user_id=uid, event_type="pause_failed"
            ).count()
            assert paused_rows == 0
            assert failed_rows == 1

    def test_pause_sets_last_pause_started_at(self, app):
        from app.services.pause_service import initiate_pause
        uid = _make_user(app)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify"), \
                 patch("app.services.stripe_service.init_stripe", return_value=True), \
                 patch("app.services.analytics_service.track_event"):
                initiate_pause(user, 30)
            user = db.session.get(User, uid)
            assert user.last_pause_started_at is not None

    def test_ineligible_user_cannot_pause_via_service(self, app):
        from app.services.pause_service import initiate_pause
        uid = _make_user(app, status="trialing")
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify") as modify:
                result = initiate_pause(user, 30)
            assert result["success"] is False
            assert result["error"] == "trial"
            assert modify.call_count == 0


# ─── Manual resume ───────────────────────────────────────────


class TestManualResume:

    def test_resume_clears_paused_until(self, app):
        from app.services.pause_service import manually_resume_pause
        future = datetime.utcnow() + timedelta(days=30)
        uid = _make_user(app, paused_until=future)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify"), \
                 patch("app.services.stripe_service.init_stripe", return_value=True), \
                 patch("app.services.analytics_service.track_event"):
                result = manually_resume_pause(user)
            assert result["success"] is True
            user = db.session.get(User, uid)
            assert user.subscription_paused_until is None

    def test_resume_writes_audit_row(self, app):
        from app.services.pause_service import manually_resume_pause
        future = datetime.utcnow() + timedelta(days=30)
        uid = _make_user(app, paused_until=future)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify"), \
                 patch("app.services.stripe_service.init_stripe", return_value=True), \
                 patch("app.services.analytics_service.track_event"):
                manually_resume_pause(user)
            event = SubscriptionEvent.query.filter_by(
                user_id=uid, event_type="resumed_manual"
            ).first()
            assert event is not None

    def test_resume_on_unpaused_user_returns_error(self, app):
        from app.services.pause_service import manually_resume_pause
        uid = _make_user(app, paused_until=None)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify") as modify:
                result = manually_resume_pause(user)
            assert result["success"] is False
            assert result["error"] == "not_paused"
            assert modify.call_count == 0

    def test_resume_stripe_failure(self, app):
        from app.services.pause_service import manually_resume_pause
        import stripe as stripe_sdk
        future = datetime.utcnow() + timedelta(days=30)
        uid = _make_user(app, paused_until=future)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("stripe.Subscription.modify",
                       side_effect=stripe_sdk.error.APIConnectionError("boom")), \
                 patch("app.services.stripe_service.init_stripe", return_value=True):
                result = manually_resume_pause(user)
            assert result["success"] is False
            assert result["error"] == "stripe_error"
            user = db.session.get(User, uid)
            # Paused state preserved on Stripe failure.
            assert user.subscription_paused_until is not None


# ─── Webhook handling ────────────────────────────────────────


class TestWebhookAutoResume:

    def test_auto_resume_clears_paused_until(self, app):
        from app.services.pause_service import handle_scheduled_resume_webhook
        future = datetime.utcnow() + timedelta(days=10)
        uid = _make_user(app, paused_until=future)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("app.services.analytics_service.track_event"):
                updated = handle_scheduled_resume_webhook(user, "evt_test_001")
            assert updated is True
            user = db.session.get(User, uid)
            assert user.subscription_paused_until is None
            event = SubscriptionEvent.query.filter_by(
                user_id=uid, event_type="resumed_scheduled"
            ).first()
            assert event is not None
            assert event.stripe_event_id == "evt_test_001"

    def test_duplicate_webhook_is_idempotent(self, app):
        """A second delivery with the same stripe_event_id must NOT
        write a second SubscriptionEvent or re-mutate the user."""
        from app.services.pause_service import handle_scheduled_resume_webhook
        future = datetime.utcnow() + timedelta(days=10)
        uid = _make_user(app, paused_until=future)
        with app.app_context():
            user = db.session.get(User, uid)
            with patch("app.services.analytics_service.track_event"):
                first = handle_scheduled_resume_webhook(user, "evt_test_dup")
                # Re-fetch user (post-first-call state).
                user = db.session.get(User, uid)
                second = handle_scheduled_resume_webhook(user, "evt_test_dup")

            assert first is True
            assert second is False
            rows = SubscriptionEvent.query.filter_by(
                user_id=uid, stripe_event_id="evt_test_dup",
            ).count()
            assert rows == 1

    def test_webhook_for_already_resumed_user_records_audit(self, app):
        """User already manually resumed before webhook arrived. We
        still record the audit row (so the trail is complete) but
        don't re-mutate state."""
        from app.services.pause_service import handle_scheduled_resume_webhook
        uid = _make_user(app, paused_until=None)
        with app.app_context():
            user = db.session.get(User, uid)
            updated = handle_scheduled_resume_webhook(user, "evt_test_002")
            assert updated is False
            event = SubscriptionEvent.query.filter_by(
                user_id=uid, event_type="resumed_scheduled"
            ).first()
            assert event is not None

    def test_dispatch_detects_pause_collection_clearing(self, app):
        """The webhook dispatcher reads previous_attributes and fires
        the resume handler when pause_collection clears."""
        from app.routes import billing_routes
        uid = _make_user(app, paused_until=datetime.utcnow() + timedelta(days=10))
        with app.app_context():
            with patch(
                "app.services.pause_service.handle_scheduled_resume_webhook"
            ) as resume_handler, \
                 patch("app.services.analytics_service.track_event"):
                billing_routes._handle_subscription_updated(
                    {
                        "id": "sub_test_abc",
                        "customer": "cus_test_xyz",
                        "status": "active",
                        "pause_collection": None,
                        "items": {"data": []},
                    },
                    previous_attributes={"pause_collection": {
                        "behavior": "void",
                        "resumes_at": 1234567890,
                    }},
                    stripe_event_id="evt_dispatch_001",
                )
            resume_handler.assert_called_once()
            args, _ = resume_handler.call_args
            assert args[1] == "evt_dispatch_001"

    def test_dispatch_ignores_non_pause_updates(self, app):
        """A subscription update that has nothing to do with pausing
        must NOT call the resume handler."""
        from app.routes import billing_routes
        _make_user(app)
        with app.app_context():
            with patch(
                "app.services.pause_service.handle_scheduled_resume_webhook"
            ) as resume_handler:
                billing_routes._handle_subscription_updated(
                    {
                        "id": "sub_test_abc",
                        "customer": "cus_test_xyz",
                        "status": "active",
                        "pause_collection": None,
                        "items": {"data": []},
                    },
                    previous_attributes={"status": "trialing"},
                    stripe_event_id="evt_dispatch_002",
                )
            assert resume_handler.call_count == 0

    def test_dispatch_handles_unknown_user_gracefully(self, app):
        """customer not in DB — handler returns early without raising."""
        from app.routes import billing_routes
        with app.app_context():
            # No user with cus_unknown — should silently no-op.
            billing_routes._handle_subscription_updated(
                {
                    "id": "sub_unknown",
                    "customer": "cus_unknown",
                    "status": "active",
                    "items": {"data": []},
                },
                previous_attributes={},
                stripe_event_id="evt_unknown",
            )
            # If we got here without raising, the test passes.


# ─── Routes ──────────────────────────────────────────────────


class TestPauseRoutes:

    def test_get_pause_renders_form_for_eligible_user(self, app, client):
        _make_user(app)
        _login(client)
        resp = client.get("/crisis/pause")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Sometimes life needs space" in body
        assert "Pause my subscription" in body
        assert 'name="duration_days"' in body
        # Mailto escape hatch must remain.
        assert "mailto:hello@getclaro.co.uk" in body

    def test_get_pause_renders_ineligible_for_trial_user(self, app, client):
        _make_user(app, status="trialing")
        _login(client)
        resp = client.get("/crisis/pause")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        # Should NOT show the form CTA.
        assert "Pause my subscription" not in body
        # Should show the trial-specific copy.
        assert "trial" in body.lower()

    def test_get_pause_renders_ineligible_for_dunning_user(self, app, client):
        _make_user(app, status="past_due")
        _login(client)
        resp = client.get("/crisis/pause")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "payment issue" in body.lower()
        assert "Pause my subscription" not in body

    def test_get_pause_confirm_renders_with_30_days(self, app, client):
        _make_user(app)
        _login(client)
        resp = client.get("/crisis/pause/confirm?duration_days=30")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Confirm pause" in body
        assert "30 days" in body
        assert 'name="duration_days" value="30"' in body

    def test_get_pause_confirm_with_invalid_duration_redirects(self, app, client):
        _make_user(app)
        _login(client)
        resp = client.get("/crisis/pause/confirm?duration_days=45",
                          follow_redirects=False)
        assert resp.status_code == 302
        assert "/crisis/pause" in resp.headers.get("Location", "")

    def test_post_pause_confirm_initiates_pause(self, app, client):
        uid = _make_user(app)
        _login(client)
        with patch("stripe.Subscription.modify"), \
             patch("app.services.stripe_service.init_stripe", return_value=True), \
             patch("app.services.analytics_service.track_event"):
            resp = client.post("/crisis/pause/confirm", data={
                "duration_days": "30",
            })
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "You're paused" in body
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.subscription_paused_until is not None

    def test_post_pause_confirm_handles_stripe_failure(self, app, client):
        import stripe as stripe_sdk
        uid = _make_user(app)
        _login(client)
        with patch("stripe.Subscription.modify",
                   side_effect=stripe_sdk.error.APIConnectionError("boom")), \
             patch("app.services.stripe_service.init_stripe", return_value=True), \
             patch("app.services.analytics_service.track_event"):
            resp = client.post(
                "/crisis/pause/confirm",
                data={"duration_days": "30"},
                follow_redirects=False,
            )
        assert resp.status_code == 302
        assert "/crisis/pause" in resp.headers.get("Location", "")
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.subscription_paused_until is None

    def test_settings_resume_button_clears_pause(self, app, client):
        future = datetime.utcnow() + timedelta(days=20)
        uid = _make_user(app, paused_until=future)
        _login(client)
        with patch("stripe.Subscription.modify"), \
             patch("app.services.stripe_service.init_stripe", return_value=True), \
             patch("app.services.analytics_service.track_event"):
            resp = client.post("/settings/subscription/resume",
                               follow_redirects=False)
        assert resp.status_code == 302
        assert "/settings" in resp.headers.get("Location", "")
        with app.app_context():
            user = db.session.get(User, uid)
            assert user.subscription_paused_until is None

    def test_pause_routes_require_login(self, app, client):
        resp = client.get("/crisis/pause/confirm", follow_redirects=False)
        assert resp.status_code in (302, 401)
        resp = client.post("/crisis/pause/confirm", data={"duration_days": "30"},
                           follow_redirects=False)
        assert resp.status_code in (302, 401)
        resp = client.post("/settings/subscription/resume",
                           follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_settings_renders_pause_section_when_paused(self, app, client):
        future = datetime.utcnow() + timedelta(days=20)
        _make_user(app, paused_until=future)
        _login(client)
        resp = client.get("/settings")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Subscription paused" in body
        assert "Resume billing now" in body

    def test_settings_omits_pause_section_when_not_paused(self, app, client):
        _make_user(app, paused_until=None)
        _login(client)
        resp = client.get("/settings")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Resume billing now" not in body
