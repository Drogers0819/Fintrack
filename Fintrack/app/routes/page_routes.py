from app.services.allocator_service import generate_waterfall_summary
from app.models.goal import Goal
from app.services.csv_parser import extract_transactions_from_csv, CSVParseError
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models.user import User
from app.models.transaction import Transaction
from sqlalchemy import func
from datetime import date, datetime
from app.models.category import Category


page_bp = Blueprint("pages", __name__)


@page_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return redirect(url_for("pages.login"))


@page_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required", "error")
            return redirect(url_for("pages.register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return redirect(url_for("pages.register"))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists", "error")
            return redirect(url_for("pages.register"))

        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Account created successfully", "success")
        return redirect(url_for("pages.dashboard"))

    return render_template("register.html")


@page_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password", "error")
            return redirect(url_for("pages.login"))

        login_user(user)
        return redirect(url_for("pages.dashboard"))

    return render_template("login.html")


@page_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "success")
    return redirect(url_for("pages.login"))


@page_bp.route("/dashboard")
@login_required
def dashboard():
    if not current_user.factfind_completed:
        flash("Complete your financial profile to get started", "success")
        return redirect(url_for("pages.factfind"))

    income = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="income").scalar()

    expenses = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="expense").scalar()

    balance = float(income) - float(expenses)
    transaction_count = Transaction.query.filter_by(user_id=current_user.id).count()

    recent = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).limit(5).all()

    hour = datetime.now().hour
    if hour < 12:
        greeting = "morning"
    elif hour < 18:
        greeting = "afternoon"
    else:
        greeting = "evening"

    return render_template("dashboard.html",
        summary={
            "total_income": float(income),
            "total_expenses": float(expenses),
            "balance": balance,
            "transaction_count": transaction_count
        },
        recent_transactions=[t.to_dict() for t in recent],
        greeting=greeting
    )


@page_bp.route("/transactions")
@login_required
def transactions():
    all_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).all()

    return render_template("transactions.html",
        transactions=[t.to_dict() for t in all_transactions]
    )


@page_bp.route("/add-transaction", methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == "POST":
        try:
            amount = round(float(request.form.get("amount", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid amount", "error")
            return redirect(url_for("pages.add_transaction"))

        if amount <= 0:
            flash("Amount must be greater than zero", "error")
            return redirect(url_for("pages.add_transaction"))

        description = request.form.get("description", "").strip()
        if not description:
            flash("Description is required", "error")
            return redirect(url_for("pages.add_transaction"))

        transaction_type = request.form.get("type", "expense")
        category_id = request.form.get("category_id", type=int)
        merchant = request.form.get("merchant", "").strip() or None

        if not category_id:
            other = Category.query.filter_by(name="Other").first()
            category_id = other.id if other else 1

        try:
            transaction_date = date.fromisoformat(request.form.get("date", ""))
        except (ValueError, TypeError):
            flash("Invalid date", "error")
            return redirect(url_for("pages.add_transaction"))

        transaction = Transaction(
            user_id=current_user.id,
            amount=amount,
            description=description,
            category_id=category_id,
            type=transaction_type,
            date=transaction_date,
            merchant=merchant
        )

        db.session.add(transaction)
        db.session.commit()

        flash("Transaction recorded successfully", "success")
        return redirect(url_for("pages.transactions"))

    categories = Category.query.order_by(Category.name).all()
    return render_template("add_transaction.html", categories=categories)


@page_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_statement():
    result = None

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file provided", "error")
            return redirect(url_for("pages.upload_statement"))

        file = request.files["file"]

        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("pages.upload_statement"))

        if not file.filename.lower().endswith(".csv"):
            flash("File must be a CSV", "error")
            return redirect(url_for("pages.upload_statement"))

        file_content = file.read()

        if len(file_content) == 0:
            flash("File is empty", "error")
            return redirect(url_for("pages.upload_statement"))

        if len(file_content) > 5 * 1024 * 1024:
            flash("File too large. Maximum size is 5MB", "error")
            return redirect(url_for("pages.upload_statement"))

        try:
            parse_result = extract_transactions_from_csv(file_content)
        except CSVParseError as e:
            flash(str(e), "error")
            return redirect(url_for("pages.upload_statement"))

        if not parse_result["transactions"]:
            flash("No valid transactions found in file", "error")
            return redirect(url_for("pages.upload_statement"))

        other_category = Category.query.filter_by(name="Other").first()
        default_category_id = other_category.id if other_category else 1

        created_count = 0
        skipped_count = 0

        for t in parse_result["transactions"]:
            existing = Transaction.query.filter_by(
                user_id=current_user.id,
                amount=t["amount"],
                description=t["description"],
                date=t["date"],
                type=t["type"]
            ).first()

            if existing:
                skipped_count += 1
                continue

            transaction = Transaction(
                user_id=current_user.id,
                amount=t["amount"],
                description=t["description"],
                category_id=default_category_id,
                type=t["type"],
                date=t["date"],
                merchant=t.get("merchant")
            )

            db.session.add(transaction)
            created_count += 1

        db.session.commit()

        result = {
            "bank_detected": parse_result["bank_detected"],
            "created": created_count,
            "skipped": skipped_count,
            "errors": parse_result["errors"],
            "error_count": parse_result["error_count"]
        }

        flash(f"Import complete. {created_count} transactions imported.", "success")

    return render_template("upload.html", result=result)


@page_bp.route("/factfind", methods=["GET", "POST"])
@login_required
def factfind():
    if request.method == "POST":
        try:
            monthly_income = round(float(request.form.get("monthly_income", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid income amount", "error")
            return redirect(url_for("pages.factfind"))

        if monthly_income <= 0:
            flash("Monthly income must be greater than zero", "error")
            return redirect(url_for("pages.factfind"))

        try:
            rent_amount = round(float(request.form.get("rent_amount", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid rent amount", "error")
            return redirect(url_for("pages.factfind"))

        try:
            bills_amount = round(float(request.form.get("bills_amount", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid bills amount", "error")
            return redirect(url_for("pages.factfind"))

        income_day = request.form.get("income_day", type=int)

        current_user.monthly_income = monthly_income
        current_user.rent_amount = rent_amount
        current_user.bills_amount = bills_amount
        current_user.income_day = income_day
        current_user.factfind_completed = True

        db.session.commit()

        flash("Financial profile saved successfully", "success")
        return redirect(url_for("pages.dashboard"))

    return render_template("factfind.html", profile=current_user.profile_dict())


@page_bp.route("/delete-transaction/<int:transaction_id>", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()

    if not transaction:
        flash("Transaction not found", "error")
        return redirect(url_for("pages.transactions"))

    db.session.delete(transaction)
    db.session.commit()

    flash("Transaction deleted", "success")
    return redirect(url_for("pages.transactions"))