"""ZephyrWealth Phase 2 - Investor Onboarding & Scorecard API Tests"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ─── Seeded investor IDs (grabbed from DB after Phase 2 seeding) ──────────────
VICTORIA_NAME = "Victoria Pemberton"
APEX_NAME = "Apex Meridian Holdings Ltd"
DMITRI_NAME = "Dmitri Volkov"


@pytest.fixture(scope="module")
def auth_session():
    """Authenticated session using compliance role"""
    session = requests.Session()
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "compliance@zephyrwealth.ai",
        "password": "Comply1234!"
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    return session


@pytest.fixture(scope="module")
def seeded_investors(auth_session):
    """Retrieve seeded investor IDs by name"""
    r = auth_session.get(f"{BASE_URL}/api/investors")
    assert r.status_code == 200
    investors = r.json()
    result = {}
    for inv in investors:
        name = inv.get("name") or inv.get("legal_name")
        if name == VICTORIA_NAME:
            result["victoria_id"] = inv["id"]
        elif name == APEX_NAME:
            result["apex_id"] = inv["id"]
        elif name == DMITRI_NAME:
            result["dmitri_id"] = inv["id"]
    assert "victoria_id" in result, f"Victoria Pemberton not found in investor list"
    assert "apex_id" in result, f"Apex Meridian Holdings Ltd not found"
    assert "dmitri_id" in result, f"Dmitri Volkov not found"
    return result


# ─── Test 1: Investors List ───────────────────────────────────────────────────
class TestInvestorsList:
    """GET /api/investors"""

    def test_investors_list_returns_all(self, auth_session):
        """Should return all investors (at least 6 after Phase 2 seeding)"""
        r = auth_session.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 200
        investors = r.json()
        assert isinstance(investors, list)
        # Phase 1 (3) + Phase 2 (3) = 6 minimum; may have test entries
        assert len(investors) >= 6, f"Expected >= 6 investors, got {len(investors)}"

    def test_investors_list_has_required_fields(self, auth_session):
        """Each investor should have id, name, kyc_status, risk_rating"""
        r = auth_session.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 200
        investors = r.json()
        for inv in investors:
            assert "id" in inv
            assert "name" in inv or "legal_name" in inv
            assert "kyc_status" in inv
            assert "risk_rating" in inv

    def test_seeded_investors_present(self, auth_session):
        """Victoria, Apex Meridian, and Dmitri Volkov must be in the list"""
        r = auth_session.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 200
        names = [i.get("name") for i in r.json()]
        assert VICTORIA_NAME in names
        assert APEX_NAME in names
        assert DMITRI_NAME in names

    def test_investors_without_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 401


# ─── Test 2: Create Investor ──────────────────────────────────────────────────
class TestCreateInvestor:
    """POST /api/investors"""

    @pytest.fixture(scope="class")
    def created_investor(self, auth_session):
        payload = {
            "entity_type": "individual",
            "legal_name": "TEST_AutoTest Investor",
            "dob": "1985-06-15",
            "nationality": "United Kingdom",
            "residence_country": "Bahamas",
            "email": "test.autotest@example.com",
            "phone": "+1 242-555-9999",
            "address": {
                "street": "99 Test Lane",
                "city": "Nassau",
                "postal_code": "N-0001",
                "country": "Bahamas"
            },
            "net_worth": 2500000,
            "annual_income": 300000,
            "source_of_wealth": "Employment",
            "investment_experience": "3-5 years",
            "classification": "individual_accredited",
            "ubo_declarations": [],
            "accredited_declaration": True,
            "terms_accepted": True
        }
        r = auth_session.post(f"{BASE_URL}/api/investors", json=payload)
        assert r.status_code == 200, f"Create investor failed: {r.text}"
        return r.json()

    def test_create_investor_returns_id(self, created_investor):
        assert "id" in created_investor
        assert isinstance(created_investor["id"], str)
        assert len(created_investor["id"]) > 0

    def test_create_investor_fields_match(self, created_investor):
        assert created_investor["legal_name"] == "TEST_AutoTest Investor"
        assert created_investor["name"] == "TEST_AutoTest Investor"
        assert created_investor["entity_type"] == "individual"
        assert created_investor["kyc_status"] == "pending"
        assert created_investor["scorecard_completed"] is False

    def test_create_investor_persisted_in_db(self, auth_session, created_investor):
        """GET to verify investor was actually saved"""
        inv_id = created_investor["id"]
        r = auth_session.get(f"{BASE_URL}/api/investors/{inv_id}")
        assert r.status_code == 200
        fetched = r.json()
        assert fetched["legal_name"] == "TEST_AutoTest Investor"
        assert fetched["email"] == "test.autotest@example.com"
        assert fetched["net_worth"] == 2500000

    def test_create_investor_appears_in_list(self, auth_session, created_investor):
        """Newly created investor should appear in investors list"""
        r = auth_session.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 200
        names = [i.get("name") for i in r.json()]
        assert "TEST_AutoTest Investor" in names

    def test_create_corporate_investor_with_ubo(self, auth_session):
        """Corporate investor with UBO declarations"""
        payload = {
            "entity_type": "corporate",
            "legal_name": "TEST_Corp Holdings Ltd",
            "dob": "2010-01-01",
            "nationality": "Cayman Islands",
            "residence_country": "Cayman Islands",
            "email": "corp@testholdingsltd.com",
            "phone": "+1 345-555-7777",
            "address": {
                "street": "1 Harbor Blvd",
                "city": "George Town",
                "postal_code": "KY1-1001",
                "country": "Cayman Islands"
            },
            "net_worth": 50000000,
            "annual_income": 8000000,
            "source_of_wealth": "Business",
            "investment_experience": "5+ years",
            "classification": "institutional",
            "ubo_declarations": [
                {"name": "John Corporate", "nationality": "United Kingdom", "ownership_percentage": 60.0},
                {"name": "Jane Corporate", "nationality": "Canada", "ownership_percentage": 40.0}
            ],
            "accredited_declaration": False,
            "terms_accepted": True
        }
        r = auth_session.post(f"{BASE_URL}/api/investors", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["entity_type"] == "corporate"
        assert data["type"] == "Corporate Entity"
        assert len(data["ubo_declarations"]) == 2

    def test_create_investor_without_auth_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/investors", json={"legal_name": "Unauthorized"})
        assert r.status_code == 401


# ─── Test 3: Get Investor Detail ──────────────────────────────────────────────
class TestGetInvestor:
    """GET /api/investors/{id}"""

    def test_get_victoria_pemberton(self, auth_session, seeded_investors):
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['victoria_id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["legal_name"] == VICTORIA_NAME
        assert data["kyc_status"] == "approved"
        assert data["risk_rating"] == "low"
        assert data["scorecard_completed"] is True
        assert data["entity_type"] == "individual"

    def test_get_apex_meridian(self, auth_session, seeded_investors):
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['apex_id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["legal_name"] == APEX_NAME
        assert data["kyc_status"] == "pending"
        assert data["risk_rating"] == "medium"
        assert data["scorecard_completed"] is False
        assert data["entity_type"] == "corporate"
        # UBO declarations should exist
        assert len(data["ubo_declarations"]) == 2

    def test_get_dmitri_volkov(self, auth_session, seeded_investors):
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['dmitri_id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["legal_name"] == DMITRI_NAME
        assert data["kyc_status"] == "flagged"
        assert data["risk_rating"] == "high"
        assert data["scorecard_completed"] is True

    def test_get_investor_invalid_id_returns_400(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/investors/invalid-id")
        assert r.status_code == 400

    def test_get_investor_nonexistent_returns_404(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/investors/000000000000000000000000")
        assert r.status_code == 404


# ─── Test 4: Documents ────────────────────────────────────────────────────────
class TestDocuments:
    """POST/GET /api/investors/{id}/documents"""

    @pytest.fixture(scope="class")
    def test_investor_id(self, auth_session):
        """Create a fresh investor for document upload testing"""
        payload = {
            "entity_type": "individual",
            "legal_name": "TEST_DocTest Investor",
            "dob": "1990-01-01",
            "nationality": "Canada",
            "residence_country": "Canada",
            "email": "doctest@example.com",
            "phone": "+1 416-555-0000",
            "address": {"street": "1 Doc St", "city": "Toronto", "postal_code": "M1A 1A1", "country": "Canada"},
            "net_worth": 1000000,
            "annual_income": 150000,
            "source_of_wealth": "Employment",
            "investment_experience": "1-3 years",
            "classification": "individual_accredited",
            "ubo_declarations": [],
            "accredited_declaration": True,
            "terms_accepted": True
        }
        r = auth_session.post(f"{BASE_URL}/api/investors", json=payload)
        assert r.status_code == 200
        return r.json()["id"]

    def test_list_docs_initially_empty(self, auth_session, test_investor_id):
        r = auth_session.get(f"{BASE_URL}/api/investors/{test_investor_id}/documents")
        assert r.status_code == 200
        assert r.json() == []

    def test_upload_document_pdf(self, auth_session, test_investor_id):
        """Upload a PDF document for passport"""
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content for testing purposes")
        r = auth_session.post(
            f"{BASE_URL}/api/investors/{test_investor_id}/documents",
            files={"file": ("test_passport.pdf", fake_pdf, "application/pdf")},
            data={"document_type": "passport"}
        )
        assert r.status_code == 200, f"Upload failed: {r.text}"
        data = r.json()
        assert data["document_type"] == "passport"
        assert data["file_name"] == "test_passport.pdf"
        assert "id" in data

    def test_list_docs_after_upload(self, auth_session, test_investor_id):
        r = auth_session.get(f"{BASE_URL}/api/investors/{test_investor_id}/documents")
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 1
        assert any(d["document_type"] == "passport" for d in docs)

    def test_seeded_apex_documents(self, auth_session, seeded_investors):
        """Apex Meridian should have 4 documents (corporate)"""
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['apex_id']}/documents")
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) == 4
        doc_types = [d["document_type"] for d in docs]
        assert "passport" in doc_types
        assert "proof_of_address" in doc_types
        assert "source_of_wealth_doc" in doc_types
        assert "corporate_documents" in doc_types

    def test_seeded_dmitri_documents(self, auth_session, seeded_investors):
        """Dmitri Volkov should have 2 documents"""
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['dmitri_id']}/documents")
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) >= 2

    def test_upload_invalid_file_type_returns_400(self, auth_session, test_investor_id):
        """Uploading a .txt file should be rejected"""
        fake_txt = io.BytesIO(b"just some text content")
        r = auth_session.post(
            f"{BASE_URL}/api/investors/{test_investor_id}/documents",
            files={"file": ("test.txt", fake_txt, "text/plain")},
            data={"document_type": "passport"}
        )
        assert r.status_code == 400


# ─── Test 5: Scorecard ────────────────────────────────────────────────────────
class TestScorecard:
    """GET/POST /api/investors/{id}/scorecard"""

    def test_get_scorecard_dmitri_volkov(self, auth_session, seeded_investors):
        """Dmitri Volkov's seeded scorecard should have Reject recommendation"""
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['dmitri_id']}/scorecard")
        assert r.status_code == 200
        sc = r.json()
        assert sc is not None
        assert sc["recommendation"] == "Reject"
        sd = sc["scorecard_data"]
        assert sd["recommendation"] == "Reject"
        assert sd["risk_rating"] == "High"
        assert sd["edd_required"] is True
        assert "identity_confidence_score" in sd
        assert sd["identity_confidence_score"] == 34
        assert "summary" in sd and len(sd["summary"]) > 0

    def test_get_scorecard_victoria_pemberton(self, auth_session, seeded_investors):
        """Victoria Pemberton's scorecard should have Approve recommendation"""
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['victoria_id']}/scorecard")
        assert r.status_code == 200
        sc = r.json()
        assert sc["recommendation"] == "Approve"
        assert sc["scorecard_data"]["identity_confidence_score"] == 91

    def test_get_scorecard_apex_no_scorecard(self, auth_session, seeded_investors):
        """Apex Meridian has no scorecard — should return null/None"""
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['apex_id']}/scorecard")
        assert r.status_code == 200
        assert r.json() is None

    def test_generate_scorecard_apex(self, auth_session, seeded_investors):
        """POST to generate AI scorecard for Apex (Claude AI — may take ~15s)"""
        import time
        r = auth_session.post(
            f"{BASE_URL}/api/investors/{seeded_investors['apex_id']}/scorecard",
            timeout=60
        )
        assert r.status_code == 200, f"Scorecard generation failed: {r.text}"
        sc = r.json()
        assert "scorecard_data" in sc
        sd = sc["scorecard_data"]
        # Validate required fields in Claude response
        assert "sanctions_status" in sd
        assert "identity_status" in sd
        assert "document_status" in sd
        assert "source_of_funds" in sd
        assert "pep_status" in sd
        assert "mandate_status" in sd
        assert "identity_confidence_score" in sd
        assert isinstance(sd["identity_confidence_score"], (int, float))
        assert 0 <= sd["identity_confidence_score"] <= 100
        assert "recommendation" in sd
        assert sd["recommendation"] in ["Approve", "Review", "Reject"]
        assert "score_breakdown" in sd
        assert "summary" in sd
        assert len(sd["summary"]) > 0

    def test_apex_scorecard_completed_after_generation(self, auth_session, seeded_investors):
        """After generation, investor.scorecard_completed should be True"""
        r = auth_session.get(f"{BASE_URL}/api/investors/{seeded_investors['apex_id']}")
        assert r.status_code == 200
        assert r.json()["scorecard_completed"] is True


