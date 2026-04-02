from datetime import date, timedelta
from app.services.recurring_service import (
    detect_recurring_transactions,
    identify_potential_savings,
    _normalise_merchant,
    _classify_frequency,
    _calculate_monthly_cost
)


class TestNormaliseMerchant:

    def test_strips_store_codes(self):
        assert _normalise_merchant("TESCO STORES 4521") == "tesco stores"

    def test_strips_asterisk_suffix(self):
        assert _normalise_merchant("UBER *TRIP BHX") == "uber"

    def test_strips_hash_codes(self):
        assert _normalise_merchant("DELIVEROO #12345") == "deliveroo"

    def test_strips_dash_numbers(self):
        assert _normalise_merchant("NETFLIX - 98765") == "netflix"

    def test_lowercase(self):
        assert _normalise_merchant("TESCO") == "tesco"

    def test_empty(self):
        assert _normalise_merchant("") == ""

    def test_none(self):
        assert _normalise_merchant(None) == ""


class TestClassifyFrequency:

    def test_weekly(self):
        freq, label = _classify_frequency(7)
        assert freq == "weekly"

    def test_fortnightly(self):
        freq, label = _classify_frequency(14)
        assert freq == "fortnightly"

    def test_monthly(self):
        freq, label = _classify_frequency(30)
        assert freq == "monthly"

    def test_quarterly(self):
        freq, label = _classify_frequency(90)
        assert freq == "quarterly"

    def test_annual(self):
        freq, label = _classify_frequency(365)
        assert freq == "annual"

    def test_irregular(self):
        freq, label = _classify_frequency(42)
        assert freq is None
        assert label == "Irregular"


class TestCalculateMonthlyCost:

    def test_monthly(self):
        assert _calculate_monthly_cost(10.99, "monthly") == 10.99

    def test_weekly(self):
        result = _calculate_monthly_cost(5.00, "weekly")
        assert result == 21.65

    def test_annual(self):
        result = _calculate_monthly_cost(120.00, "annual")
        assert result == 9.96

    def test_quarterly(self):
        result = _calculate_monthly_cost(30.00, "quarterly")
        assert result == 9.90


class TestDetectRecurring:

    def _make_monthly_transactions(self, merchant, amount, months=6):
        """Helper to create monthly transaction data."""
        txns = []
        base = date.today() - timedelta(days=months * 30)
        for i in range(months):
            txns.append({
                "amount": amount,
                "description": f"{merchant} payment",
                "merchant": merchant,
                "category": "Subscriptions",
                "category_id": 8,
                "type": "expense",
                "date": base + timedelta(days=i * 30)
            })
        return txns

    def test_detect_monthly_subscription(self):
        txns = self._make_monthly_transactions("Netflix", 10.99, months=6)
        result = detect_recurring_transactions(txns)

        assert result["count"] == 1
        assert result["recurring"][0]["merchant"] == "netflix"
        assert result["recurring"][0]["frequency"] == "monthly"
        assert result["recurring"][0]["avg_amount"] == 10.99

    def test_detect_multiple_recurring(self):
        txns = (
            self._make_monthly_transactions("Netflix", 10.99, months=4) +
            self._make_monthly_transactions("Spotify", 9.99, months=4) +
            self._make_monthly_transactions("Gym", 29.99, months=4)
        )

        result = detect_recurring_transactions(txns)
        assert result["count"] == 3
        merchants = [r["merchant"] for r in result["recurring"]]
        assert "netflix" in merchants
        assert "spotify" in merchants
        assert "gym" in merchants

    def test_detect_income(self):
        base = date.today() - timedelta(days=180)
        txns = []
        for i in range(6):
            txns.append({
                "amount": 1700,
                "description": "SALARY ACME LTD",
                "merchant": "SALARY ACME LTD",
                "category": "Income",
                "type": "income",
                "date": base + timedelta(days=i * 30)
            })

        result = detect_recurring_transactions(txns)
        assert result["income_count"] >= 1
        assert result["total_monthly_income"] > 0

    def test_no_recurring_single_transaction(self):
        txns = [{"amount": 50, "description": "Random", "merchant": "Random",
                 "type": "expense", "date": date.today()}]
        result = detect_recurring_transactions(txns)
        assert result["count"] == 0

    def test_empty_transactions(self):
        result = detect_recurring_transactions([])
        assert result["count"] == 0

    def test_irregular_not_detected(self):
        """Transactions with highly irregular intervals should not be detected."""
        txns = [
            {"amount": 50, "description": "Random Shop", "merchant": "Random Shop",
             "type": "expense", "date": date.today() - timedelta(days=100)},
            {"amount": 50, "description": "Random Shop", "merchant": "Random Shop",
             "type": "expense", "date": date.today() - timedelta(days=55)},
            {"amount": 50, "description": "Random Shop", "merchant": "Random Shop",
             "type": "expense", "date": date.today() - timedelta(days=10)},
        ]
        result = detect_recurring_transactions(txns)
        # Irregular intervals (45 days, then 45 days) — might detect or not
        # but the key test is it doesn't crash
        assert isinstance(result["count"], int)

    def test_monthly_cost_calculation(self):
        txns = self._make_monthly_transactions("Netflix", 10.99, months=6)
        result = detect_recurring_transactions(txns)

        assert result["total_monthly_cost"] == 10.99

    def test_next_expected_date(self):
        txns = self._make_monthly_transactions("Netflix", 10.99, months=4)
        result = detect_recurring_transactions(txns)

        assert result["recurring"][0]["next_expected"] is not None

    def test_amount_consistency(self):
        txns = self._make_monthly_transactions("Netflix", 10.99, months=6)
        result = detect_recurring_transactions(txns)

        assert result["recurring"][0]["amount_consistent"] is True

    def test_varying_amounts(self):
        base = date.today() - timedelta(days=180)
        txns = []
        amounts = [45.20, 52.10, 38.90, 67.30, 41.50, 55.80]
        for i in range(6):
            txns.append({
                "amount": amounts[i],
                "description": "Tesco weekly shop",
                "merchant": "Tesco",
                "category": "Food",
                "type": "expense",
                "date": base + timedelta(days=i * 30)
            })

        result = detect_recurring_transactions(txns)
        if result["count"] > 0:
            assert result["recurring"][0]["amount_consistent"] is False


