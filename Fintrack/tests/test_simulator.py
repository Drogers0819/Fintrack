from app.services.simulator_service import (
    project_goal_timeline,
    calculate_cost_of_habit,
    simulate_scenario,
    generate_multi_horizon_projection,
    GROWTH_RATES
)


class TestProjectGoalTimeline:

    def test_basic_projection(self):
        goal = {"target_amount": 10000, "current_amount": 0}
        result = project_goal_timeline(goal, 500, growth_rate=0)

        assert result["reachable"] is True
        assert result["months_to_target"] == 20
        assert result["total_contributed"] == 10000

    def test_projection_with_existing_savings(self):
        goal = {"target_amount": 10000, "current_amount": 5000}
        result = project_goal_timeline(goal, 500, growth_rate=0)

        assert result["reachable"] is True
        assert result["months_to_target"] == 10

    def test_projection_with_compound_growth(self):
        goal = {"target_amount": 10000, "current_amount": 0}
        result_no_growth = project_goal_timeline(goal, 412, growth_rate=0)
        result_with_growth = project_goal_timeline(goal, 412, growth_rate=0.04)

        assert result_with_growth["months_to_target"] < result_no_growth["months_to_target"]
        assert result_with_growth["total_interest_earned"] > 0

    def test_projection_milestones(self):
        goal = {"target_amount": 10000, "current_amount": 0}
        result = project_goal_timeline(goal, 500, growth_rate=0)

        milestones = result["milestones"]
        assert len(milestones) == 4
        assert milestones[0]["percent"] == 25
        assert milestones[1]["percent"] == 50
        assert milestones[2]["percent"] == 75
        assert milestones[3]["percent"] == 100

    def test_projection_completion_date_human(self):
        goal = {"target_amount": 1000, "current_amount": 0}
        result = project_goal_timeline(goal, 500, growth_rate=0)

        assert result["completion_date_human"] is not None
        assert len(result["completion_date_human"]) > 0

    def test_unreachable_no_contribution(self):
        goal = {"target_amount": 10000, "current_amount": 500}
        result = project_goal_timeline(goal, 0)

        assert result["reachable"] is False

    def test_zero_target(self):
        goal = {"target_amount": 0, "current_amount": 0}
        result = project_goal_timeline(goal, 500)

        assert result["reachable"] is False

    def test_already_reached(self):
        goal = {"target_amount": 1000, "current_amount": 1000}
        result = project_goal_timeline(goal, 100, growth_rate=0)

        assert result["reachable"] is True
        assert result["months_to_target"] == 0

    def test_sarah_house_deposit(self):
        goal = {"target_amount": 10000, "current_amount": 2400}
        result = project_goal_timeline(goal, 412, growth_rate=0.04)

        assert result["reachable"] is True
        assert result["months_to_target"] < 24
        assert result["total_interest_earned"] > 0
        assert "completion_date_human" in result

    def test_monthly_projections_included(self):
        goal = {"target_amount": 5000, "current_amount": 0}
        result = project_goal_timeline(goal, 500, growth_rate=0)

        assert len(result["monthly_projections"]) == 10
        assert result["monthly_projections"][0]["month"] == 1
        assert result["monthly_projections"][-1]["month"] == 10


class TestCostOfHabit:

    def test_deliveroo_habit(self):
        result = calculate_cost_of_habit(340)

        assert "5_year" in result["horizons"]
        assert "10_year" in result["horizons"]
        assert "20_year" in result["horizons"]

        ten_year = result["horizons"]["10_year"]
        assert ten_year["simple_cost"] == 40800
        assert ten_year["opportunity_cost"] > 40800
        assert ten_year["lost_growth"] > 0

    def test_small_daily_habit(self):
        result = calculate_cost_of_habit(120)

        five_year = result["horizons"]["5_year"]
        assert five_year["simple_cost"] == 7200
        assert five_year["opportunity_cost"] > 7200

    def test_insight_generation(self):
        result = calculate_cost_of_habit(340)

        assert result["insight"] is not None
        assert "headline" in result["insight"]
        assert "detail" in result["insight"]
        assert "reframe" in result["insight"]
        assert "340" in result["insight"]["headline"]

    def test_zero_spend(self):
        result = calculate_cost_of_habit(0)
        assert "error" in result

    def test_compound_growth_matters(self):
        result_low = calculate_cost_of_habit(340, growth_rate=0.02)
        result_high = calculate_cost_of_habit(340, growth_rate=0.06)

        low_10yr = result_low["horizons"]["10_year"]["opportunity_cost"]
        high_10yr = result_high["horizons"]["10_year"]["opportunity_cost"]

        assert high_10yr > low_10yr


