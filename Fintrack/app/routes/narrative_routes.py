from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction
from app.models.goal import Goal
from app.models.budget import Budget
from app.services.narrative_service import generate_monthly_narrative, generate_narrative_email_data
from app.services.prediction_service import predict_monthly_spending
from app.services.budget_service import calculate_budget_status as calc_budget_status
from app.services.anomaly_service import detect_anomalies
from app.services.recurring_service import detect_recurring_transactions
from sqlalchemy import func, extract
from datetime import date
import calendar

narrative_bp = Blueprint("narrative", __name__, url_prefix="/api/narrative")


def _build_narrative_data(target_month=None, target_year=None):
    """Gathers data for narrative generation."""
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.asc()).all()

    txn_list = [{
        "amount": float(t.amount),
        "description": t.description,
        "merchant": t.merchant or t.description,
        "category": t.category_rel.name if t.category_rel else "Other",
        "type": t.type,
        "date": t.date
    } for t in transactions]

    goals = Goal.query.filter_by(
        user_id=current_user.id,
        status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    goals_list = [g.to_dict() for g in goals]

    predictions = predict_monthly_spending(txn_list)
    anomalies = detect_anomalies(txn_list)
    recurring = detect_recurring_transactions(txn_list)

    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    budget_list = [b.to_dict() for b in budgets]
    budget_status = calc_budget_status(budget_list, txn_list) if budget_list else {"budgets": []}

    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    money_left = None
    if current_user.factfind_completed and current_user.monthly_income:
        current_month_expenses = db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense",
            extract("month", Transaction.date) == today.month,
            extract("year", Transaction.date) == today.year
        ).scalar()

        total_goal_allocation = sum(
            float(g.monthly_allocation) if g.monthly_allocation else 0
            for g in goals
        )
        disposable = current_user.monthly_surplus - total_goal_allocation
        money_left = round(disposable - float(current_month_expenses), 2)

    return {
        "user_name": current_user.name,
        "transactions": txn_list,
        "goals": goals_list,
        "budget_statuses": budget_status.get("budgets", []),
        "predictions": predictions,
        "anomalies": anomalies,
        "recurring": recurring,
        "money_left": money_left,
        "days_remaining": days_in_month - today.day,
        "member_since": current_user.created_at.strftime("%B %Y") if current_user.created_at else ""
    }


@narrative_bp.route("/monthly", methods=["GET"])
@login_required
def monthly_narrative():
    target_month = request.args.get("month", type=int)
    target_year = request.args.get("year", type=int)

    data = _build_narrative_data(target_month, target_year)
    result = generate_monthly_narrative(data, target_month, target_year)

    return jsonify(result), 200


@narrative_bp.route("/email-preview", methods=["GET"])
@login_required
def email_preview():
    target_month = request.args.get("month", type=int)
    target_year = request.args.get("year", type=int)

    data = _build_narrative_data(target_month, target_year)
    result = generate_narrative_email_data(data, target_month, target_year)

    return jsonify(result), 200