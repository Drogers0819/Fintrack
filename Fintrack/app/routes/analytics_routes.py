from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction
from app.models.category import Category
from sqlalchemy import func, extract
from datetime import date, datetime, timedelta

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/spending-by-category", methods=["GET"])
@login_required
def spending_by_category():
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    if not month or not year:
        today = date.today()
        month = today.month
        year = today.year

    results = db.session.query(
        Category.name,
        Category.icon,
        Category.colour,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count")
    ).join(
        Category, Transaction.category_id == Category.id
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == month,
        extract("year", Transaction.date) == year
    ).group_by(
        Category.id, Category.name, Category.icon, Category.colour
    ).order_by(
        func.sum(Transaction.amount).desc()
    ).all()

    total_expenses = sum(float(r.total) for r in results)

    categories = []
    for r in results:
        amount = float(r.total)
        categories.append({
            "name": r.name,
            "icon": r.icon,
            "colour": r.colour,
            "total": round(amount, 2),
            "count": r.count,
            "percentage": round((amount / total_expenses * 100), 1) if total_expenses > 0 else 0
        })

    return jsonify({
        "month": month,
        "year": year,
        "total_expenses": round(total_expenses, 2),
        "categories": categories,
        "category_count": len(categories)
    }), 200


@analytics_bp.route("/monthly-summary", methods=["GET"])
@login_required
def monthly_summary():
    months_back = request.args.get("months", 6, type=int)
    months_back = min(months_back, 24)

    today = date.today()

    summaries = []

    for i in range(months_back):
        if today.month - i > 0:
            m = today.month - i
            y = today.year
        else:
            m = today.month - i + 12
            y = today.year - 1

        income = db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "income",
            extract("month", Transaction.date) == m,
            extract("year", Transaction.date) == y
        ).scalar()

        expenses = db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense",
            extract("month", Transaction.date) == m,
            extract("year", Transaction.date) == y
        ).scalar()

        transaction_count = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            extract("month", Transaction.date) == m,
            extract("year", Transaction.date) == y
        ).count()

        income_val = float(income)
        expenses_val = float(expenses)

        summaries.append({
            "month": m,
            "year": y,
            "month_name": date(y, m, 1).strftime("%B"),
            "income": round(income_val, 2),
            "expenses": round(expenses_val, 2),
            "balance": round(income_val - expenses_val, 2),
            "transaction_count": transaction_count
        })

    summaries.reverse()

    return jsonify({
        "summaries": summaries,
        "months_included": len(summaries)
    }), 200


@analytics_bp.route("/trends", methods=["GET"])
@login_required
def spending_trends():
    today = date.today()
    current_month = today.month
    current_year = today.year

    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year

    current_expenses = db.session.query(
        Category.name,
        Category.icon,
        func.sum(Transaction.amount).label("total")
    ).join(
        Category, Transaction.category_id == Category.id
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == current_month,
        extract("year", Transaction.date) == current_year
    ).group_by(
        Category.id, Category.name, Category.icon
    ).all()

    prev_expenses = db.session.query(
        Category.name,
        func.sum(Transaction.amount).label("total")
    ).join(
        Category, Transaction.category_id == Category.id
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == prev_month,
        extract("year", Transaction.date) == prev_year
    ).group_by(
        Category.id, Category.name
    ).all()

    prev_dict = {r.name: float(r.total) for r in prev_expenses}

    trends = []
    for r in current_expenses:
        current_total = float(r.total)
        prev_total = prev_dict.get(r.name, 0)

        if prev_total > 0:
            change_amount = current_total - prev_total
            change_percent = round(((current_total - prev_total) / prev_total) * 100, 1)
        else:
            change_amount = current_total
            change_percent = 100.0

        trends.append({
            "category": r.name,
            "icon": r.icon,
            "current_month": round(current_total, 2),
            "previous_month": round(prev_total, 2),
            "change_amount": round(change_amount, 2),
            "change_percent": change_percent,
            "direction": "up" if change_amount > 0 else "down" if change_amount < 0 else "flat"
        })

    trends.sort(key=lambda t: abs(t["change_amount"]), reverse=True)

    biggest_change = trends[0] if trends else None

    return jsonify({
        "current_month": current_month,
        "current_year": current_year,
        "previous_month": prev_month,
        "previous_year": prev_year,
        "trends": trends,
        "biggest_change": biggest_change
    }), 200