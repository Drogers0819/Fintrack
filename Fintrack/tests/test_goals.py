class TestCreateGoal:

    def test_create_savings_goal(self, auth_client):
        response = auth_client.post("/api/goals", json={
            "name": "Manchester house deposit",
            "type": "savings_target",
            "target_amount": 10000,
            "current_amount": 2400,
            "monthly_allocation": 412,
            "deadline": "2028-12-01",
            "priority_rank": 1
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["goal"]["name"] == "Manchester house deposit"
        assert data["goal"]["type"] == "savings_target"
        assert data["goal"]["target_amount"] == 10000
        assert data["goal"]["current_amount"] == 2400
        assert data["goal"]["progress_percent"] == 24.0
        assert data["goal"]["status"] == "active"

    def test_create_spending_allocation(self, auth_client):
        response = auth_client.post("/api/goals", json={
            "name": "Eating out budget",
            "type": "spending_allocation",
            "monthly_allocation": 100
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data["goal"]["target_amount"] is None
        assert data["goal"]["progress_percent"] is None

    def test_create_accumulation_goal(self, auth_client):
        response = auth_client.post("/api/goals", json={
            "name": "Emergency fund",
            "type": "accumulation",
            "target_amount": 2400,
            "monthly_allocation": 200
        })
        assert response.status_code == 201

    def test_create_goal_missing_name(self, auth_client):
        response = auth_client.post("/api/goals", json={
            "type": "savings_target",
            "target_amount": 5000
        })
        assert response.status_code == 400

    def test_create_goal_invalid_type(self, auth_client):
        response = auth_client.post("/api/goals", json={
            "name": "Test goal",
            "type": "invalid_type"
        })
        assert response.status_code == 400

    def test_create_goal_negative_target(self, auth_client):
        response = auth_client.post("/api/goals", json={
            "name": "Test goal",
            "type": "savings_target",
            "target_amount": -5000
        })
        assert response.status_code == 400

    def test_create_goal_without_auth(self, client):
        response = client.post("/api/goals", json={
            "name": "Test",
            "type": "savings_target"
        })
        assert response.status_code == 401


class TestListGoals:

    def test_list_goals_empty(self, auth_client):
        response = auth_client.get("/api/goals")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0

    def test_list_goals_with_data(self, auth_client):
        auth_client.post("/api/goals", json={
            "name": "Goal 1", "type": "savings_target",
            "target_amount": 5000, "priority_rank": 2
        })
        auth_client.post("/api/goals", json={
            "name": "Goal 2", "type": "accumulation",
            "priority_rank": 1
        })

        response = auth_client.get("/api/goals")
        data = response.get_json()
        assert data["count"] == 2
        assert data["goals"][0]["name"] == "Goal 2"
        assert data["goals"][1]["name"] == "Goal 1"

    def test_list_goals_filter_status(self, auth_client):
        auth_client.post("/api/goals", json={
            "name": "Active goal", "type": "savings_target",
            "target_amount": 5000
        })

        response = auth_client.get("/api/goals?status=completed")
        data = response.get_json()
        assert data["count"] == 0

        response = auth_client.get("/api/goals?status=all")
        data = response.get_json()
        assert data["count"] == 1

    def test_list_goals_without_auth(self, client):
        response = client.get("/api/goals")
        assert response.status_code == 401


class TestGetGoal:

    def test_get_goal_success(self, auth_client):
        create_response = auth_client.post("/api/goals", json={
            "name": "Test goal", "type": "savings_target",
            "target_amount": 5000
        })
        goal_id = create_response.get_json()["goal"]["id"]

        response = auth_client.get(f"/api/goals/{goal_id}")
        assert response.status_code == 200
        assert response.get_json()["goal"]["name"] == "Test goal"

    def test_get_goal_not_found(self, auth_client):
        response = auth_client.get("/api/goals/9999")
        assert response.status_code == 404


class TestUpdateGoal:

    def test_update_goal_name(self, auth_client):
        create_response = auth_client.post("/api/goals", json={
            "name": "Old name", "type": "savings_target",
            "target_amount": 5000
        })
        goal_id = create_response.get_json()["goal"]["id"]

        response = auth_client.put(f"/api/goals/{goal_id}", json={
            "name": "New name"
        })
        assert response.status_code == 200
        assert response.get_json()["goal"]["name"] == "New name"
        assert response.get_json()["goal"]["target_amount"] == 5000

    def test_update_goal_progress(self, auth_client):
        create_response = auth_client.post("/api/goals", json={
            "name": "Savings", "type": "savings_target",
            "target_amount": 10000, "current_amount": 2000
        })
        goal_id = create_response.get_json()["goal"]["id"]

        response = auth_client.put(f"/api/goals/{goal_id}", json={
            "current_amount": 5000
        })
        assert response.status_code == 200
        assert response.get_json()["goal"]["current_amount"] == 5000
        assert response.get_json()["goal"]["progress_percent"] == 50.0

    def test_update_goal_status_completed(self, auth_client):
        create_response = auth_client.post("/api/goals", json={
            "name": "Quick goal", "type": "savings_target",
            "target_amount": 100
        })
        goal_id = create_response.get_json()["goal"]["id"]

        response = auth_client.put(f"/api/goals/{goal_id}", json={
            "status": "completed",
            "current_amount": 100
        })
        assert response.status_code == 200
        assert response.get_json()["goal"]["status"] == "completed"
        assert response.get_json()["goal"]["progress_percent"] == 100.0

    def test_update_goal_invalid_status(self, auth_client):
        create_response = auth_client.post("/api/goals", json={
            "name": "Test", "type": "savings_target",
            "target_amount": 5000
        })
        goal_id = create_response.get_json()["goal"]["id"]

        response = auth_client.put(f"/api/goals/{goal_id}", json={
            "status": "invalid"
        })
        assert response.status_code == 400

    def test_update_goal_not_found(self, auth_client):
        response = auth_client.put("/api/goals/9999", json={
            "name": "Updated"
        })
        assert response.status_code == 404


class TestDeleteGoal:

    def test_delete_goal_success(self, auth_client):
        create_response = auth_client.post("/api/goals", json={
            "name": "To delete", "type": "savings_target",
            "target_amount": 1000
        })
        goal_id = create_response.get_json()["goal"]["id"]

        delete_response = auth_client.delete(f"/api/goals/{goal_id}")
        assert delete_response.status_code == 200

        get_response = auth_client.get(f"/api/goals/{goal_id}")
        assert get_response.status_code == 404

    def test_delete_goal_not_found(self, auth_client):
        response = auth_client.delete("/api/goals/9999")
        assert response.status_code == 404