"""
Demo seed script — populates the first user's account with realistic
test data so all overview features are visible without going through
full onboarding manually.

Run once from the Fintrack root:
    python seed_demo.py

Safe to re-run — clears existing seed data for the user first.
"""

from datetime import date, timedelta
import random
from app import create_app, db
from app.models.user import User
from app.models.goal import Goal
from app.models.transaction import Transaction
from app.models.category import Category

app = create_app()

with app.app_context():

    # ── Find the first user ──────────────────────────────────────
    user = User.query.first()
    if not user:
        print("No users found. Register an account first, then run this script.")
        exit(1)

    print(f"Seeding data for: {user.name} ({user.email})")

    # ── Update financial profile ─────────────────────────────────
    user.monthly_income = 3200.00
    user.rent_amount = 950.00
    user.bills_amount = 180.00
    user.income_day = 25
    user.factfind_completed = True

    # ── Clear existing seed transactions and goals ───────────────
    Transaction.query.filter_by(user_id=user.id).delete()
    Goal.query.filter_by(user_id=user.id).delete()
    db.session.flush()

    # ── Create a goal ────────────────────────────────────────────
    goal = Goal(
        user_id=user.id,
        name="House deposit",
        type="savings",
        target_amount=15000.00,
        current_amount=3240.00,
        monthly_allocation=300.00,
        priority_rank=1,
        status="active"
    )
    db.session.add(goal)

    # ── Category lookup ──────────────────────────────────────────
    cats = {c.name: c.id for c in Category.query.all()}
    food_id       = cats.get("Food", 1)
    transport_id  = cats.get("Transport", 1)
    bills_id      = cats.get("Bills", 1)
    entertainment = cats.get("Entertainment", 1)
    shopping_id   = cats.get("Shopping", 1)
    health_id     = cats.get("Health", 1)
    subs_id       = cats.get("Subscriptions", 1)
    income_id     = cats.get("Income", 1)
    other_id      = cats.get("Other", 1)

    today = date.today()

    def d(days_ago):
        return today - timedelta(days=days_ago)

    transactions = [

        # ── Income — last 3 months ───────────────────────────────
        dict(description="Salary", amount=3200.00, type="income",  category_id=income_id, date=d(5),  merchant="Employer"),
        dict(description="Salary", amount=3200.00, type="income",  category_id=income_id, date=d(35), merchant="Employer"),
        dict(description="Salary", amount=3200.00, type="income",  category_id=income_id, date=d(65), merchant="Employer"),

        # ── Rent & bills — recurring ─────────────────────────────
        dict(description="Rent payment",   amount=950.00, type="expense", category_id=bills_id,    date=d(3),  merchant="Landlord"),
        dict(description="Rent payment",   amount=950.00, type="expense", category_id=bills_id,    date=d(33), merchant="Landlord"),
        dict(description="Rent payment",   amount=950.00, type="expense", category_id=bills_id,    date=d(63), merchant="Landlord"),
        dict(description="EDF Energy",     amount=68.00,  type="expense", category_id=bills_id,    date=d(4),  merchant="EDF Energy"),
        dict(description="EDF Energy",     amount=68.00,  type="expense", category_id=bills_id,    date=d(34), merchant="EDF Energy"),
        dict(description="EDF Energy",     amount=68.00,  type="expense", category_id=bills_id,    date=d(64), merchant="EDF Energy"),
        dict(description="Sky Broadband",  amount=42.00,  type="expense", category_id=bills_id,    date=d(4),  merchant="Sky"),
        dict(description="Sky Broadband",  amount=42.00,  type="expense", category_id=bills_id,    date=d(34), merchant="Sky"),
        dict(description="Sky Broadband",  amount=42.00,  type="expense", category_id=bills_id,    date=d(64), merchant="Sky"),

        # ── Subscriptions — recurring ────────────────────────────
        dict(description="Netflix",        amount=17.99,  type="expense", category_id=subs_id,     date=d(6),  merchant="Netflix"),
        dict(description="Netflix",        amount=17.99,  type="expense", category_id=subs_id,     date=d(36), merchant="Netflix"),
        dict(description="Netflix",        amount=17.99,  type="expense", category_id=subs_id,     date=d(66), merchant="Netflix"),
        dict(description="Spotify",        amount=11.99,  type="expense", category_id=subs_id,     date=d(6),  merchant="Spotify"),
        dict(description="Spotify",        amount=11.99,  type="expense", category_id=subs_id,     date=d(36), merchant="Spotify"),
        dict(description="Spotify",        amount=11.99,  type="expense", category_id=subs_id,     date=d(66), merchant="Spotify"),
        dict(description="Gym membership", amount=35.00,  type="expense", category_id=health_id,   date=d(7),  merchant="PureGym"),
        dict(description="Gym membership", amount=35.00,  type="expense", category_id=health_id,   date=d(37), merchant="PureGym"),
        dict(description="Gym membership", amount=35.00,  type="expense", category_id=health_id,   date=d(67), merchant="PureGym"),

        # ── Food — this month slightly elevated ──────────────────
        dict(description="Deliveroo",      amount=34.50,  type="expense", category_id=food_id,     date=d(2),  merchant="Deliveroo"),
        dict(description="Deliveroo",      amount=28.90,  type="expense", category_id=food_id,     date=d(6),  merchant="Deliveroo"),
        dict(description="Tesco",          amount=62.40,  type="expense", category_id=food_id,     date=d(4),  merchant="Tesco"),
        dict(description="Tesco",          amount=55.10,  type="expense", category_id=food_id,     date=d(9),  merchant="Tesco"),
        dict(description="Sainsbury's",    amount=38.20,  type="expense", category_id=food_id,     date=d(12), merchant="Sainsbury's"),
        dict(description="Pret A Manger",  amount=8.50,   type="expense", category_id=food_id,     date=d(3),  merchant="Pret"),
        dict(description="Pret A Manger",  amount=7.90,   type="expense", category_id=food_id,     date=d(7),  merchant="Pret"),

        # Food last month — lower for comparison
        dict(description="Deliveroo",      amount=18.50,  type="expense", category_id=food_id,     date=d(38), merchant="Deliveroo"),
        dict(description="Tesco",          amount=54.30,  type="expense", category_id=food_id,     date=d(40), merchant="Tesco"),
        dict(description="Tesco",          amount=48.60,  type="expense", category_id=food_id,     date=d(50), merchant="Tesco"),
        dict(description="Sainsbury's",    amount=32.10,  type="expense", category_id=food_id,     date=d(55), merchant="Sainsbury's"),

        # ── Transport ────────────────────────────────────────────
        dict(description="TfL",            amount=48.00,  type="expense", category_id=transport_id, date=d(5),  merchant="TfL"),
        dict(description="TfL",            amount=48.00,  type="expense", category_id=transport_id, date=d(35), merchant="TfL"),
        dict(description="TfL",            amount=48.00,  type="expense", category_id=transport_id, date=d(65), merchant="TfL"),
        dict(description="Uber",           amount=12.40,  type="expense", category_id=transport_id, date=d(3),  merchant="Uber"),
        dict(description="Uber",           amount=9.80,   type="expense", category_id=transport_id, date=d(14), merchant="Uber"),

        # ── Shopping ─────────────────────────────────────────────
        dict(description="ASOS",           amount=67.00,  type="expense", category_id=shopping_id, date=d(8),  merchant="ASOS"),
        dict(description="Amazon",         amount=24.99,  type="expense", category_id=shopping_id, date=d(11), merchant="Amazon"),
        dict(description="Boots",          amount=18.60,  type="expense", category_id=shopping_id, date=d(44), merchant="Boots"),

        # ── Entertainment ────────────────────────────────────────
        dict(description="Vue Cinema",     amount=22.00,  type="expense", category_id=entertainment, date=d(10), merchant="Vue"),
        dict(description="Ticketmaster",   amount=85.00,  type="expense", category_id=entertainment, date=d(18), merchant="Ticketmaster"),
        dict(description="Vue Cinema",     amount=19.50,  type="expense", category_id=entertainment, date=d(42), merchant="Vue"),
    ]

    for t in transactions:
        db.session.add(Transaction(user_id=user.id, **t))

    db.session.commit()

    txn_count = Transaction.query.filter_by(user_id=user.id).count()
    print(f"Done. {txn_count} transactions seeded.")
    print(f"Profile: £{user.monthly_income}/month · £{user.rent_amount} rent · £{user.bills_amount} bills")
    print(f"Goal: House deposit — £3,240 of £15,000 · £300/month allocation")
    print(f"Recurring detected: rent, energy, broadband, Netflix, Spotify, gym, TfL")
    print(f"Food spend elevated this month vs last — projection should show timeline shift")
    print()
    print("Restart the server, then visit http://127.0.0.1:5001/overview")
