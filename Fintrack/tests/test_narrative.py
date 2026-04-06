from datetime import date, timedelta
from app.services.narrative_service import (
    generate_monthly_narrative,
    generate_narrative_email_data,
    _build_opening,
    _build_category_breakdown,
    _build_goal_section,
    _build_budget_section,
    _build_highlights,
    _build_recurring_section,
    _build_closing,
    _generate_subject_line,
    _ordinal
)


class TestOrdinal:

    def test_first(self):
        assert _ordinal(1) == "1st"

    def test_second(self):
        assert _ordinal(2) == "2nd"

    def test_third(self):
        assert _ordinal(3) == "3rd"

    def test_fourth(self):
        assert _ordinal(4) == "4th"

    def test_eleventh(self):
        assert _ordinal(11) == "11th"

    def test_twelfth(self):
        assert _ordinal(12) == "12th"

    def test_thirteenth(self):
        assert _ordinal(13) == "13th"

    def test_twentyfirst(self):
        assert _ordinal(21) == "21st"


class TestBuildOpening:

    def test_above_average(self):
        result = _build_opening(
            "April", 2026, 1200, 1700, 45,
            {"historical_average": 1000, "difference": 200}, "Sarah"
        )
        assert "heavier" in result["text"]
        assert "1,200" in result["text"]
        assert "Sarah" in result["text"]

    def test_below_average(self):
        result = _build_opening(
            "April", 2026, 800, 1700, 30,
            {"historical_average": 1000, "difference": -200}, "Sarah"
        )
        assert "lighter" in result["text"]

    def test_no_comparison(self):
        result = _build_opening(
            "April", 2026, 500, 1700, 20,
            {}, "Sarah"
        )
        assert "500" in result["text"]
        assert "1,700" in result["text"]

    def test_no_spending(self):
        result = _build_opening(
            "April", 2026, 0, 0, 0, {}, ""
        )
        assert "No spending" in result["text"]


class TestBuildCategoryBreakdown:

    def test_with_expenses(self):
        expenses = [
            {"amount": 200, "category": "Food"},
            {"amount": 150, "category": "Transport"},
            {"amount": 80, "category": "Entertainment"},
            {"amount": 50, "category": "Health"}
        ]

        result = _build_category_breakdown(expenses, "April")
        assert "Food" in result["text"]
        assert "Transport" in result["text"]

    def test_single_category(self):
        expenses = [{"amount": 100, "category": "Food"}]

        result = _build_category_breakdown(expenses, "April")
        assert "Food" in result["text"]

    def test_empty(self):
        result = _build_category_breakdown([], "April")
        assert result is None


class TestBuildGoalSection:

    def test_with_goals(self):
        goals = [
            {"name": "House deposit", "status": "active", "progress_percent": 31},
            {"name": "Holiday", "status": "active", "progress_percent": 50}
        ]

        result = _build_goal_section(goals, "April")
        assert "House deposit" in result["text"]
        assert "31%" in result["text"]

    def test_no_active_goals(self):
        goals = [{"name": "Done", "status": "completed", "progress_percent": 100}]
        result = _build_goal_section(goals, "April")
        assert result is None

    def test_many_goals(self):
        goals = [
            {"name": f"Goal {i}", "status": "active", "progress_percent": i * 10}
            for i in range(1, 6)
        ]

        result = _build_goal_section(goals, "April")
        assert "Plus 2 more" in result["text"]


class TestBuildBudgetSection:

    def test_all_on_track(self):
        budgets = [
            {"category_name": "Food", "status": "on_track"},
            {"category_name": "Transport", "status": "on_track"}
        ]

        result = _build_budget_section(budgets, "April")
        assert "on track" in result["text"]
        assert "discipline" in result["text"]

    def test_exceeded(self):
        budgets = [
            {"category_name": "Food", "status": "exceeded"},
            {"category_name": "Transport", "status": "on_track"}
        ]

        result = _build_budget_section(budgets, "April")
        assert "Food" in result["text"]
        assert "over" in result["text"]

    def test_warning(self):
        budgets = [{"category_name": "Food", "status": "warning"}]

        result = _build_budget_section(budgets, "April")
        assert "close" in result["text"]

    def test_empty(self):
        result = _build_budget_section([], "April")
        assert result is None


class TestBuildHighlights:

    def test_largest_transaction(self):
        expenses = [
            {"amount": 50, "description": "Tesco", "date": date.today()},
            {"amount": 180, "description": "Amazon", "date": date.today()},
            {"amount": 30, "description": "Uber", "date": date.today()}
        ]

        result = _build_highlights([], expenses, "April")
        assert "Amazon" in result["text"]
        assert "180" in result["text"]

    def test_with_anomalies(self):
        anomalies = [
            {"severity": "high", "type": "large_transaction",
             "message": "Unusual £500 spend"}
        ]

        result = _build_highlights(anomalies, [], "April")
        assert "500" in result["text"]

    def test_quiet_period(self):
        anomalies = [
            {"severity": "low", "type": "quiet_period",
             "message": "Low spend week"}
        ]

        result = _build_highlights(anomalies, [], "April")
        assert "Low spend" in result["text"]

    def test_empty(self):
        result = _build_highlights([], [], "April")
        assert result is None


class TestBuildRecurringSection:

    def test_with_recurring(self):
        recurring = {"count": 5, "total_monthly_cost": 120}

        result = _build_recurring_section(recurring)
        assert "5" in result["text"]
        assert "120" in result["text"]
        assert "1,440" in result["text"]

    def test_no_recurring(self):
        result = _build_recurring_section({"count": 0, "total_monthly_cost": 0})
        assert result is None


