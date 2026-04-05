"""
Phase 3 Backend Tests for ZephyrWealth
Tests: Deal Pipeline APIs, Dashboard Charts, Role-Based Access
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ─── Helpers ─────────────────────────────────────────────────────────────────
def get_session_for(email, password):
    """Return a requests.Session with auth cookie set."""
    s = requests.Session()
    res = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed for {email}: {res.text}"
    return s


# ─── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def compliance_session():
    return get_session_for("compliance@zephyrwealth.ai", "Comply1234!")

@pytest.fixture(scope="module")
def risk_session():
    return get_session_for("risk@zephyrwealth.ai", "Risk1234!")

@pytest.fixture(scope="module")
def manager_session():
    return get_session_for("manager@zephyrwealth.ai", "Manager1234!")

@pytest.fixture(scope="module")
def seed_deal_ids(compliance_session):
    """Fetch seed deal IDs from the DB."""
    res = compliance_session.get(f"{BASE_URL}/api/deals")
    assert res.status_code == 200
    deals = res.json()
    return {d['company_name']: d['id'] for d in deals if 'company_name' in d}


# ─── Dashboard Charts API ─────────────────────────────────────────────────────
class TestDashboardCharts:
    """Tests for /api/dashboard/charts endpoint"""

    def test_charts_returns_200(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/dashboard/charts")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"

    def test_charts_has_investor_funnel(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/dashboard/charts")
        data = res.json()
        assert "investor_funnel" in data, "Missing investor_funnel key"
        assert isinstance(data["investor_funnel"], list), "investor_funnel must be a list"
        assert len(data["investor_funnel"]) > 0, "investor_funnel should not be empty"

    def test_charts_has_deal_pipeline(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/dashboard/charts")
        data = res.json()
        assert "deal_pipeline" in data, "Missing deal_pipeline key"
        assert isinstance(data["deal_pipeline"], list), "deal_pipeline must be a list"

    def test_deal_pipeline_has_4_stages(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/dashboard/charts")
        data = res.json()
        stages = [item["stage"] for item in data["deal_pipeline"]]
        # Should have Leads, Due Diligence, IC Review, Closing
        assert len(data["deal_pipeline"]) == 4, f"Expected 4 stages, got {len(data['deal_pipeline'])}"

    def test_investor_funnel_items_have_required_fields(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/dashboard/charts")
        data = res.json()
        for item in data["investor_funnel"]:
            assert "status" in item, "investor_funnel item missing 'status'"
            assert "count" in item, "investor_funnel item missing 'count'"
            assert "color" in item, "investor_funnel item missing 'color'"

    def test_deal_pipeline_items_have_required_fields(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/dashboard/charts")
        data = res.json()
        for item in data["deal_pipeline"]:
            assert "stage" in item, "deal_pipeline item missing 'stage'"
            assert "count" in item, "deal_pipeline item missing 'count'"
            assert "color" in item, "deal_pipeline item missing 'color'"

    def test_charts_requires_auth(self):
        anon = requests.Session()
        res = anon.get(f"{BASE_URL}/api/dashboard/charts")
        assert res.status_code == 401, f"Expected 401 for unauthenticated, got {res.status_code}"


# ─── Deals API: List ───────────────────────────────────────────────────────────
class TestDealsListAPI:
    """Tests for GET /api/deals"""

    def test_get_deals_returns_200(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        assert res.status_code == 200

    def test_get_deals_returns_list(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        data = res.json()
        assert isinstance(data, list), "Expected list response"

    def test_seed_deals_present(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        names = [d.get("company_name") for d in res.json()]
        assert "NexaTech Caribbean Ltd" in names, "NexaTech seed deal missing"
        assert "West African Fintrust ICON" in names, "West African Fintrust seed deal missing"
        assert "Nassau Microfinance Co." in names, "Nassau Microfinance seed deal missing"

    def test_deal_has_required_fields(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        deals = res.json()
        full_schema_deals = [d for d in deals if d.get("company_name")]
        assert len(full_schema_deals) > 0
        deal = full_schema_deals[0]
        for field in ["id", "company_name", "sector", "geography", "expected_irr", "entity_type", "mandate_status", "pipeline_stage"]:
            assert field in deal, f"Deal missing field: {field}"

    def test_nexatech_is_in_ic_review(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        deals = {d.get("company_name"): d for d in res.json()}
        nexa = deals.get("NexaTech Caribbean Ltd")
        assert nexa is not None
        assert nexa["pipeline_stage"] == "ic_review", f"Expected ic_review, got {nexa['pipeline_stage']}"
        assert nexa["mandate_status"] == "In Mandate"
        assert nexa["entity_type"] == "IBC"

    def test_west_african_is_in_due_diligence(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        deals = {d.get("company_name"): d for d in res.json()}
        wa = deals.get("West African Fintrust ICON")
        assert wa is not None
        assert wa["pipeline_stage"] == "due_diligence", f"Expected due_diligence, got {wa['pipeline_stage']}"
        assert wa["mandate_status"] == "Exception"
        assert wa["entity_type"] == "ICON"

    def test_nassau_microfinance_is_in_leads(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        deals = {d.get("company_name"): d for d in res.json()}
        nassau = deals.get("Nassau Microfinance Co.")
        assert nassau is not None
        assert nassau["pipeline_stage"] == "leads", f"Expected leads, got {nassau['pipeline_stage']}"
        assert nassau["mandate_status"] == "In Mandate"

    def test_get_deals_requires_auth(self):
        anon = requests.Session()
        res = anon.get(f"{BASE_URL}/api/deals")
        assert res.status_code == 401


# ─── Deals API: Create ─────────────────────────────────────────────────────────
class TestDealsCreateAPI:
    """Tests for POST /api/deals"""

    def test_create_deal_returns_201_or_200(self, compliance_session):
        payload = {
            "company_name": "TEST_Alpha Holdings Ltd",
            "sector": "Technology",
            "geography": "Caribbean",
            "asset_class": "Private Equity",
            "expected_irr": 20.0,
            "entry_valuation": 5000000,
            "entity_type": "IBC"
        }
        res = compliance_session.post(f"{BASE_URL}/api/deals", json=payload)
        assert res.status_code in [200, 201], f"Expected 200/201, got {res.status_code}: {res.text}"

    def test_create_deal_response_has_id(self, compliance_session):
        payload = {
            "company_name": "TEST_Beta Ventures ICON",
            "sector": "Fintech",
            "geography": "Africa",
            "asset_class": "Venture",
            "expected_irr": 8.0,  # Low IRR may trigger Exception
            "entry_valuation": 2000000,
            "entity_type": "ICON"
        }
        res = compliance_session.post(f"{BASE_URL}/api/deals", json=payload)
        assert res.status_code in [200, 201]
        data = res.json()
        assert "id" in data, "Response missing 'id'"

    def test_create_deal_starts_in_leads(self, compliance_session):
        payload = {
            "company_name": "TEST_Gamma Corp IBC",
            "sector": "Healthcare",
            "geography": "Caribbean",
            "asset_class": "Private Equity",
            "expected_irr": 15.0,
            "entry_valuation": 3000000,
            "entity_type": "IBC"
        }
        res = compliance_session.post(f"{BASE_URL}/api/deals", json=payload)
        data = res.json()
        assert data.get("pipeline_stage") == "leads", f"New deal should start in leads, got {data.get('pipeline_stage')}"

    def test_create_deal_persisted_in_db(self, compliance_session):
        payload = {
            "company_name": "TEST_Delta Fund",
            "sector": "Real Estate",
            "geography": "Caribbean",
            "asset_class": "Real Estate",
            "expected_irr": 18.0,
            "entry_valuation": 10000000,
            "entity_type": "IBC"
        }
        res = compliance_session.post(f"{BASE_URL}/api/deals", json=payload)
        assert res.status_code in [200, 201]
        deal_id = res.json()["id"]

        # GET to verify persistence
        get_res = compliance_session.get(f"{BASE_URL}/api/deals/{deal_id}")
        assert get_res.status_code == 200
        fetched = get_res.json()
        assert fetched["company_name"] == "TEST_Delta Fund"

    def test_create_deal_requires_auth(self):
        anon = requests.Session()
        payload = {
            "company_name": "TEST_Anon Deal",
            "sector": "Technology",
            "geography": "Caribbean",
            "asset_class": "Private Equity",
            "expected_irr": 15.0,
            "entry_valuation": 1000000,
            "entity_type": "IBC"
        }
        res = anon.post(f"{BASE_URL}/api/deals", json=payload)
        assert res.status_code == 401


# ─── Deals API: Get Single ────────────────────────────────────────────────────
class TestDealGetAPI:
    """Tests for GET /api/deals/{id}"""

    def test_get_single_deal(self, compliance_session, seed_deal_ids):
        deal_id = seed_deal_ids.get("NexaTech Caribbean Ltd")
        assert deal_id, "NexaTech deal ID not found"
        res = compliance_session.get(f"{BASE_URL}/api/deals/{deal_id}")
        assert res.status_code == 200

    def test_get_single_deal_data_correct(self, compliance_session, seed_deal_ids):
        deal_id = seed_deal_ids.get("NexaTech Caribbean Ltd")
        res = compliance_session.get(f"{BASE_URL}/api/deals/{deal_id}")
        data = res.json()
        assert data["company_name"] == "NexaTech Caribbean Ltd"
        assert data["entity_type"] == "IBC"
        assert data["mandate_status"] == "In Mandate"
        assert data["pipeline_stage"] == "ic_review"

    def test_get_deal_invalid_id_returns_400(self, compliance_session):
        res = compliance_session.get(f"{BASE_URL}/api/deals/invalid_id")
        assert res.status_code == 400

    def test_get_deal_not_found_returns_404(self, compliance_session):
        # Valid ObjectId format but non-existent
        res = compliance_session.get(f"{BASE_URL}/api/deals/000000000000000000000000")
        assert res.status_code == 404


# ─── Deal Health Score ─────────────────────────────────────────────────────────
class TestDealHealthScore:
    """Tests for GET /api/deals/{id}/health-score"""

    def test_health_score_returns_200(self, compliance_session, seed_deal_ids):
        deal_id = seed_deal_ids.get("NexaTech Caribbean Ltd")
        assert deal_id
        res = compliance_session.get(f"{BASE_URL}/api/deals/{deal_id}/health-score")
        assert res.status_code == 200

    def test_health_score_has_required_fields(self, compliance_session, seed_deal_ids):
        deal_id = seed_deal_ids.get("NexaTech Caribbean Ltd")
        res = compliance_session.get(f"{BASE_URL}/api/deals/{deal_id}/health-score")
        data = res.json()
        for field in ["compliance_risk", "financial_alignment", "document_status", "mandate_status",
                      "stamp_duty_estimate", "stamp_duty_pct", "entry_valuation", "overall", "doc_count"]:
            assert field in data, f"Missing field: {field}"

    def test_health_score_overall_valid(self, compliance_session, seed_deal_ids):
        deal_id = seed_deal_ids.get("NexaTech Caribbean Ltd")
        res = compliance_session.get(f"{BASE_URL}/api/deals/{deal_id}/health-score")
        data = res.json()
        assert data["overall"] in ["Recommend Approve", "Review", "Block"], f"Unexpected overall: {data['overall']}"

    def test_health_score_stamp_duty_calculated(self, compliance_session, seed_deal_ids):
        deal_id = seed_deal_ids.get("NexaTech Caribbean Ltd")
        res = compliance_session.get(f"{BASE_URL}/api/deals/{deal_id}/health-score")
        data = res.json()
        # NexaTech entry_valuation = 8000000; stamp = 8000000 * 0.005 = 40000
        assert data["stamp_duty_estimate"] == 40000.0, f"Expected 40000, got {data['stamp_duty_estimate']}"


# ─── Deal Stage Update ─────────────────────────────────────────────────────────
class TestDealStageUpdate:
    """Tests for PUT /api/deals/{id}/stage"""

    def test_advance_deal_stage(self, compliance_session):
        # Create a fresh test deal to advance
        payload = {
            "company_name": "TEST_StageAdvance Co",
            "sector": "Technology",
            "geography": "Caribbean",
            "asset_class": "Private Equity",
            "expected_irr": 18.0,
            "entry_valuation": 3000000,
            "entity_type": "IBC"
        }
        create_res = compliance_session.post(f"{BASE_URL}/api/deals", json=payload)
        assert create_res.status_code in [200, 201]
        deal_id = create_res.json()["id"]

        # Advance from leads -> due_diligence
        res = compliance_session.put(f"{BASE_URL}/api/deals/{deal_id}/stage", json={"stage": "due_diligence"})
        assert res.status_code == 200, f"Stage update failed: {res.text}"
        data = res.json()
        assert data["pipeline_stage"] == "due_diligence"

    def test_exception_deal_blocked_without_override(self, compliance_session, seed_deal_ids):
        # West African Fintrust has Exception mandate status
        deal_id = seed_deal_ids.get("West African Fintrust ICON")
        assert deal_id
        # Try to advance without override_note
        res = compliance_session.put(f"{BASE_URL}/api/deals/{deal_id}/stage", json={"stage": "ic_review"})
        assert res.status_code == 403, f"Expected 403 for mandate exception block, got {res.status_code}: {res.text}"

    def test_exception_deal_advances_with_override(self, risk_session, seed_deal_ids):
        # Risk officer can advance with override_note
        deal_id = seed_deal_ids.get("West African Fintrust ICON")
        assert deal_id
        res = risk_session.put(f"{BASE_URL}/api/deals/{deal_id}/stage", json={
            "stage": "ic_review",
            "override_note": "Risk officer override - deal reviewed and approved for advancement"
        })
        assert res.status_code == 200, f"Expected 200 with override, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["pipeline_stage"] == "ic_review"
        # Move it back to due_diligence for other tests
        risk_session.put(f"{BASE_URL}/api/deals/{deal_id}/stage", json={"stage": "due_diligence", "override_note": "Moved back for testing"})


# ─── Role-Based Access ──────────────────────────────────────────────────────────
class TestRoleBasedAccess:
    """Test role-based behavior at API level"""

    def test_all_roles_can_list_deals(self, compliance_session, risk_session, manager_session):
        for sess, role in [(compliance_session, "compliance"), (risk_session, "risk"), (manager_session, "manager")]:
            res = sess.get(f"{BASE_URL}/api/deals")
            assert res.status_code == 200, f"{role} should be able to list deals"

    def test_all_roles_can_get_deal_detail(self, compliance_session, risk_session, manager_session, seed_deal_ids):
        deal_id = seed_deal_ids.get("NexaTech Caribbean Ltd")
        for sess, role in [(compliance_session, "compliance"), (risk_session, "risk"), (manager_session, "manager")]:
            res = sess.get(f"{BASE_URL}/api/deals/{deal_id}")
            assert res.status_code == 200, f"{role} should be able to get deal detail"

    def test_all_roles_can_get_health_score(self, compliance_session, risk_session, manager_session, seed_deal_ids):
        deal_id = seed_deal_ids.get("NexaTech Caribbean Ltd")
        for sess, role in [(compliance_session, "compliance"), (risk_session, "risk"), (manager_session, "manager")]:
            res = sess.get(f"{BASE_URL}/api/deals/{deal_id}/health-score")
            assert res.status_code == 200, f"{role} should be able to get health score"

    def test_all_roles_can_access_dashboard_charts(self, compliance_session, risk_session, manager_session):
        for sess, role in [(compliance_session, "compliance"), (risk_session, "risk"), (manager_session, "manager")]:
            res = sess.get(f"{BASE_URL}/api/dashboard/charts")
            assert res.status_code == 200, f"{role} should be able to access dashboard charts"

    def test_all_roles_can_advance_stage(self, compliance_session, risk_session, manager_session):
        """All authenticated roles should be able to advance a deal stage (backend has no role restriction for advance)"""
        # Create a fresh deal for each role to advance
        for sess, role in [(compliance_session, "compliance"), (risk_session, "risk"), (manager_session, "manager")]:
            payload = {
                "company_name": f"TEST_RoleAdvance_{role}",
                "sector": "Technology",
                "geography": "Caribbean",
                "asset_class": "Private Equity",
                "expected_irr": 16.0,
                "entry_valuation": 2000000,
                "entity_type": "IBC"
            }
            create_res = compliance_session.post(f"{BASE_URL}/api/deals", json=payload)
            assert create_res.status_code in [200, 201]
            deal_id = create_res.json()["id"]
            adv_res = sess.put(f"{BASE_URL}/api/deals/{deal_id}/stage", json={"stage": "due_diligence"})
            assert adv_res.status_code == 200, f"{role} should be able to advance deal stage, got {adv_res.status_code}"
