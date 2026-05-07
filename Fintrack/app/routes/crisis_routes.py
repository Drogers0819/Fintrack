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
    """GET renders the page; POST records the pause-requested event so
    support has a row when the user emails. The mailto link in the
    template is the actual handoff — there's no self-service pause yet
    (Task 2.6)."""
    if request.method == "POST":
        record_pause_request(current_user)
        track_event(current_user.id, "crisis_pause_requested", {})
        return ("", 204)

    track_event(current_user.id, "crisis_pause_viewed", {})
    return render_template("crisis/pause.html")


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
