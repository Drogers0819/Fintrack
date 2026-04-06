from datetime import date, timedelta
from collections import defaultdict
import calendar


def generate_monthly_narrative(user_data, target_month=None, target_year=None):
    """
    Generates a human-readable financial narrative for a given month.
    Written in second person, specific to the user's actual data.
    
    This is the story the user reads at the end of each month —
    it should feel personal, honest, and specific.
    """
    today = date.today()
    if target_month is None:
        target_month = today.month
    if target_year is None:
        target_year = today.year

    month_name = date(target_year, target_month, 1).strftime("%B")

    # Extract relevant data
    transactions = user_data.get("transactions", [])
    goals = user_data.get("goals", [])
    budgets = user_data.get("budget_statuses", [])
    recurring = user_data.get("recurring", {})
    predictions = user_data.get("predictions", {})
    comparison = predictions.get("comparison", {})
    anomalies = user_data.get("anomalies", {}).get("anomalies", [])

    # Filter transactions to target month
    month_txns = _filter_month_transactions(transactions, target_month, target_year)
    expenses = [t for t in month_txns if t.get("type") == "expense"]
    income_txns = [t for t in month_txns if t.get("type") == "income"]

    total_expenses = round(sum(float(t["amount"]) for t in expenses), 2)
    total_income = round(sum(float(t["amount"]) for t in income_txns), 2)
    txn_count = len(month_txns)

    # Build narrative sections
    sections = []

    # 1. Opening — the headline
    sections.append(_build_opening(
        month_name, target_year, total_expenses, total_income,
        txn_count, comparison, user_data.get("user_name", "")
    ))

    # 2. Spending breakdown — where the money went
    category_breakdown = _build_category_breakdown(expenses, month_name)
    if category_breakdown:
        sections.append(category_breakdown)

    # 3. Goal progress — what moved forward
    goal_section = _build_goal_section(goals, month_name)
    if goal_section:
        sections.append(goal_section)

    # 4. Budget performance — how limits held
    budget_section = _build_budget_section(budgets, month_name)
    if budget_section:
        sections.append(budget_section)

    # 5. Notable moments — anomalies and highlights
    highlights = _build_highlights(anomalies, expenses, month_name)
    if highlights:
        sections.append(highlights)

    # 6. Recurring costs — the fixed landscape
    recurring_section = _build_recurring_section(recurring)
    if recurring_section:
        sections.append(recurring_section)

    # 7. Closing — forward-looking
    sections.append(_build_closing(
        total_expenses, goals, budgets, month_name, user_data
    ))

    # Assemble full narrative
    full_narrative = "\n\n".join(s["text"] for s in sections if s.get("text"))

    return {
        "month": target_month,
        "year": target_year,
        "month_name": month_name,
        "narrative": full_narrative,
        "sections": sections,
        "stats": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "transaction_count": txn_count,
            "net": round(total_income - total_expenses, 2)
        },
        "subject_line": _generate_subject_line(
            month_name, total_expenses, comparison, goals
        )
    }


def _filter_month_transactions(transactions, month, year):
    """Filters transactions to a specific month."""
    filtered = []
    for t in transactions:
        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))
        if txn_date.month == month and txn_date.year == year:
            filtered.append(t)
    return filtered


def _build_opening(month_name, year, total_expenses, total_income, txn_count, comparison, user_name):
    """The first paragraph — sets the tone."""
    hist_avg = comparison.get("historical_average", 0)
    diff = comparison.get("difference", 0)

    greeting = f"{user_name}'s " if user_name else "Your "

    if hist_avg > 0 and diff != 0:
        if diff > 0:
            tone = f"£{abs(diff):.2f} more than your usual"
            verdict = "a heavier month than average"
        else:
            tone = f"£{abs(diff):.2f} less than your usual"
            verdict = "a lighter month than average"

        text = (
            f"{greeting}{month_name} {year} in review.\n\n"
            f"This was {verdict}. You spent £{total_expenses:,.2f} across "
            f"{txn_count} transactions — {tone}."
        )
    elif total_expenses > 0:
        text = (
            f"{greeting}{month_name} {year} in review.\n\n"
            f"You spent £{total_expenses:,.2f} across {txn_count} transactions this month."
        )
    else:
        text = (
            f"{greeting}{month_name} {year} in review.\n\n"
            f"No spending recorded this month. Upload a bank statement to see your full picture."
        )

    if total_income > 0:
        text += f" You received £{total_income:,.2f} in income."

    return {"section": "opening", "text": text}


