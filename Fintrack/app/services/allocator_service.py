from datetime import date, timedelta
import math


def calculate_waterfall(monthly_income, fixed_commitments, goals):
    if not monthly_income or monthly_income <= 0:
        return {
            "error": "Monthly income is required",
            "allocations": [],
            "surplus": 0,
            "total_income": 0,
            "total_commitments": 0,
            "unallocated": 0
        }

    income = float(monthly_income)
    commitments = float(fixed_commitments) if fixed_commitments else 0

    surplus = income - commitments

    if surplus <= 0:
        return {
            "error": "Your commitments exceed your income. No surplus available for goals.",
            "allocations": [],
            "surplus": round(surplus, 2),
            "total_income": round(income, 2),
            "total_commitments": round(commitments, 2),
            "unallocated": 0
        }

    sorted_goals = sorted(goals, key=lambda g: g.get("priority_rank", 99))

    allocations = []
    remaining = surplus

    for goal in sorted_goals:
        if remaining <= 0:
            allocations.append({
                "goal_id": goal.get("id"),
                "goal_name": goal.get("name"),
                "type": goal.get("type"),
                "requested": float(goal.get("monthly_allocation", 0) or 0),
                "allocated": 0,
                "status": "unfunded",
                "reason": "No surplus remaining after higher-priority goals"
            })
            continue

        goal_type = goal.get("type", "savings_target")
        requested = float(goal.get("monthly_allocation", 0) or 0)

        if goal_type == "spending_allocation":
            allocated = min(requested, remaining)
            remaining -= allocated

            allocations.append({
                "goal_id": goal.get("id"),
                "goal_name": goal.get("name"),
                "type": goal_type,
                "requested": round(requested, 2),
                "allocated": round(allocated, 2),
                "status": "funded" if allocated >= requested else "partially_funded",
                "reason": None if allocated >= requested else f"Only £{allocated:.2f} available of £{requested:.2f} requested"
            })

        elif goal_type in ("savings_target", "accumulation"):
            if requested > 0:
                allocated = min(requested, remaining)
            else:
                allocated = remaining

            remaining -= allocated

            projection = None
            if goal_type == "savings_target" and goal.get("target_amount"):
                target = float(goal["target_amount"])
                current = float(goal.get("current_amount", 0))
                remaining_amount = target - current

                if allocated > 0 and remaining_amount > 0:
                    months_to_target = math.ceil(remaining_amount / allocated)
                    projected_date = _add_months(date.today(), months_to_target)
                    projection = {
                        "months_to_target": months_to_target,
                        "projected_date": projected_date.isoformat(),
                        "remaining_amount": round(remaining_amount, 2)
                    }
                elif remaining_amount <= 0:
                    projection = {
                        "months_to_target": 0,
                        "projected_date": date.today().isoformat(),
                        "remaining_amount": 0
                    }

            allocations.append({
                "goal_id": goal.get("id"),
                "goal_name": goal.get("name"),
                "type": goal_type,
                "requested": round(requested, 2),
                "allocated": round(allocated, 2),
                "status": "funded" if requested <= 0 or allocated >= requested else "partially_funded",
                "projection": projection,
                "reason": None if requested <= 0 or allocated >= requested else f"Only £{allocated:.2f} available of £{requested:.2f} requested"
            })

    return {
        "allocations": allocations,
        "surplus": round(surplus, 2),
        "total_income": round(income, 2),
        "total_commitments": round(commitments, 2),
        "unallocated": round(remaining, 2),
        "fully_allocated": remaining <= 0.01
    }


def _add_months(start_date, months):
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, 28)
    return date(year, month, day)


def detect_conflicts(allocations):
    conflicts = []

    unfunded = [a for a in allocations if a["status"] == "unfunded"]
    partially_funded = [a for a in allocations if a["status"] == "partially_funded"]

    if unfunded:
        names = ", ".join([a["goal_name"] for a in unfunded])
        conflicts.append({
            "type": "insufficient_surplus",
            "severity": "high",
            "message": f"These goals cannot be funded with your current surplus: {names}. Consider increasing income or reducing commitments.",
            "affected_goals": [a["goal_id"] for a in unfunded]
        })

    if partially_funded:
        for a in partially_funded:
            shortfall = a["requested"] - a["allocated"]
            conflicts.append({
                "type": "partial_funding",
                "severity": "medium",
                "message": f"'{a['goal_name']}' is receiving £{a['allocated']:.2f}/month instead of the £{a['requested']:.2f} you planned. Shortfall: £{shortfall:.2f}/month.",
                "affected_goals": [a["goal_id"]]
            })

    return conflicts


def generate_waterfall_summary(user_profile, goals_data):
    waterfall = calculate_waterfall(
        user_profile.get("monthly_income"),
        user_profile.get("fixed_commitments"),
        goals_data
    )

    if "error" in waterfall and waterfall["error"]:
        return waterfall

    conflicts = detect_conflicts(waterfall["allocations"])

    waterfall["conflicts"] = conflicts
    waterfall["conflict_count"] = len(conflicts)
    waterfall["has_conflicts"] = len(conflicts) > 0

    return waterfall