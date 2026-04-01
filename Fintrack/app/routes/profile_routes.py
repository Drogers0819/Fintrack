from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.goal import Goal
from app.services.allocator_service import generate_waterfall_summary

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.route("/factfind", methods=["POST"])
@login_required
def submit_factfind():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        monthly_income = round(float(data.get("monthly_income", 0)), 2)
    except (ValueError, TypeError):
        return jsonify({"error": "Monthly income must be a valid number"}), 400

    if monthly_income <= 0:
        return jsonify({"error": "Monthly income must be greater than zero"}), 400

    try:
        rent_amount = round(float(data.get("rent_amount", 0)), 2)
    except (ValueError, TypeError):
        return jsonify({"error": "Rent amount must be a valid number"}), 400

    if rent_amount < 0:
        return jsonify({"error": "Rent amount cannot be negative"}), 400

    try:
        bills_amount = round(float(data.get("bills_amount", 0)), 2)
    except (ValueError, TypeError):
        return jsonify({"error": "Bills amount must be a valid number"}), 400

    if bills_amount < 0:
        return jsonify({"error": "Bills amount cannot be negative"}), 400

    income_day = data.get("income_day")
    if income_day is not None:
        if not isinstance(income_day, int) or income_day < 1 or income_day > 31:
            return jsonify({"error": "Income day must be between 1 and 31"}), 400

    current_user.monthly_income = monthly_income
    current_user.rent_amount = rent_amount
    current_user.bills_amount = bills_amount
    current_user.income_day = income_day
    current_user.factfind_completed = True

    db.session.commit()

    return jsonify({
        "message": "Financial profile saved successfully",
        "profile": current_user.profile_dict()
    }), 200


@profile_bp.route("/factfind", methods=["GET"])
@login_required
def get_factfind():
    return jsonify({
        "profile": current_user.profile_dict()
    }), 200


@profile_bp.route("/waterfall", methods=["GET"])
@login_required
def get_waterfall():
    if not current_user.factfind_completed:
        return jsonify({
            "error": "Please complete the fact-find first to see your budget allocation.",
            "factfind_completed": False
        }), 400

    goals = Goal.query.filter_by(
        user_id=current_user.id,
        status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    goals_data = []
    for g in goals:
        goals_data.append({
            "id": g.id,
            "name": g.name,
            "type": g.type,
            "target_amount": float(g.target_amount) if g.target_amount else None,
            "current_amount": float(g.current_amount) if g.current_amount else 0,
            "monthly_allocation": float(g.monthly_allocation) if g.monthly_allocation else 0,
            "priority_rank": g.priority_rank
        })

    user_profile = {
        "monthly_income": float(current_user.monthly_income),
        "fixed_commitments": current_user.fixed_commitments
    }

    result = generate_waterfall_summary(user_profile, goals_data)

    return jsonify(result), 200