def _build_category_breakdown(expenses, month_name):
    """Where the money went — top categories."""
    if not expenses:
        return None

    by_cat = defaultdict(float)
    by_cat_count = defaultdict(int)

    for t in expenses:
        cat = t.get("category", "Other")
        by_cat[cat] += float(t["amount"])
        by_cat_count[cat] += 1

    sorted_cats = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
    total = sum(v for _, v in sorted_cats)

    if not sorted_cats:
        return None

    top = sorted_cats[0]
    top_pct = round((top[1] / total) * 100) if total > 0 else 0

    text = f"Where your money went: {top[0]} was your biggest category at £{top[1]:,.2f} ({top_pct}% of spending)."

    if len(sorted_cats) >= 2:
        second = sorted_cats[1]
        text += f" Next was {second[0]} at £{second[1]:,.2f}."

    if len(sorted_cats) >= 3:
        rest_total = sum(v for _, v in sorted_cats[2:])
        text += f" Everything else totalled £{rest_total:,.2f} across {len(sorted_cats) - 2} other categories."

    return {"section": "category_breakdown", "text": text}


def _build_goal_section(goals, month_name):
    """Goal progress narrative."""
    active = [g for g in goals if g.get("status") == "active"]

    if not active:
        return None

    parts = []

    for g in active[:3]:
        name = g.get("name", "your goal")
        progress = g.get("progress_percent")

        if progress is not None and progress > 0:
            parts.append(f"{name} is {progress}% complete")
        elif progress == 0:
            parts.append(f"{name} is just getting started")

    if not parts:
        return None

    if len(parts) == 1:
        text = f"Goal update: {parts[0]}."
    elif len(parts) == 2:
        text = f"Goal updates: {parts[0]}, and {parts[1]}."
    else:
        text = f"Goal updates: {', '.join(parts[:-1])}, and {parts[-1]}."

    remaining = len(active) - 3
    if remaining > 0:
        text += f" Plus {remaining} more goal{'s' if remaining != 1 else ''} in progress."

    return {"section": "goals", "text": text}


def _build_budget_section(budgets, month_name):
    """Budget performance narrative."""
    if not budgets:
        return None

    exceeded = [b for b in budgets if b.get("status") == "exceeded"]
    warning = [b for b in budgets if b.get("status") == "warning"]
    on_track = [b for b in budgets if b.get("status") == "on_track"]

    total = len(exceeded) + len(warning) + len(on_track)
    if total == 0:
        return None

    if exceeded:
        names = ", ".join(b.get("category_name", "?") for b in exceeded)
        text = f"Budget check: {len(exceeded)} budget{'s' if len(exceeded) != 1 else ''} went over this month ({names})."
        if on_track:
            text += f" {len(on_track)} stayed on track."
    elif warning:
        names = ", ".join(b.get("category_name", "?") for b in warning)
        text = f"Budget check: {names} {'were' if len(warning) > 1 else 'was'} close to the limit but you stayed within bounds."
        if on_track:
            text += f" {len(on_track)} {'others' if len(on_track) > 1 else 'other'} comfortably on track."
    else:
        text = f"Budget check: all {len(on_track)} budget{'s' if len(on_track) != 1 else ''} stayed on track this month. Solid discipline."

    return {"section": "budgets", "text": text}


def _build_highlights(anomalies, expenses, month_name):
    """Notable moments — largest transaction, anomalies."""
    parts = []

    # Largest single transaction
    if expenses:
        largest = max(expenses, key=lambda t: float(t["amount"]))
        amount = float(largest["amount"])
        desc = largest.get("description", "an unknown merchant")
        txn_date = largest["date"] if isinstance(largest["date"], date) else date.fromisoformat(str(largest["date"]))
        day = txn_date.day

        parts.append(
            f"Your biggest single spend was £{amount:,.2f} at {desc} on the {_ordinal(day)}."
        )

    # Notable anomalies
    important = [a for a in anomalies if a.get("severity") in ("high", "medium")]
    for a in important[:2]:
        if a.get("type") == "large_transaction":
            parts.append(a.get("message", ""))
        elif a.get("type") == "category_spike":
            parts.append(a.get("message", ""))
        elif a.get("type") == "new_merchant":
            parts.append(a.get("message", ""))

    # Quiet period — frame positively
    quiet = [a for a in anomalies if a.get("type") == "quiet_period"]
    if quiet:
        parts.append(quiet[0].get("message", ""))

    if not parts:
        return None

    text = "Highlights: " + " ".join(parts[:3])

    return {"section": "highlights", "text": text}


