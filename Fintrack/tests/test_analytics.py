from datetime import date


class TestSpendingByCategory:

    def test_spending_by_category_with_data(self, auth_client):
        auth_client.post("/api/transactions", json={
            "amount": 52.40, "description": "Tesco",
            "category_id": 1, "type": "expense",
            "date": date.today().isoformat()
        })
        auth_client.post("/api/transactions", json={
            "amount": 28.50, "description": "Deliveroo",
            "category_id": 1, "type": "expense",
            "date": date.today().isoformat()
        })
        auth_client.post("/api/transactions", json={
            "amount": 12.80, "description": "Uber",
            "category_id": 2, "type": "expense",
            "date": date.today().isoformat()
        })

        response = auth_client.get("/api/analytics/spending-by-category")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_expenses"] == 93.70
        assert data["category_count"] == 2
        assert data["categories"][0]["total"] == 80.90
        assert data["categories"][0]["name"] == "Food"
        assert data["categories"][1]["total"] == 12.80

    def test_spending_by_category_empty(self, auth_client):
        response = auth_client.get("/api/analytics/spending-by-category")
        assert response.status_code == 200
        data = response.get_json()
        assert data["total_expenses"] == 0
        assert data["categories"] == []

    def test_spending_by_category_specific_month(self, auth_client):
        auth_client.post("/api/transactions", json={
            "amount": 50, "description": "Test",
            "category_id": 1, "type": "expense",
            "date": "2026-01-15"
        })

        response = auth_client.get("/api/analytics/spending-by-category?month=1&year=2026")
        assert response.status_code == 200
        data = response.get_json()
        assert data["month"] == 1
        assert data["year"] == 2026
        assert data["total_expenses"] == 50

    def test_spending_excludes_income(self, auth_client):
        auth_client.post("/api/transactions", json={
            "amount": 1700, "description": "Salary",
            "type": "income", "date": date.today().isoformat()
        })
        auth_client.post("/api/transactions", json={
            "amount": 50, "description": "Food",
            "category_id": 1, "type": "expense",
            "date": date.today().isoformat()
        })

        response = auth_client.get("/api/analytics/spending-by-category")
        data = response.get_json()
        assert data["total_expenses"] == 50

    def test_spending_by_category_without_auth(self, client):
        response = client.get("/api/analytics/spending-by-category")
        assert response.status_code == 401


class TestMonthlySummary:

    def test_monthly_summary_with_data(self, auth_client):
        auth_client.post("/api/transactions", json={
            "amount": 1700, "description": "Salary",
            "type": "income", "date": date.today().isoformat()
        })
        auth_client.post("/api/transactions", json={
            "amount": 800, "description": "Rent",
            "type": "expense", "date": date.today().isoformat()
        })

        response = auth_client.get("/api/analytics/monthly-summary?months=1")
        assert response.status_code == 200
        data = response.get_json()
        assert data["months_included"] == 1
        assert data["summaries"][0]["income"] == 1700
        assert data["summaries"][0]["expenses"] == 800
        assert data["summaries"][0]["balance"] == 900

    def test_monthly_summary_empty(self, auth_client):
        response = auth_client.get("/api/analytics/monthly-summary?months=3")
        assert response.status_code == 200
        data = response.get_json()
        assert data["months_included"] == 3
        for s in data["summaries"]:
            assert s["income"] == 0
            assert s["expenses"] == 0

    def test_monthly_summary_default_months(self, auth_client):
        response = auth_client.get("/api/analytics/monthly-summary")
        assert response.status_code == 200
        data = response.get_json()
        assert data["months_included"] == 6

    def test_monthly_summary_without_auth(self, client):
        response = client.get("/api/analytics/monthly-summary")
        assert response.status_code == 401


class TestSpendingTrends:

    def test_trends_with_data(self, auth_client):
        today = date.today()
        auth_client.post("/api/transactions", json={
            "amount": 100, "description": "Food this month",
            "category_id": 1, "type": "expense",
            "date": today.isoformat()
        })

        response = auth_client.get("/api/analytics/trends")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["trends"]) >= 1
        assert data["biggest_change"] is not None

    def test_trends_empty(self, auth_client):
        response = auth_client.get("/api/analytics/trends")
        assert response.status_code == 200
        data = response.get_json()
        assert data["trends"] == []
        assert data["biggest_change"] is None

    def test_trends_without_auth(self, client):
        response = client.get("/api/analytics/trends")
        assert response.status_code == 401