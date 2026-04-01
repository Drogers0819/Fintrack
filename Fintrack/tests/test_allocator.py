from app.services.allocator_service import calculate_waterfall, detect_conflicts, generate_waterfall_summary


class TestCalculateWaterfall:

    def test_basic_allocation(self):
        goals = [
            {"id": 1, "name": "House deposit", "type": "savings_target",
             "target_amount": 10000, "current_amount": 2400,
             "monthly_allocation": 412, "priority_rank": 1},
            {"id": 2, "name": "Holiday", "type": "savings_target",
             "target_amount": 1500, "current_amount": 340,
             "monthly_allocation": 188, "priority_rank": 2},
        ]

        result = calculate_waterfall(1700, 800, goals)

        assert result["surplus"] == 900
        assert result["allocations"][0]["allocated"] == 412
        assert result["allocations"][1]["allocated"] == 188
        assert result["unallocated"] == 300

    def test_full_sarah_scenario(self):
        goals = [
            {"id": 1, "name": "House deposit", "type": "savings_target",
             "target_amount": 10000, "current_amount": 2400,
             "monthly_allocation": 412, "priority_rank": 1},
            {"id": 2, "name": "Holiday", "type": "savings_target",
             "target_amount": 1500, "current_amount": 340,
             "monthly_allocation": 188, "priority_rank": 2},
            {"id": 3, "name": "Eating out", "type": "spending_allocation",
             "monthly_allocation": 100, "priority_rank": 3},
            {"id": 4, "name": "Emergency fund", "type": "accumulation",
             "target_amount": 2400, "current_amount": 400,
             "monthly_allocation": 200, "priority_rank": 4},
        ]

        result = calculate_waterfall(1700, 800, goals)

        assert result["surplus"] == 900
        assert result["total_income"] == 1700
        assert result["total_commitments"] == 800
        assert result["fully_allocated"]

        total_allocated = sum(a["allocated"] for a in result["allocations"])
        assert total_allocated == 900

    def test_insufficient_surplus(self):
        goals = [
            {"id": 1, "name": "Big goal", "type": "savings_target",
             "target_amount": 50000, "monthly_allocation": 800,
             "priority_rank": 1},
            {"id": 2, "name": "Another goal", "type": "savings_target",
             "target_amount": 10000, "monthly_allocation": 500,
             "priority_rank": 2},
        ]

        result = calculate_waterfall(1700, 800, goals)

        assert result["allocations"][0]["allocated"] == 800
        assert result["allocations"][1]["allocated"] == 100
        assert result["allocations"][1]["status"] == "partially_funded"

    def test_no_income(self):
        result = calculate_waterfall(0, 800, [])
        assert "error" in result

    def test_commitments_exceed_income(self):
        result = calculate_waterfall(500, 800, [])
        assert "error" in result
        assert result["surplus"] == -300

    def test_goal_without_allocation_gets_remainder(self):
        goals = [
            {"id": 1, "name": "Eating out", "type": "spending_allocation",
             "monthly_allocation": 100, "priority_rank": 1},
            {"id": 2, "name": "House deposit", "type": "savings_target",
             "target_amount": 10000, "current_amount": 0,
             "monthly_allocation": 0, "priority_rank": 2},
        ]

        result = calculate_waterfall(1700, 800, goals)

        assert result["allocations"][0]["allocated"] == 100
        assert result["allocations"][1]["allocated"] == 800

    def test_projection_calculation(self):
        goals = [
            {"id": 1, "name": "Savings", "type": "savings_target",
             "target_amount": 1000, "current_amount": 0,
             "monthly_allocation": 100, "priority_rank": 1},
        ]

        result = calculate_waterfall(1000, 500, goals)

        projection = result["allocations"][0]["projection"]
        assert projection is not None
        assert projection["months_to_target"] == 10
        assert projection["remaining_amount"] == 1000

    def test_already_completed_goal(self):
        goals = [
            {"id": 1, "name": "Done", "type": "savings_target",
             "target_amount": 1000, "current_amount": 1000,
             "monthly_allocation": 100, "priority_rank": 1},
        ]

        result = calculate_waterfall(1700, 800, goals)

        projection = result["allocations"][0]["projection"]
        assert projection["months_to_target"] == 0

    def test_empty_goals(self):
        result = calculate_waterfall(1700, 800, [])

        assert result["surplus"] == 900
        assert result["unallocated"] == 900
        assert result["allocations"] == []


class TestDetectConflicts:

    def test_no_conflicts(self):
        allocations = [
            {"goal_id": 1, "goal_name": "Test", "status": "funded",
             "requested": 100, "allocated": 100}
        ]
        conflicts = detect_conflicts(allocations)
        assert len(conflicts) == 0

    def test_unfunded_conflict(self):
        allocations = [
            {"goal_id": 1, "goal_name": "Unfunded goal", "status": "unfunded",
             "requested": 500, "allocated": 0}
        ]
        conflicts = detect_conflicts(allocations)
        assert len(conflicts) == 1
        assert conflicts[0]["severity"] == "high"

    def test_partial_funding_conflict(self):
        allocations = [
            {"goal_id": 1, "goal_name": "Partial goal", "status": "partially_funded",
             "requested": 500, "allocated": 300}
        ]
        conflicts = detect_conflicts(allocations)
        assert len(conflicts) == 1
        assert conflicts[0]["severity"] == "medium"