class TestSimulateScenario:

    def test_basic_scenario(self):
        current_state = {
            "monthly_income": 1700,
            "fixed_commitments": 800,
            "goals": [
                {"id": 1, "name": "House deposit", "type": "savings_target",
                 "target_amount": 10000, "current_amount": 2400,
                 "monthly_allocation": 412},
                {"id": 2, "name": "Holiday", "type": "savings_target",
                 "target_amount": 1500, "current_amount": 340,
                 "monthly_allocation": 188}
            ]
        }

        proposed_changes = {
            "spending_changes": {"1": 512}
        }

        result = simulate_scenario(current_state, proposed_changes)

        assert len(result["comparison"]) == 2
        house = result["comparison"][0]
        assert house["proposed_allocation"] == 512
        assert house["months_saved"] > 0

    def test_scenario_with_trade_off(self):
        current_state = {
            "monthly_income": 1700,
            "fixed_commitments": 800,
            "goals": [
                {"id": 1, "name": "House deposit", "type": "savings_target",
                 "target_amount": 10000, "current_amount": 2400,
                 "monthly_allocation": 412},
                {"id": 2, "name": "Holiday", "type": "savings_target",
                 "target_amount": 1500, "current_amount": 340,
                 "monthly_allocation": 188}
            ]
        }

        proposed_changes = {
            "spending_changes": {"1": 512, "2": 88}
        }

        result = simulate_scenario(current_state, proposed_changes)

        house = result["comparison"][0]
        holiday = result["comparison"][1]

        assert house["months_saved"] > 0
        assert holiday["months_saved"] < 0

        assert result["summary"]["goals_accelerated"] >= 1
        assert result["summary"]["goals_delayed"] >= 1

    def test_scenario_insight_generated(self):
        current_state = {
            "monthly_income": 1700,
            "fixed_commitments": 800,
            "goals": [
                {"id": 1, "name": "House deposit", "type": "savings_target",
                 "target_amount": 10000, "current_amount": 2400,
                 "monthly_allocation": 412}
            ]
        }

        proposed_changes = {
            "spending_changes": {"1": 600}
        }

        result = simulate_scenario(current_state, proposed_changes)

        assert result["summary"]["net_insight"] is not None
        assert len(result["summary"]["net_insight"]) > 0

    def test_rent_increase_scenario(self):
        current_state = {
            "monthly_income": 1700,
            "fixed_commitments": 800,
            "goals": [
                {"id": 1, "name": "House deposit", "type": "savings_target",
                 "target_amount": 10000, "current_amount": 2400,
                 "monthly_allocation": 412}
            ]
        }

        proposed_changes = {
            "fixed_commitments": 950
        }

        result = simulate_scenario(current_state, proposed_changes)

        assert result["summary"]["proposed_surplus"] == 750
        assert result["summary"]["surplus_change"] == -150


class TestMultiHorizonProjection:

    def test_three_horizons(self):
        goal = {"target_amount": 100000, "current_amount": 0}
        result = generate_multi_horizon_projection(goal, 500)

        assert "5_year" in result
        assert "10_year" in result
        assert "20_year" in result

    def test_three_scenarios_per_horizon(self):
        goal = {"target_amount": 100000, "current_amount": 0}
        result = generate_multi_horizon_projection(goal, 500)

        for horizon in ["5_year", "10_year", "20_year"]:
            assert "conservative" in result[horizon]
            assert "moderate" in result[horizon]
            assert "optimistic" in result[horizon]

    def test_optimistic_beats_conservative(self):
        goal = {"target_amount": 100000, "current_amount": 0}
        result = generate_multi_horizon_projection(goal, 500)

        conservative = result["10_year"]["conservative"]["final_balance"]
        optimistic = result["10_year"]["optimistic"]["final_balance"]

        assert optimistic > conservative

    def test_interest_earned_increases_with_time(self):
        goal = {"target_amount": 100000, "current_amount": 0}
        result = generate_multi_horizon_projection(goal, 500)

        interest_5 = result["5_year"]["moderate"]["interest_earned"]
        interest_10 = result["10_year"]["moderate"]["interest_earned"]
        interest_20 = result["20_year"]["moderate"]["interest_earned"]

        assert interest_10 > interest_5
        assert interest_20 > interest_10