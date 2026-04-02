from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models.transaction import Transaction
from app.services.recurring_service import detect_recurring_transactions, identify_potential_savings

recurring_bp = Blueprint("recurring", __name__, url_prefix="/api/recurring")


@recurring_bp.route("", methods=["GET"])
@login_required
def get_recurring():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.asc()).all()

    txn_list = []
    for t in transactions:
        txn_list.append({
            "id": t.id,
            "amount": float(t.amount),
            "description": t.description,
            "merchant": t.merchant or t.description,
            "category": t.category_rel.name if t.category_rel else "Other",
            "category_id": t.category_id,
            "type": t.type,
            "date": t.date
        })

    result = detect_recurring_transactions(txn_list)

    return jsonify(result), 200


@recurring_bp.route("/savings", methods=["GET"])
@login_required
def get_savings_opportunities():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.asc()).all()

    txn_list = []
    for t in transactions:
        txn_list.append({
            "id": t.id,
            "amount": float(t.amount),
            "description": t.description,
            "merchant": t.merchant or t.description,
            "category": t.category_rel.name if t.category_rel else "Other",
            "category_id": t.category_id,
            "type": t.type,
            "date": t.date
        })

    recurring_result = detect_recurring_transactions(txn_list)
    savings = identify_potential_savings(recurring_result["recurring"])

    return jsonify(savings), 200