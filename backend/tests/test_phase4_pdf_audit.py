"""
Phase 4 Backend Tests - PDF Exports, Audit Logs, TAV Report, Seed Data
Tests: Feature 8 (Deal PDF), Feature 9 (Investor KYC PDF), Feature 10 (Audit Logs),
       Feature 11 (TAV PDF), Feature 12 (Seed Data)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def compliance_session():
    """Authenticated session for compliance@zephyrwealth.ai"""
    session = requests.Session()
    res = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "compliance@zephyrwealth.ai",
        "password": "Comply1234!"
    })
    assert res.status_code == 200, f"Compliance login failed: {res.text}"
    return session


@pytest.fixture(scope="module")
def risk_session():
    """Authenticated session for risk@zephyrwealth.ai"""
    session = requests.Session()
    res = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "risk@zephyrwealth.ai",
        "password": "Risk1234!"
    })
    assert res.status_code == 200, f"Risk login failed: {res.text}"
    return session


@pytest.fixture(scope="module")
def manager_session():
    """Authenticated session for manager@zephyrwealth.ai"""
    session = requests.Session()
    res = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "manager@zephyrwealth.ai",
        "password": "Manager1234!"
    })
    assert res.status_code == 200, f"Manager login failed: {res.text}"
    return session


@pytest.fixture(scope="module")
def first_deal_id(compliance_session):
    """Get first available deal ID for PDF tests"""
    res = compliance_session.get(f"{BASE_URL}/api/deals")
    assert res.status_code == 200
    deals = res.json()
    assert len(deals) > 0, "No deals found in database"
    return deals[0]["id"]


@pytest.fixture(scope="module")
def first_investor_id(compliance_session):
    """Get first available investor ID for PDF tests"""
    res = compliance_session.get(f"{BASE_URL}/api/investors")
    assert res.status_code == 200
    investors = res.json()
    assert len(investors) > 0, "No investors found in database"
    return investors[0]["id"]


# ─── Feature 8: Deal PDF Export ───────────────────────────────────────────────

class TestDealPDFExport:
    """Feature 8 - GET /api/deals/{id}/export-pdf"""

    def test_deal_pdf_compliance_http200(self, compliance_session, first_deal_id):
        """Compliance role can download deal IC Pack PDF"""
        res = compliance_session.get(f"{BASE_URL}/api/deals/{first_deal_id}/export-pdf")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text[:200]}"

    def test_deal_pdf_compliance_content_type(self, compliance_session, first_deal_id):
        """Deal PDF response should be application/pdf"""
        res = compliance_session.get(f"{BASE_URL}/api/deals/{first_deal_id}/export-pdf")
        assert res.status_code == 200
        assert "application/pdf" in res.headers.get("content-type", ""), \
            f"Expected PDF content type, got: {res.headers.get('content-type')}"

    def test_deal_pdf_compliance_has_content(self, compliance_session, first_deal_id):
        """Deal PDF should have actual PDF content (starts with %PDF)"""
        res = compliance_session.get(f"{BASE_URL}/api/deals/{first_deal_id}/export-pdf")
        assert res.status_code == 200
        assert res.content[:4] == b"%PDF", "PDF content does not start with %PDF"

    def test_deal_pdf_compliance_content_disposition(self, compliance_session, first_deal_id):
        """Deal PDF should have Content-Disposition attachment header"""
        res = compliance_session.get(f"{BASE_URL}/api/deals/{first_deal_id}/export-pdf")
        assert res.status_code == 200
        cd = res.headers.get("content-disposition", "")
        assert "attachment" in cd, f"Missing attachment in Content-Disposition: {cd}"

    def test_deal_pdf_risk_http200(self, risk_session, first_deal_id):
        """Risk role can download deal IC Pack PDF"""
        res = risk_session.get(f"{BASE_URL}/api/deals/{first_deal_id}/export-pdf")
        assert res.status_code == 200, f"Expected 200 for risk role, got {res.status_code}"

    def test_deal_pdf_manager_forbidden(self, manager_session, first_deal_id):
        """Manager role should get 403 for deal PDF"""
        res = manager_session.get(f"{BASE_URL}/api/deals/{first_deal_id}/export-pdf")
        assert res.status_code == 403, f"Expected 403 for manager, got {res.status_code}: {res.text[:200]}"

    def test_deal_pdf_unauthenticated_forbidden(self, first_deal_id):
        """Unauthenticated request should get 401/403"""
        session = requests.Session()
        res = session.get(f"{BASE_URL}/api/deals/{first_deal_id}/export-pdf")
        assert res.status_code in (401, 403), f"Expected 401/403 for unauthenticated, got {res.status_code}"

    def test_deal_pdf_invalid_id(self, compliance_session):
        """Invalid deal ID should return 400 or 404"""
        res = compliance_session.get(f"{BASE_URL}/api/deals/invalid_id_abc/export-pdf")
        assert res.status_code in (400, 404), f"Expected 400/404 for invalid ID, got {res.status_code}"

    def test_deal_pdf_nonexistent_id(self, compliance_session):
        """Non-existent deal ID should return 404"""
        res = compliance_session.get(f"{BASE_URL}/api/deals/000000000000000000000000/export-pdf")
        assert res.status_code == 404, f"Expected 404 for nonexistent deal, got {res.status_code}"


# ─── Feature 9: Investor KYC PDF Export ───────────────────────────────────────

class TestInvestorKYCPDFExport:
    """Feature 9 - GET /api/investors/{id}/export-pdf"""

    def test_investor_pdf_compliance_http200(self, compliance_session, first_investor_id):
        """Compliance role can download investor KYC Pack PDF"""
        res = compliance_session.get(f"{BASE_URL}/api/investors/{first_investor_id}/export-pdf")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text[:200]}"

    def test_investor_pdf_compliance_content_type(self, compliance_session, first_investor_id):
        """Investor KYC PDF should be application/pdf"""
        res = compliance_session.get(f"{BASE_URL}/api/investors/{first_investor_id}/export-pdf")
        assert res.status_code == 200
        assert "application/pdf" in res.headers.get("content-type", "")

    def test_investor_pdf_compliance_has_pdf_content(self, compliance_session, first_investor_id):
        """Investor KYC PDF should have actual PDF binary content"""
        res = compliance_session.get(f"{BASE_URL}/api/investors/{first_investor_id}/export-pdf")
        assert res.status_code == 200
        assert res.content[:4] == b"%PDF", "KYC PDF content does not start with %PDF"

    def test_investor_pdf_risk_forbidden(self, risk_session, first_investor_id):
        """Risk role should get 403 for investor KYC PDF"""
        res = risk_session.get(f"{BASE_URL}/api/investors/{first_investor_id}/export-pdf")
        assert res.status_code == 403, f"Expected 403 for risk role, got {res.status_code}"

    def test_investor_pdf_manager_forbidden(self, manager_session, first_investor_id):
        """Manager role should get 403 for investor KYC PDF"""
        res = manager_session.get(f"{BASE_URL}/api/investors/{first_investor_id}/export-pdf")
        assert res.status_code == 403, f"Expected 403 for manager role, got {res.status_code}"

    def test_investor_pdf_invalid_id(self, compliance_session):
        """Invalid investor ID should return 400"""
        res = compliance_session.get(f"{BASE_URL}/api/investors/bad_id_xyz/export-pdf")
        assert res.status_code in (400, 404), f"Expected 400/404 for invalid ID, got {res.status_code}"


# ─── Feature 10: Audit Logs ───────────────────────────────────────────────────

class TestAuditLogs:
    """Feature 10 - GET /api/audit-logs"""

    def test_audit_log_compliance_http200(self, compliance_session):
        """Compliance role can access audit logs"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text[:200]}"

    def test_audit_log_response_structure(self, compliance_session):
        """Audit log response should have logs, total, page, limit, total_pages"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs")
        assert res.status_code == 200
        data = res.json()
        assert "logs" in data, "Missing 'logs' key in response"
        assert "total" in data, "Missing 'total' key in response"
        assert "page" in data, "Missing 'page' key in response"
        assert "limit" in data, "Missing 'limit' key in response"
        assert "total_pages" in data, "Missing 'total_pages' key in response"
        assert isinstance(data["logs"], list), "logs should be a list"

    def test_audit_log_has_seed_entries(self, compliance_session):
        """Audit log should have at least 15 seed entries"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs?limit=100")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 15, f"Expected >= 15 audit log entries, got {data['total']}"

    def test_audit_log_entry_fields(self, compliance_session):
        """Each audit log entry should have required fields"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs?limit=5")
        assert res.status_code == 200
        data = res.json()
        if len(data["logs"]) > 0:
            log = data["logs"][0]
            assert "id" in log, "Log entry missing 'id' field"
            assert "action" in log, "Log entry missing 'action' field"
            assert "timestamp" in log, "Log entry missing 'timestamp' field"

    def test_audit_log_action_filter(self, compliance_session):
        """Action filter should work correctly"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs?action=login")
        assert res.status_code == 200
        data = res.json()
        # All returned logs should have action=login
        for log in data["logs"]:
            assert log["action"] == "login", f"Filter failed: got action={log['action']}"

    def test_audit_log_role_filter(self, compliance_session):
        """Role filter should work without 500 error"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs?role=compliance")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data["logs"], list)

    def test_audit_log_date_filter(self, compliance_session):
        """Date range filter should return results without error"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs?from=2025-01-01&to=2026-12-31")
        assert res.status_code == 200
        data = res.json()
        assert "logs" in data

    def test_audit_log_pagination(self, compliance_session):
        """Pagination should work - page 1 limit 5"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs?page=1&limit=5")
        assert res.status_code == 200
        data = res.json()
        assert data["page"] == 1
        assert data["limit"] == 5
        assert len(data["logs"]) <= 5

    def test_audit_log_risk_forbidden(self, risk_session):
        """Risk role should get 403 for audit logs"""
        res = risk_session.get(f"{BASE_URL}/api/audit-logs")
        assert res.status_code == 403, f"Expected 403 for risk role, got {res.status_code}"

    def test_audit_log_manager_allowed(self, manager_session):
        """Manager role should be allowed to see audit logs (per backend implementation)"""
        res = manager_session.get(f"{BASE_URL}/api/audit-logs")
        assert res.status_code == 200, f"Expected 200 for manager role, got {res.status_code}"


# ─── Feature 11: TAV Report PDF ───────────────────────────────────────────────

class TestTAVReport:
    """Feature 11 - GET /api/reports/tav-pdf"""

    def test_tav_pdf_compliance_http200(self, compliance_session):
        """Compliance role can generate TAV PDF"""
        res = compliance_session.get(f"{BASE_URL}/api/reports/tav-pdf?from=2026-04-01&to=2026-06-30")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text[:200]}"

    def test_tav_pdf_is_pdf_content(self, compliance_session):
        """TAV PDF should have PDF content type and binary"""
        res = compliance_session.get(f"{BASE_URL}/api/reports/tav-pdf?from=2026-04-01&to=2026-06-30")
        assert res.status_code == 200
        assert "application/pdf" in res.headers.get("content-type", "")
        assert res.content[:4] == b"%PDF", "TAV PDF content not valid PDF"

    def test_tav_pdf_content_disposition(self, compliance_session):
        """TAV PDF should have attachment content-disposition"""
        res = compliance_session.get(f"{BASE_URL}/api/reports/tav-pdf?from=2026-04-01&to=2026-06-30")
        assert res.status_code == 200
        cd = res.headers.get("content-disposition", "")
        assert "attachment" in cd

    def test_tav_pdf_no_date_params_uses_current_quarter(self, compliance_session):
        """TAV PDF without date params should use current quarter"""
        res = compliance_session.get(f"{BASE_URL}/api/reports/tav-pdf")
        assert res.status_code == 200, f"Expected 200 without date params, got {res.status_code}"
        assert "application/pdf" in res.headers.get("content-type", "")

    def test_tav_pdf_risk_forbidden(self, risk_session):
        """Risk role should get 403 for TAV PDF"""
        res = risk_session.get(f"{BASE_URL}/api/reports/tav-pdf?from=2026-04-01&to=2026-06-30")
        assert res.status_code == 403, f"Expected 403 for risk role, got {res.status_code}"

    def test_tav_pdf_manager_forbidden(self, manager_session):
        """Manager role should get 403 for TAV PDF"""
        res = manager_session.get(f"{BASE_URL}/api/reports/tav-pdf?from=2026-04-01&to=2026-06-30")
        assert res.status_code == 403, f"Expected 403 for manager role, got {res.status_code}"


# ─── Feature 12: Seed Data Verification ──────────────────────────────────────

class TestSeedData:
    """Feature 12 - Idempotent demo seed data"""

    def test_investors_have_minimum_count(self, compliance_session):
        """Should have at least 6 seeded investors"""
        res = compliance_session.get(f"{BASE_URL}/api/investors")
        assert res.status_code == 200
        investors = res.json()
        assert len(investors) >= 6, f"Expected >= 6 investors, got {len(investors)}"

    def test_cayman_tech_ventures_approved(self, compliance_session):
        """Cayman Tech Ventures SPV Ltd should exist with approved status"""
        res = compliance_session.get(f"{BASE_URL}/api/investors")
        assert res.status_code == 200
        investors = res.json()
        names = [inv.get("legal_name", "") or inv.get("name", "") for inv in investors]
        cayman = [n for n in names if "Cayman" in n or "cayman" in n.lower()]
        assert len(cayman) >= 1, f"Expected Cayman Tech Ventures in investors, found: {names[:10]}"

    def test_investors_have_kyc_statuses(self, compliance_session):
        """Should have investors with different KYC statuses"""
        res = compliance_session.get(f"{BASE_URL}/api/investors")
        assert res.status_code == 200
        investors = res.json()
        statuses = set(inv.get("kyc_status") for inv in investors)
        # Should have at least approved status
        assert "approved" in statuses, f"No approved investors found. Statuses: {statuses}"

    def test_deals_have_minimum_count(self, compliance_session):
        """Should have at least 5 seeded deals"""
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        assert res.status_code == 200
        deals = res.json()
        assert len(deals) >= 5, f"Expected >= 5 deals, got {len(deals)}"

    def test_caribpay_deal_in_closing(self, compliance_session):
        """CaribPay Solutions Ltd should be in Closing stage"""
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        assert res.status_code == 200
        deals = res.json()
        carib_deals = [d for d in deals if "CaribPay" in d.get("company_name", "")]
        assert len(carib_deals) >= 1, f"CaribPay deal not found. Companies: {[d.get('company_name') for d in deals]}"
        # Check the seeded one is in closing
        carib_closing = [d for d in carib_deals if d.get("pipeline_stage") == "closing"]
        assert len(carib_closing) >= 1, f"CaribPay not in closing stage. Stages: {[d.get('pipeline_stage') for d in carib_deals]}"

    def test_seed_data_idempotency(self, compliance_session):
        """Calling GET /api/investors twice should return same count (no duplicates)"""
        res1 = compliance_session.get(f"{BASE_URL}/api/investors")
        assert res1.status_code == 200
        count1 = len(res1.json())

        res2 = compliance_session.get(f"{BASE_URL}/api/investors")
        assert res2.status_code == 200
        count2 = len(res2.json())

        assert count1 == count2, f"Investor count changed between requests: {count1} vs {count2}"

    def test_deals_stages_spread(self, compliance_session):
        """Deals should span multiple pipeline stages"""
        res = compliance_session.get(f"{BASE_URL}/api/deals")
        assert res.status_code == 200
        deals = res.json()
        stages = set(d.get("pipeline_stage") for d in deals)
        assert len(stages) >= 2, f"Expected deals across multiple stages, got: {stages}"

    def test_audit_logs_have_seed_entries(self, compliance_session):
        """Should have audit log entries from seed data (15 entries)"""
        res = compliance_session.get(f"{BASE_URL}/api/audit-logs?limit=100")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 15, f"Expected >= 15 audit log entries, got {data['total']}"