# ─── Test 6: Decision ────────────────────────────────────────────────────────
class TestDecision:
    """POST /api/investors/{id}/decision"""

    @pytest.fixture(scope="class")
    def decisioned_investor_id(self, auth_session):
        """Create investor with generated scorecard for decision testing"""
        payload = {
            "entity_type": "individual",
            "legal_name": "TEST_Decision Investor",
            "dob": "1980-03-10",
            "nationality": "Canada",
            "residence_country": "Canada",
            "email": "decision.test@example.com",
            "phone": "+1 416-555-1234",
            "address": {"street": "10 Decision Ave", "city": "Vancouver", "postal_code": "V6B 1A1", "country": "Canada"},
            "net_worth": 5000000,
            "annual_income": 500000,
            "source_of_wealth": "Business",
            "investment_experience": "5+ years",
            "classification": "individual_accredited",
            "ubo_declarations": [],
            "accredited_declaration": True,
            "terms_accepted": True
        }
        r = auth_session.post(f"{BASE_URL}/api/investors", json=payload)
        assert r.status_code == 200
        inv_id = r.json()["id"]
        # Generate scorecard for this investor
        sc_r = auth_session.post(f"{BASE_URL}/api/investors/{inv_id}/scorecard", timeout=60)
        assert sc_r.status_code == 200, f"Scorecard gen failed: {sc_r.text}"
        return inv_id

    def test_approve_investor(self, auth_session, decisioned_investor_id):
        """Approve an investor with completed scorecard"""
        r = auth_session.post(
            f"{BASE_URL}/api/investors/{decisioned_investor_id}/decision",
            json={"decision": "approve"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "approved"
        assert "message" in data

    def test_investor_status_updated_to_approved(self, auth_session, decisioned_investor_id):
        """After approval, investor kyc_status should be 'approved'"""
        r = auth_session.get(f"{BASE_URL}/api/investors/{decisioned_investor_id}")
        assert r.status_code == 200
        assert r.json()["kyc_status"] == "approved"

    def test_reject_decision(self, auth_session, seeded_investors):
        """Reject Dmitri Volkov (already has scorecard)"""
        r = auth_session.post(
            f"{BASE_URL}/api/investors/{seeded_investors['dmitri_id']}/decision",
            json={"decision": "reject"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "rejected"

    def test_more_info_decision(self, auth_session, seeded_investors):
        """Request more info (keeps status pending)"""
        # Use Victoria (scorecard_completed = True)
        r = auth_session.post(
            f"{BASE_URL}/api/investors/{seeded_investors['victoria_id']}/decision",
            json={"decision": "more_info"}
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "pending"

    def test_decision_without_auth_returns_401(self, seeded_investors):
        r = requests.post(
            f"{BASE_URL}/api/investors/{seeded_investors['dmitri_id']}/decision",
            json={"decision": "reject"}
        )
        assert r.status_code == 401


# ─── Test 7: Dashboard Stats Updated ─────────────────────────────────────────
class TestDashboardStats:
    """Dashboard KPIs with Phase 2 data"""

    def test_stats_total_investors_updated(self, auth_session):
        """Total investors should be at least 6 (3 phase1 + 3 phase2)"""
        r = auth_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total_investors"] >= 6, f"Expected >= 6, got {data['total_investors']}"

    def test_stats_has_required_kpi_fields(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_investors" in data
        assert "pending_kyc" in data
        assert "deals_in_pipeline" in data
        assert "flagged_items" in data