class TestBuildClosing:

    def test_with_goal_progress(self):
        goals = [{"name": "House deposit", "status": "active", "progress_percent": 31}]
        result = _build_closing(1000, goals, [], "April", {"money_left": 200, "days_remaining": 10})
        assert "31%" in result["text"]
        assert "House deposit" in result["text"]

    def test_with_money_left(self):
        result = _build_closing(1000, [], [], "April", {"money_left": 340, "days_remaining": 14})
        assert "340" in result["text"]

    def test_fallback(self):
        result = _build_closing(0, [], [], "April", {})
        assert "Keep tracking" in result["text"]


class TestGenerateSubjectLine:

    def test_goal_based(self):
        goals = [{"name": "House deposit", "status": "active", "progress_percent": 55}]
        subject = _generate_subject_line("April", 1000, {}, goals)
        assert "55%" in subject
        assert "House deposit" in subject

    def test_below_average(self):
        comparison = {"historical_average": 1000, "difference": -150}
        subject = _generate_subject_line("April", 850, comparison, [])
        assert "less" in subject

    def test_above_average(self):
        comparison = {"historical_average": 1000, "difference": 200}
        subject = _generate_subject_line("April", 1200, comparison, [])
        assert "above" in subject

    def test_fallback(self):
        subject = _generate_subject_line("April", 500, {}, [])
        assert "April" in subject


class TestGenerateMonthlyNarrative:

    def test_full_narrative(self):
        today = date.today()
        data = {
            "user_name": "Sarah",
            "transactions": [
                {"amount": 200, "type": "expense", "date": today,
                 "category": "Food", "description": "Tesco"},
                {"amount": 50, "type": "expense", "date": today,
                 "category": "Transport", "description": "Uber"},
                {"amount": 1700, "type": "income", "date": today,
                 "category": "Income", "description": "Salary"}
            ],
            "goals": [
                {"name": "House deposit", "status": "active", "progress_percent": 31}
            ],
            "budget_statuses": [
                {"category_name": "Food", "status": "on_track"}
            ],
            "recurring": {"count": 3, "total_monthly_cost": 45},
            "predictions": {
                "comparison": {"historical_average": 1000, "difference": -50},
                "spending_so_far": {"total": 250}
            },
            "anomalies": {"anomalies": []},
            "money_left": 300,
            "days_remaining": 15
        }

        result = generate_monthly_narrative(data)
        assert result["narrative"] is not None
        assert len(result["narrative"]) > 50
        assert len(result["sections"]) >= 3
        assert result["subject_line"] is not None
        assert "Sarah" in result["narrative"]

    def test_empty_data(self):
        data = {
            "user_name": "",
            "transactions": [],
            "goals": [],
            "budget_statuses": [],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "predictions": {"comparison": {}, "spending_so_far": {}},
            "anomalies": {"anomalies": []}
        }

        result = generate_monthly_narrative(data)
        assert result["narrative"] is not None
        assert result["stats"]["total_expenses"] == 0

    def test_specific_month(self):
        data = {
            "user_name": "Daniel",
            "transactions": [
                {"amount": 100, "type": "expense",
                 "date": date(2026, 3, 15), "category": "Food",
                 "description": "Tesco"}
            ],
            "goals": [],
            "budget_statuses": [],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "predictions": {"comparison": {}, "spending_so_far": {}},
            "anomalies": {"anomalies": []}
        }

        result = generate_monthly_narrative(data, target_month=3, target_year=2026)
        assert result["month_name"] == "March"
        assert result["month"] == 3


class TestNarrativeEmailData:

    def test_email_data(self):
        today = date.today()
        data = {
            "user_name": "Sarah",
            "transactions": [
                {"amount": 200, "type": "expense", "date": today,
                 "category": "Food", "description": "Tesco"}
            ],
            "goals": [
                {"name": "House deposit", "status": "active",
                 "progress_percent": 31, "current_amount": 3100,
                 "target_amount": 10000}
            ],
            "budget_statuses": [],
            "recurring": {"count": 0, "total_monthly_cost": 0},
            "predictions": {"comparison": {}, "spending_so_far": {}},
            "anomalies": {"anomalies": []},
            "member_since": "March 2026"
        }

        result = generate_narrative_email_data(data)
        assert result["subject"] is not None
        assert result["narrative"] is not None
        assert result["user_name"] == "Sarah"
        assert result["primary_goal"] is not None
        assert result["primary_goal"]["name"] == "House deposit"


class TestNarrativeAPI:

    def test_monthly_narrative(self, auth_client):
        response = auth_client.get("/api/narrative/monthly")
        assert response.status_code == 200
        data = response.get_json()
        assert "narrative" in data
        assert "sections" in data
        assert "subject_line" in data

    def test_email_preview(self, auth_client):
        response = auth_client.get("/api/narrative/email-preview")
        assert response.status_code == 200
        data = response.get_json()
        assert "subject" in data
        assert "narrative" in data

    def test_specific_month(self, auth_client):
        response = auth_client.get("/api/narrative/monthly?month=3&year=2026")
        assert response.status_code == 200
        data = response.get_json()
        assert data["month_name"] == "March"

    def test_narrative_without_auth(self, client):
        response = client.get("/api/narrative/monthly")
        assert response.status_code == 401