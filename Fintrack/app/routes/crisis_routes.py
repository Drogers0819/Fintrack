"""
Crisis flow — Block 2 Task 2.4.

A single entry point at /crisis that branches three ways:
  • /crisis/income — user has lost income
  • /crisis/cost — user has an unexpected cost
  • /crisis/pause — user wants to step back

This task ships the routing + form capture + minimal placeholder
responses. Real responses arrive in:
  • Task 2.5 (survival mode) — replaces the income placeholder
  • Task 2.6 (hardship pause) — replaces the pause placeholder
  • Task 2.7 (signposting library) — replaces the inline resource lists

FCA boundary: this blueprint never gives financial advice. It records
events, lets the user update their plan inside Claro, and signposts
free regulated UK resources. Nothing here recommends a financial
product or tells the user what to do with money outside the app.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.services.analytics_service import track_event
from app.services.crisis_service import (
    calculate_cost_absorption,
    record_lost_income,
    record_pause_request,
    record_unexpected_cost,
)
from app.services.signposting_library import get_resources_for_categories
from app.utils.validators import sanitize_string, validate_amount

logger = logging.getLogger(__name__)

crisis_bp = Blueprint("crisis", __name__, url_prefix="/crisis")


_INCOME_CHANGE_TYPES = {"job_loss", "reduced_hours", "other"}
_OCCURRED_MAX_BACKFILL_DAYS = 30


def _parse_occurred_on(raw: str | None) -> date | None:
    """Accept yyyy-mm-dd, default to today, clamp to 30 days back. Future
    dates are rejected up the stack — return None and let the caller
    flash an error."""
    if not raw:
        return date.today()
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    if parsed > today:
        return None
    earliest = today - timedelta(days=_OCCURRED_MAX_BACKFILL_DAYS)
    if parsed < earliest:
        parsed = earliest
    return parsed


# ─── Landing page ────────────────────────────────────────────


@crisis_bp.route("/", methods=["GET"])
@login_required
def index():
    track_event(current_user.id, "crisis_landing_viewed", {
        "source": request.args.get("source") or "direct",
    })
    return render_template("crisis/index.html")


# ─── /crisis/income ──────────────────────────────────────────


@crisis_bp.route("/income", methods=["GET", "POST"])
@login_required
def income():
    if request.method == "POST":
        change_type = request.form.get("change_type", "")
        if change_type not in _INCOME_CHANGE_TYPES:
            flash("Pick one of the options so we know what's changed.", "error")
            return redirect(url_for("crisis.income"))

        income_unknown = request.form.get("income_unknown") == "1"
        new_income_value = None

        if not income_unknown:
            raw_income = request.form.get("new_monthly_income", "").strip()
            if not raw_income:
                flash("Tell us your new monthly income, or tick \"I don't know yet\".", "error")
                return redirect(url_for("crisis.income"))
            try:
                new_income_value = validate_amount(
                    raw_income, "Monthly income", min_val=0, max_val=1_000_000,
                )
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("crisis.income"))

        occurred_on = _parse_occurred_on(request.form.get("occurred_on"))
        if occurred_on is None:
            flash("Pick a date today or up to 30 days back.", "error")
            return redirect(url_for("crisis.income"))

        event = record_lost_income(
            current_user,
            change_type=change_type,
            new_monthly_income=new_income_value,
            occurred_on=occurred_on,
            income_unknown=income_unknown,
        )

        survival_just_activated = bool(
            getattr(event, "survival_mode_just_activated", False)
        )

        track_event(current_user.id, "crisis_income_submitted", {
            "change_type": change_type,
            "income_unknown": income_unknown,
            "survival_mode_just_activated": survival_just_activated,
        })

        return render_template(
            "crisis/income_response.html",
            survival_mode_just_activated=survival_just_activated,
            resources=get_resources_for_categories(
                ["debt", "general_money", "benefits"]
            ),
        )

    return render_template(
        "crisis/income.html",
        today_iso=date.today().isoformat(),
        max_backfill_iso=(date.today() - timedelta(days=_OCCURRED_MAX_BACKFILL_DAYS)).isoformat(),
    )


# ─── /crisis/cost ────────────────────────────────────────────


@crisis_bp.route("/cost", methods=["GET", "POST"])
@login_required
def cost():
    if request.method == "POST":
        description = sanitize_string(
            request.form.get("description", ""), max_length=200,
        )
        if not description:
            flash("Give us a quick description of what the cost is for.", "error")
            return redirect(url_for("crisis.cost"))

        try:
            amount = validate_amount(
                request.form.get("amount", ""), "Cost", min_val=0.01, max_val=1_000_000,
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("crisis.cost"))

        already_paid = request.form.get("already_paid") == "yes"

        occurred_on = _parse_occurred_on(request.form.get("occurred_on"))
        if occurred_on is None:
            flash("Pick a date today or up to 30 days back.", "error")
            return redirect(url_for("crisis.cost"))

        event = record_unexpected_cost(
            current_user,
            description=description,
            amount=amount,
            already_paid=already_paid,
            occurred_on=occurred_on,
        )

        absorption = calculate_cost_absorption(current_user, amount)

        track_event(current_user.id, "crisis_cost_submitted", {
            "amount": float(amount),
            "already_paid": already_paid,
            "absorbable": bool(absorption.get("affordable")),
            "impact": absorption.get("impact"),
        })

        return render_template(
            "crisis/cost_response.html",
            description=description,
            amount=float(amount),
            already_paid=already_paid,
            absorption=absorption,
            event_id=event.id,
            resources=get_resources_for_categories(["debt", "general_money"]),
        )

    return render_template(
        "crisis/cost.html",
        today_iso=date.today().isoformat(),
        max_backfill_iso=(date.today() - timedelta(days=_OCCURRED_MAX_BACKFILL_DAYS)).isoformat(),
    )


# ─── /crisis/pause ───────────────────────────────────────────


@crisis_bp.route("/pause", methods=["GET", "POST"])
@login_required
def pause():
    """GET renders the self-service pause flow when eligible, an
    explanatory ineligible page otherwise. POST is the fire-and-forget
    tracker fired by the email-support mailto link — kept from Task
    2.4 so support still gets a row when a user asks for a longer
    pause via email."""
    from app.services.pause_service import (
        is_pause_eligible,
        next_pause_available_date,
    )

    if request.method == "POST":
        record_pause_request(current_user)
        track_event(current_user.id, "crisis_pause_requested", {})
        return ("", 204)

    eligible, reason = is_pause_eligible(current_user)
    track_event(current_user.id, "crisis_pause_viewed", {
        "eligible": eligible,
        "reason": reason,
    })

    resources = get_resources_for_categories(["mental_health", "debt"])

    if not eligible:
        next_available = next_pause_available_date(current_user)
        return render_template(
            "crisis/pause_ineligible.html",
            reason=reason,
            next_available=next_available,
            resources=resources,
        )

    return render_template(
        "crisis/pause.html",
        resources=resources,
        allowed_durations=(30, 60),
    )


@crisis_bp.route("/pause/confirm", methods=["GET", "POST"])
@login_required
def pause_confirm():
    """GET shows the confirmation interstitial; POST executes the
    pause via the service. Both branches re-check eligibility so a
    user can't pause via a stale tab after their state changed."""
    from app.services.pause_service import (
        ALLOWED_DURATIONS_DAYS,
        calculate_resume_date,
        initiate_pause,
        is_pause_eligible,
    )
    from datetime import datetime as _dt

    raw_duration = (
        request.form.get("duration_days")
        if request.method == "POST"
        else request.args.get("duration_days")
    )
    try:
        duration_days = int(raw_duration or 0)
    except (TypeError, ValueError):
        duration_days = 0

    if duration_days not in ALLOWED_DURATIONS_DAYS:
        flash("Pick how long you'd like to pause.", "error")
        return redirect(url_for("crisis.pause"))

    eligible, reason = is_pause_eligible(current_user)
    if not eligible:
        return redirect(url_for("crisis.pause"))

    if request.method == "POST":
        result = initiate_pause(current_user, duration_days)
        if not result["success"]:
            track_event(current_user.id, "subscription_pause_failed", {
                "duration_days": duration_days,
                "error": result.get("error"),
            })
            flash(
                "We couldn't pause your subscription right now. Try again in a few minutes.",
                "error",
            )
            return redirect(url_for("crisis.pause"))
        return render_template(
            "crisis/pause_success.html",
            duration_days=duration_days,
            resume_date=result["resume_date"],
        )

    # GET — render the confirmation page.
    resume_date = calculate_resume_date(_dt.utcnow(), duration_days)
    return render_template(
        "crisis/pause_confirm.html",
        duration_days=duration_days,
        resume_date=resume_date,
    )


# ─── Click tracker for the contextual entry points ───────────


@crisis_bp.route("/api/link-clicked", methods=["POST"])
@login_required
def link_clicked():
    """Fire-and-forget click tracker for the overview-page contextual
    link and the popover entry. Mirrors /api/companion/chip-clicked."""
    data = request.get_json(silent=True) or {}
    location = sanitize_string(data.get("location") or "unknown", max_length=40)
    track_event(current_user.id, "crisis_link_clicked", {
        "location": location,
    })
    return ("", 204)