def _build_recurring_section(recurring):
    """Recurring costs summary."""
    count = recurring.get("count", 0)
    total = recurring.get("total_monthly_cost", 0)

    if count == 0:
        return None

    text = (
        f"Your regular payments: {count} recurring expense{'s' if count != 1 else ''} "
        f"totalling £{total:,.2f}/month (£{total * 12:,.2f}/year)."
    )

    return {"section": "recurring", "text": text}


def _build_closing(total_expenses, goals, budgets, month_name, user_data):
    """Forward-looking closing paragraph."""
    parts = []

    active_goals = [g for g in goals if g.get("status") == "active"]

    if active_goals:
        primary = active_goals[0]
        name = primary.get("name", "your primary goal")
        progress = primary.get("progress_percent", 0)

        if progress and progress > 0:
            remaining = 100 - progress
            parts.append(f"You're {progress}% of the way to {name} — {remaining}% to go.")

    money_left = user_data.get("money_left")
    days_remaining = user_data.get("days_remaining", 0)

    if money_left is not None and days_remaining > 0 and money_left > 0:
        parts.append(f"You still have £{money_left:,.2f} to work with for the rest of the month.")

    if not parts:
        parts.append("Keep tracking your finances to build a clearer picture month by month.")

    text = " ".join(parts)

    return {"section": "closing", "text": text}


def _generate_subject_line(month_name, total_expenses, comparison, goals):
    """
    Generates the email subject line. Must be specific and personal —
    never generic like "Your monthly report."
    """
    diff = comparison.get("difference", 0)
    hist_avg = comparison.get("historical_average", 0)

    active_goals = [g for g in goals if g.get("status") == "active"]

    # Try goal-based subject
    if active_goals:
        primary = active_goals[0]
        progress = primary.get("progress_percent")
        name = primary.get("name", "your goal")

        if progress and progress >= 50:
            return f"You're {progress}% of the way to {name}"

    # Try comparison-based subject
    if hist_avg > 0 and diff != 0:
        if diff < 0:
            return f"You spent £{abs(diff):.0f} less in {month_name} — here's the full picture"
        else:
            return f"Your {month_name} spending was £{diff:.0f} above average — let's look at why"

    # Fallback
    if total_expenses > 0:
        return f"Your {month_name} financial story — £{total_expenses:,.0f} in review"
    else:
        return f"Your {month_name} financial summary"


def _ordinal(n):
    """Returns ordinal string for a number (1st, 2nd, 3rd, etc.)"""
    if 11 <= n <= 13:
        return f"{n}th"
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def generate_narrative_email_data(user_data, target_month=None, target_year=None):
    """
    Generates the complete data structure needed for the monthly
    email template. Includes narrative, stats, and template variables.
    """
    narrative = generate_monthly_narrative(user_data, target_month, target_year)

    # Calculate months as a Claro user
    member_since = user_data.get("member_since", "")
    today = date.today()

    return {
        "subject": narrative["subject_line"],
        "narrative": narrative["narrative"],
        "sections": narrative["sections"],
        "stats": narrative["stats"],
        "month_name": narrative["month_name"],
        "year": narrative["year"],
        "user_name": user_data.get("user_name", ""),
        "member_since": member_since,
        "primary_goal": _get_primary_goal_summary(user_data.get("goals", [])),
        "top_category": _get_top_category(user_data.get("transactions", []),
                                           narrative["month"], narrative["year"]),
        "generated_at": today.isoformat()
    }


def _get_primary_goal_summary(goals):
    """Extracts primary goal data for the email template."""
    active = [g for g in goals if g.get("status") == "active"]
    if not active:
        return None

    primary = active[0]
    return {
        "name": primary.get("name"),
        "progress_percent": primary.get("progress_percent", 0),
        "current_amount": primary.get("current_amount", 0),
        "target_amount": primary.get("target_amount")
    }


def _get_top_category(transactions, month, year):
    """Finds the top spending category for the month."""
    by_cat = defaultdict(float)

    for t in transactions:
        if t.get("type") != "expense":
            continue
        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))
        if txn_date.month == month and txn_date.year == year:
            by_cat[t.get("category", "Other")] += float(t["amount"])

    if not by_cat:
        return None

    top = max(by_cat.items(), key=lambda x: x[1])
    return {"name": top[0], "amount": round(top[1], 2)}