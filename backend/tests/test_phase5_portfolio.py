"""
Phase 5 - Feature 13: Portfolio Analytics
Tests for GET /api/portfolio/summary endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def compliance_session():
    """Authenticated session for compliance role."""
    s = requests.Session()
    resp = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": "compliance@zephyrwealth.ai",
        "password": "Comply1234!"
    })
    if resp.status_code != 200:
        pytest.skip(f"Compliance login failed: {resp.status_code} {resp.text}")
    return s


@pytest.fixture(scope="module")
def risk_session():
    """Authenticated session for risk role."""
    s = requests.Session()
    resp = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": "risk@zephyrwealth.ai",
        "password": "Risk1234!"
    })
    if resp.status_code != 200:
        pytest.skip(f"Risk login failed: {resp.status_code} {resp.text}")
    return s


@pytest.fixture(scope="module")
def manager_session():
    """Authenticated session for manager role."""
    s = requests.Session()
    resp = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": "manager@zephyrwealth.ai",
        "password": "Manager1234!"
    })
    if resp.status_code != 200:
        pytest.skip(f"Manager login failed: {resp.status_code} {resp.text}")
    return s


# ---------------------------------------------------------------------------
# Section 1: API Status & Auth
# ---------------------------------------------------------------------------

class TestPortfolioSummaryAccess:
    """GET /api/portfolio/summary — accessibility for all 3 roles"""

    def test_compliance_can_access_portfolio_summary(self, compliance_session):
        """Compliance role can access portfolio summary"""
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: compliance can access /api/portfolio/summary")

    def test_risk_can_access_portfolio_summary(self, risk_session):
        """Risk role can access portfolio summary"""
        resp = risk_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: risk can access /api/portfolio/summary")

    def test_manager_can_access_portfolio_summary(self, manager_session):
        """Manager role can access portfolio summary"""
        resp = manager_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print("PASS: manager can access /api/portfolio/summary")

    def test_unauthenticated_cannot_access_portfolio_summary(self):
        """Unauthenticated requests should be rejected (401)"""
        resp = requests.get(f"{BASE_URL}/api/portfolio/summary")
        assert resp.status_code == 401, f"Expected 401 for unauth, got {resp.status_code}"
        print("PASS: unauthenticated blocked from /api/portfolio/summary")


# ---------------------------------------------------------------------------
# Section 2: Response Structure & KPI Fields
# ---------------------------------------------------------------------------

class TestPortfolioSummaryKPIs:
    """Validate KPI fields in /api/portfolio/summary response"""

    @pytest.fixture(scope="class")
    def summary(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert resp.status_code == 200
        return resp.json()

    def test_response_has_kpis_key(self, summary):
        assert "kpis" in summary, "Response missing 'kpis' key"
        print("PASS: response has 'kpis' key")

    def test_kpis_has_total_portfolio_value(self, summary):
        kpis = summary["kpis"]
        assert "total_portfolio_value" in kpis, "KPIs missing total_portfolio_value"
        assert isinstance(kpis["total_portfolio_value"], (int, float)), "total_portfolio_value must be numeric"
        assert kpis["total_portfolio_value"] >= 0
        print(f"PASS: total_portfolio_value = {kpis['total_portfolio_value']}")

    def test_kpis_has_active_investments(self, summary):
        kpis = summary["kpis"]
        assert "active_investments" in kpis, "KPIs missing active_investments"
        assert isinstance(kpis["active_investments"], int), "active_investments must be integer"
        assert kpis["active_investments"] >= 0
        print(f"PASS: active_investments = {kpis['active_investments']}")

    def test_kpis_has_weighted_avg_irr(self, summary):
        kpis = summary["kpis"]
        assert "weighted_avg_irr" in kpis, "KPIs missing weighted_avg_irr"
        assert isinstance(kpis["weighted_avg_irr"], (int, float)), "weighted_avg_irr must be numeric"
        print(f"PASS: weighted_avg_irr = {kpis['weighted_avg_irr']}")

    def test_kpis_has_mandate_exception_rate(self, summary):
        kpis = summary["kpis"]
        assert "mandate_exception_rate" in kpis, "KPIs missing mandate_exception_rate"
        assert isinstance(kpis["mandate_exception_rate"], (int, float)), "mandate_exception_rate must be numeric"
        assert 0 <= kpis["mandate_exception_rate"] <= 100
        print(f"PASS: mandate_exception_rate = {kpis['mandate_exception_rate']}")

    def test_kpis_active_investments_counts_ic_review_and_closing(self, summary):
        """active_investments should be count of deals in ic_review or closing stages"""
        kpis = summary["kpis"]
        holdings = summary["holdings"]
        active_in_holdings = sum(1 for h in holdings if h.get("pipeline_stage") in ("ic_review", "closing"))
        assert kpis["active_investments"] == active_in_holdings, (
            f"active_investments={kpis['active_investments']} but holdings count active={active_in_holdings}"
        )
        print(f"PASS: active_investments={kpis['active_investments']} matches holdings ({active_in_holdings} in ic_review/closing)")

    def test_kpis_mandate_exception_rate_calculation(self, summary):
        """mandate_exception_rate = (exception_deals / total_deals) * 100"""
        kpis = summary["kpis"]
        holdings = summary["holdings"]
        total = len(holdings)
        exceptions = sum(1 for h in holdings if h.get("mandate_status") == "Exception")
        expected_rate = round((exceptions / total * 100) if total > 0 else 0, 1)
        assert kpis["mandate_exception_rate"] == expected_rate, (
            f"mandate_exception_rate={kpis['mandate_exception_rate']} but expected {expected_rate}"
        )
        print(f"PASS: mandate_exception_rate={kpis['mandate_exception_rate']} (exceptions={exceptions}/{total})")


# ---------------------------------------------------------------------------
# Section 3: Chart Data
# ---------------------------------------------------------------------------

class TestPortfolioSummaryCharts:
    """Validate chart data in /api/portfolio/summary response"""

    @pytest.fixture(scope="class")
    def summary(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert resp.status_code == 200
        return resp.json()

    def test_response_has_charts_key(self, summary):
        assert "charts" in summary, "Response missing 'charts' key"
        print("PASS: response has 'charts' key")

    def test_charts_has_sector_allocation(self, summary):
        charts = summary["charts"]
        assert "sector_allocation" in charts, "Charts missing sector_allocation"
        assert isinstance(charts["sector_allocation"], list)
        print(f"PASS: sector_allocation has {len(charts['sector_allocation'])} entries")

    def test_sector_allocation_has_correct_fields(self, summary):
        sectors = summary["charts"]["sector_allocation"]
        if sectors:
            s = sectors[0]
            assert "name" in s, "sector_allocation entry missing 'name'"
            assert "value" in s, "sector_allocation entry missing 'value'"
            assert "count" in s, "sector_allocation entry missing 'count'"
            print(f"PASS: sector_allocation[0] has name={s['name']}, value={s['value']}, count={s['count']}")

    def test_charts_has_geography_allocation(self, summary):
        charts = summary["charts"]
        assert "geography_allocation" in charts, "Charts missing geography_allocation"
        assert isinstance(charts["geography_allocation"], list)
        print(f"PASS: geography_allocation has {len(charts['geography_allocation'])} entries")

    def test_geography_allocation_has_correct_fields(self, summary):
        geos = summary["charts"]["geography_allocation"]
        if geos:
            g = geos[0]
            assert "name" in g, "geography_allocation entry missing 'name'"
            assert "value" in g, "geography_allocation entry missing 'value'"
            assert "count" in g, "geography_allocation entry missing 'count'"
            print(f"PASS: geography_allocation[0] has name={g['name']}, value={g['value']}, count={g['count']}")

    def test_charts_has_irr_distribution(self, summary):
        charts = summary["charts"]
        assert "irr_distribution" in charts, "Charts missing irr_distribution"
        assert isinstance(charts["irr_distribution"], list)
        print(f"PASS: irr_distribution has {len(charts['irr_distribution'])} entries")

    def test_irr_distribution_sorted_by_irr_desc(self, summary):
        irr_list = summary["charts"]["irr_distribution"]
        if len(irr_list) > 1:
            irrs = [item["irr"] for item in irr_list]
            assert irrs == sorted(irrs, reverse=True), f"irr_distribution not sorted desc: {irrs}"
        print(f"PASS: irr_distribution sorted by IRR desc")

    def test_irr_distribution_has_correct_fields(self, summary):
        irr_list = summary["charts"]["irr_distribution"]
        if irr_list:
            item = irr_list[0]
            assert "id" in item, "irr_distribution item missing 'id'"
            assert "name" in item, "irr_distribution item missing 'name'"
            assert "irr" in item, "irr_distribution item missing 'irr'"
            assert "valuation" in item, "irr_distribution item missing 'valuation'"
            assert "mandate_status" in item, "irr_distribution item missing 'mandate_status'"
            print(f"PASS: irr_distribution[0] has name={item['name']}, irr={item['irr']}, mandate_status={item['mandate_status']}")

    def test_charts_has_pipeline_stage_value(self, summary):
        charts = summary["charts"]
        assert "pipeline_stage_value" in charts, "Charts missing pipeline_stage_value"
        assert isinstance(charts["pipeline_stage_value"], list)
        print(f"PASS: pipeline_stage_value has {len(charts['pipeline_stage_value'])} entries")

    def test_pipeline_stage_value_has_4_stages(self, summary):
        stages = summary["charts"]["pipeline_stage_value"]
        assert len(stages) == 4, f"Expected 4 pipeline stages, got {len(stages)}"
        stage_keys = {s["key"] for s in stages}
        expected_keys = {"leads", "due_diligence", "ic_review", "closing"}
        assert stage_keys == expected_keys, f"Stage keys mismatch: {stage_keys}"
        print(f"PASS: pipeline_stage_value has all 4 stages: {stage_keys}")

    def test_pipeline_stage_value_has_correct_fields(self, summary):
        stages = summary["charts"]["pipeline_stage_value"]
        if stages:
            s = stages[0]
            assert "stage" in s, "pipeline_stage_value entry missing 'stage'"
            assert "key" in s, "pipeline_stage_value entry missing 'key'"
            assert "value" in s, "pipeline_stage_value entry missing 'value'"
            print(f"PASS: pipeline_stage_value[0] has stage={s['stage']}, key={s['key']}, value={s['value']}")


# ---------------------------------------------------------------------------
# Section 4: Holdings Data
# ---------------------------------------------------------------------------

class TestPortfolioSummaryHoldings:
    """Validate holdings list in /api/portfolio/summary response"""

    @pytest.fixture(scope="class")
    def summary(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert resp.status_code == 200
        return resp.json()

    def test_response_has_holdings_key(self, summary):
        assert "holdings" in summary, "Response missing 'holdings' key"
        assert isinstance(summary["holdings"], list)
        print(f"PASS: holdings list has {len(summary['holdings'])} entries")

    def test_holdings_not_empty(self, summary):
        """Seed data should have at least 5 deals"""
        assert len(summary["holdings"]) >= 5, f"Expected >= 5 holdings, got {len(summary['holdings'])}"
        print(f"PASS: holdings has {len(summary['holdings'])} entries (>=5)")

    def test_holdings_have_all_required_fields(self, summary):
        """Each holding must have all 10 required fields"""
        required_fields = [
            "id", "company_name", "sector", "geography", "entity_type",
            "pipeline_stage", "entry_valuation", "expected_irr", "mandate_status", "health_score"
        ]
        for i, h in enumerate(summary["holdings"]):
            for field in required_fields:
                assert field in h, f"holdings[{i}] missing field '{field}': {h}"
        print(f"PASS: all {len(summary['holdings'])} holdings have required fields")

    def test_holdings_id_is_string(self, summary):
        """id should be a non-empty string"""
        for h in summary["holdings"]:
            assert isinstance(h["id"], str) and h["id"], f"holding id invalid: {h['id']}"
        print("PASS: all holding IDs are non-empty strings")

    def test_holdings_entry_valuation_is_numeric(self, summary):
        for h in summary["holdings"]:
            assert isinstance(h["entry_valuation"], (int, float)), f"entry_valuation not numeric in {h['company_name']}"
        print("PASS: all entry_valuations are numeric")

    def test_holdings_expected_irr_is_numeric(self, summary):
        for h in summary["holdings"]:
            assert isinstance(h["expected_irr"], (int, float)), f"expected_irr not numeric in {h['company_name']}"
        print("PASS: all expected_irrs are numeric")

    def test_holdings_mandate_status_valid_values(self, summary):
        valid = {"In Mandate", "Exception", "Exception Cleared", "Blocked"}
        for h in summary["holdings"]:
            assert h["mandate_status"] in valid, f"Invalid mandate_status '{h['mandate_status']}' in {h['company_name']}"
        print("PASS: all mandate_status values are valid")

    def test_holdings_health_score_valid_values(self, summary):
        valid = {"Good", "Review", "Poor"}
        for h in summary["holdings"]:
            assert h["health_score"] in valid, f"Invalid health_score '{h['health_score']}' in {h['company_name']}"
        print("PASS: all health_score values are valid")

    def test_holdings_pipeline_stage_valid_values(self, summary):
        valid = {"leads", "due_diligence", "ic_review", "closing"}
        for h in summary["holdings"]:
            ps = h["pipeline_stage"]
            assert ps in valid, f"Invalid pipeline_stage '{ps}' in {h['company_name']}"
        print("PASS: all pipeline_stage values are valid")

    def test_holdings_seed_data_caribpay_present(self, summary):
        """CaribPay Solutions Ltd should be in holdings (seed data)"""
        names = [h["company_name"] for h in summary["holdings"]]
        # Check at least one seeded deal exists
        seed_companies = {"CaribPay Solutions Ltd", "AgroHub Africa Ltd", "InsureSync Caribbean ICON",
                          "SaaSAfrica BV", "CariLogix Ltd"}
        found = [n for n in names if n in seed_companies]
        assert len(found) >= 1, f"No seed data companies found in holdings. Got: {names}"
        print(f"PASS: seed companies found in holdings: {found}")

    def test_total_portfolio_value_matches_holdings(self, summary):
        """total_portfolio_value KPI must equal sum of all entry_valuation in holdings"""
        kpi_val = summary["kpis"]["total_portfolio_value"]
        holdings_sum = sum(h.get("entry_valuation", 0) or 0 for h in summary["holdings"])
        assert kpi_val == holdings_sum, (
            f"KPI total_portfolio_value={kpi_val} != holdings sum={holdings_sum}"
        )
        print(f"PASS: total_portfolio_value={kpi_val} matches holdings sum={holdings_sum}")

    def test_no_mongodb_id_in_holdings(self, summary):
        """MongoDB _id should never be exposed in the API response"""
        for h in summary["holdings"]:
            assert "_id" not in h, f"MongoDB _id exposed in holding: {h['company_name']}"
        print("PASS: no MongoDB _id in holdings")
