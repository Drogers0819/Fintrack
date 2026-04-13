"""Test complex scenario: Sarah, 27, Leeds, 5 goals + debt"""
from datetime import date
from dateutil.relativedelta import relativedelta
from app.services.planner_service import generate_financial_plan, can_i_afford, get_plan_summary
import json

# Sarah's profile
profile = {
    "monthly_income": 2400,
    "rent_amount": 875,
    "bills_amount": 320,
    "groceries_estimate": 280,
    "transport_estimate": 95,
}

# Sarah's goals
goals = [
    {
        "id": 1, "name": "Emergency fund", "type": "savings_target",
        "target_amount": 4710, "current_amount": 800,
    },
    {
        "id": 2, "name": "House deposit", "type": "savings_target",
        "target_amount": 15000, "current_amount": 3200,
        "deadline": "2029-03-01",
    },
    {
        "id": 3, "name": "Wedding fund", "type": "savings_target",
        "target_amount": 8000, "current_amount": 500,
        "deadline": "2027-09-01",
    },
    {
        "id": 4, "name": "Holiday Greece", "type": "savings_target",
        "target_amount": 1800, "current_amount": 0,
        "deadline": "2026-08-01",
    },
    {
        "id": 5, "name": "Pay off credit card", "type": "savings_target",
        "target_amount": 1200, "current_amount": 0,
    },
]

# Debts
debts = [
    {"name": "Credit card", "amount": 1200, "min_payment": 25}
]

print("=" * 60)
print("SARAH'S FINANCIAL SCENARIO")
print("=" * 60)

# Basic maths
essentials = 875 + 320 + 280 + 95
surplus = 2400 - essentials
print(f"\nIncome:     £{2400}")
print(f"Essentials: £{essentials}")
print(f"Surplus:    £{surplus}")

print("\n" + "=" * 60)
print("TEST 1: Plan generation (without debt as separate param)")
print("=" * 60)

plan = generate_financial_plan(profile, goals)

if plan.get("error"):
    print(f"\nERROR: {plan['error']}")
else:
    print(f"\nSurplus: £{plan['surplus']}")
    print(f"Phases: {plan['phase_count']}")
    print(f"\nPot allocations:")
    total_allocated = 0
    for p in plan["pots"]:
        total_allocated += p["monthly_amount"]
        status = ""
        if p.get("completed"):
            status = " [DONE]"
        elif p.get("months_to_target"):
            status = f" [{p['months_to_target']} months]"
        print(f"  {p['name']:25s} £{p['monthly_amount']:>7.2f}/mo  "
              f"(£{p.get('current', 0):>8,.0f} of £{p.get('target', 0) or 0:>8,.0f}){status}")
    
    print(f"\n  {'TOTAL ALLOCATED':25s} £{total_allocated:>7.2f}/mo")
    print(f"  {'SURPLUS':25s} £{plan['surplus']:>7.2f}/mo")
    print(f"  {'DIFFERENCE':25s} £{abs(total_allocated - plan['surplus']):>7.2f}")

    print(f"\nPhase details:")
    for phase in plan["phases"]:
        print(f"\n  Phase {phase['phase']}:")
        print(f"    Duration: {phase['duration_months']} months")
        print(f"    Active pots: {', '.join(phase['active_pots'])}")
        if phase.get("completed_pots"):
            print(f"    Completed: {', '.join(phase['completed_pots'])}")
        print(f"    Description: {phase['description']}")

    print(f"\nAlerts:")
    if plan["alerts"]:
        for alert in plan["alerts"]:
            print(f"  [{alert['severity'].upper()}] {alert['message']}")
    else:
        print("  None")

print("\n" + "=" * 60)
print("TEST 2: Plan summary (whisper text)")
print("=" * 60)

summary = get_plan_summary(plan)
print(f"\n  \"{summary}\"")

print("\n" + "=" * 60)
print("TEST 3: Can Sarah afford a £200 birthday weekend?")
print("=" * 60)

afford = can_i_afford(plan, "Birthday weekend", 200)
print(f"\n  Affordable: {afford['affordable']}")
print(f"  Impact: {afford.get('impact', 'N/A')}")
print(f"  Message: {afford['message']}")

print("\n" + "=" * 60)
print("TEST 4: Can Sarah afford a £2000 emergency car repair?")
print("=" * 60)

afford2 = can_i_afford(plan, "Emergency car repair", 2000)
print(f"\n  Affordable: {afford2['affordable']}")
print(f"  Impact: {afford2.get('impact', 'N/A')}")
print(f"  Message: {afford2['message']}")

print("\n" + "=" * 60)
print("TEST 5: Plan with debt as separate parameter")
print("=" * 60)

# Remove credit card from goals, pass as debt instead
goals_no_debt = [g for g in goals if g["name"] != "Pay off credit card"]
plan_with_debt = generate_financial_plan(profile, goals_no_debt, debts=debts)

if plan_with_debt.get("error"):
    print(f"\nERROR: {plan_with_debt['error']}")
else:
    print(f"\nSurplus: £{plan_with_debt['surplus']}")
    print(f"Phases: {plan_with_debt['phase_count']}")
    print(f"\nPot allocations:")
    for p in plan_with_debt["pots"]:
        status = ""
        if p.get("completed"):
            status = " [DONE]"
        elif p.get("months_to_target"):
            status = f" [{p['months_to_target']} months]"
        print(f"  {p['name']:25s} £{p['monthly_amount']:>7.2f}/mo  "
              f"(£{p.get('current', 0):>8,.0f} of £{p.get('target', 0) or 0:>8,.0f}){status}")

print("\n" + "=" * 60)
print("TEST 6: Validation checks")
print("=" * 60)

# Check no goal gets zero
zero_pots = [p for p in plan["pots"] if p["monthly_amount"] == 0 
             and not p.get("completed") and p["type"] not in ("lifestyle", "buffer")]
print(f"\n  Goals with £0 allocation: {len(zero_pots)}")
if zero_pots:
    for p in zero_pots:
        print(f"    WARNING: {p['name']} has £0/mo!")

# Check total doesn't exceed surplus
total = sum(p["monthly_amount"] for p in plan["pots"])
print(f"  Total allocated: £{total:.2f}")
print(f"  Surplus: £{plan['surplus']:.2f}")
print(f"  Over-allocated: {'YES - PROBLEM!' if total > plan['surplus'] + 0.01 else 'No - OK'}")

# Check lifestyle exists and is reasonable
lifestyle = next((p for p in plan["pots"] if p["type"] == "lifestyle"), None)
print(f"  Lifestyle allocated: £{lifestyle['monthly_amount']:.2f}/mo" if lifestyle else "  WARNING: No lifestyle pot!")

# Check emergency fund exists
emergency = next((p for p in plan["pots"] if p["type"] == "emergency"), None)
print(f"  Emergency fund: £{emergency['monthly_amount']:.2f}/mo (target £{emergency['target']:.0f})" if emergency else "  WARNING: No emergency fund!")

# Check projections exist
print(f"  Monthly projections: {len(plan.get('monthly_projections', []))} months")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)