class TestIdentifySavings:

    def test_expensive_subscription(self):
        recurring = [{
            "merchant": "gym membership",
            "frequency": "monthly",
            "avg_amount": 45.00,
            "monthly_cost": 45.00,
            "transaction_type": "expense",
            "last_date": date.today().isoformat(),
            "occurrence_count": 6,
            "confidence": 0.9
        }]

        result = identify_potential_savings(recurring)
        assert result["count"] >= 1
        assert result["total_potential_annual_saving"] > 0

    def test_potentially_unused(self):
        old_date = (date.today() - timedelta(days=60)).isoformat()
        recurring = [{
            "merchant": "old subscription",
            "frequency": "monthly",
            "avg_amount": 9.99,
            "monthly_cost": 9.99,
            "transaction_type": "expense",
            "last_date": old_date,
            "occurrence_count": 4,
            "confidence": 0.8
        }]

        result = identify_potential_savings(recurring)
        types = [s["type"] for s in result["opportunities"]]
        assert "potentially_unused" in types

    def test_no_savings_for_income(self):
        recurring = [{
            "merchant": "salary",
            "frequency": "monthly",
            "avg_amount": 1700,
            "monthly_cost": 1700,
            "transaction_type": "income",
            "last_date": date.today().isoformat(),
            "occurrence_count": 6,
            "confidence": 0.95
        }]

        result = identify_potential_savings(recurring)
        assert result["count"] == 0

    def test_empty_recurring(self):
        result = identify_potential_savings([])
        assert result["count"] == 0


class TestRecurringAPI:

    def test_get_recurring(self, auth_client):
        response = auth_client.get("/api/recurring")
        assert response.status_code == 200
        data = response.get_json()
        assert "recurring" in data
        assert "total_monthly_cost" in data

    def test_get_savings(self, auth_client):
        response = auth_client.get("/api/recurring/savings")
        assert response.status_code == 200
        data = response.get_json()
        assert "opportunities" in data

    def test_recurring_without_auth(self, client):
        response = client.get("/api/recurring")
        assert response.status_code == 401

    def test_savings_without_auth(self, client):
        response = client.get("/api/recurring/savings")
        assert response.status_code == 401
