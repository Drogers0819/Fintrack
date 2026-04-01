class TestFactFind:

    def test_submit_factfind(self, auth_client):
        response = auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1700,
            "rent_amount": 800,
            "bills_amount": 150,
            "income_day": 25
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["profile"]["monthly_income"] == 1700
        assert data["profile"]["rent_amount"] == 800
        assert data["profile"]["bills_amount"] == 150
        assert data["profile"]["fixed_commitments"] == 950
        assert data["profile"]["monthly_surplus"] == 750
        assert data["profile"]["factfind_completed"] is True

    def test_get_factfind(self, auth_client):
        auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1700,
            "rent_amount": 800,
            "bills_amount": 150
        })

        response = auth_client.get("/api/profile/factfind")
        assert response.status_code == 200
        assert response.get_json()["profile"]["monthly_income"] == 1700

    def test_submit_factfind_invalid_income(self, auth_client):
        response = auth_client.post("/api/profile/factfind", json={
            "monthly_income": -500,
            "rent_amount": 800
        })
        assert response.status_code == 400

    def test_submit_factfind_no_data(self, auth_client):
        response = auth_client.post("/api/profile/factfind", json={})
        assert response.status_code == 400

    def test_factfind_without_auth(self, client):
        response = client.post("/api/profile/factfind", json={
            "monthly_income": 1700
        })
        assert response.status_code == 401


class TestWaterfall:

    def test_waterfall_with_goals(self, auth_client):
        auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1700,
            "rent_amount": 800,
            "bills_amount": 0
        })

        auth_client.post("/api/goals", json={
            "name": "House deposit",
            "type": "savings_target",
            "target_amount": 10000,
            "current_amount": 2400,
            "monthly_allocation": 412,
            "priority_rank": 1
        })

        auth_client.post("/api/goals", json={
            "name": "Eating out",
            "type": "spending_allocation",
            "monthly_allocation": 100,
            "priority_rank": 2
        })

        response = auth_client.get("/api/profile/waterfall")
        assert response.status_code == 200
        data = response.get_json()
        assert data["surplus"] == 900
        assert len(data["allocations"]) == 2
        assert data["allocations"][0]["allocated"] == 412
        assert data["allocations"][1]["allocated"] == 100

    def test_waterfall_without_factfind(self, auth_client):
        response = auth_client.get("/api/profile/waterfall")
        assert response.status_code == 400
        assert response.get_json()["factfind_completed"] is False

    def test_waterfall_without_auth(self, client):
        response = client.get("/api/profile/waterfall")
        assert response.status_code == 401

    def test_waterfall_with_conflicts(self, auth_client):
        auth_client.post("/api/profile/factfind", json={
            "monthly_income": 1000,
            "rent_amount": 800,
            "bills_amount": 0
        })

        auth_client.post("/api/goals", json={
            "name": "Big goal",
            "type": "savings_target",
            "target_amount": 50000,
            "monthly_allocation": 300,
            "priority_rank": 1
        })

        response = auth_client.get("/api/profile/waterfall")
        assert response.status_code == 200
        data = response.get_json()
        assert data["has_conflicts"] is True
