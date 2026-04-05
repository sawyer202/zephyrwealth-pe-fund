"""
Phase 5 — Capital Calls & Trailer Fee Automation Tests
Tests: Placement Agents, Capital Calls, Trailer Fees, Dashboard KPIs, Portfolio capital_by_class
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def compliance_session():
    """Authenticated session as compliance officer"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "compliance@zephyrwealth.ai",
        "password": "Comply1234!"
    })
    if resp.status_code != 200:
        pytest.skip(f"Compliance auth failed: {resp.status_code} {resp.text}")
    return session

@pytest.fixture(scope="module")
def risk_session():
    """Authenticated session as risk officer"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "risk@zephyrwealth.ai",
        "password": "Risk1234!"
    })
    if resp.status_code != 200:
        pytest.skip(f"Risk auth failed: {resp.status_code} {resp.text}")
    return session

@pytest.fixture(scope="module")
def manager_session():
    """Authenticated session as fund manager"""
    session = requests.Session()
    resp = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "manager@zephyrwealth.ai",
        "password": "Manager1234!"
    })
    if resp.status_code != 200:
        pytest.skip(f"Manager auth failed: {resp.status_code} {resp.text}")
    return session


# ─── Helpers ────────────────────────────────────────────────────────────────

def get_agent_ids(session):
    """Returns list of agent IDs from seeded data"""
    resp = session.get(f"{BASE_URL}/api/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 2
    return [ag["id"] for ag in agents]

def get_capital_call_ids(session):
    """Returns list of capital call IDs from seeded data"""
    resp = session.get(f"{BASE_URL}/api/capital-calls")
    assert resp.status_code == 200
    calls = resp.json()
    assert len(calls) >= 2
    return [c["id"] for c in calls]

def get_trailer_fee_ids(session):
    """Returns list of trailer fee IDs"""
    resp = session.get(f"{BASE_URL}/api/trailer-fees")
    assert resp.status_code == 200
    fees = resp.json()
    assert len(fees) >= 1
    return [f["id"] for f in fees]


# ─── Placement Agent Tests ───────────────────────────────────────────────────

class TestAgents:
    """GET /api/agents — seeded agents, linked_investors count"""

    def test_get_agents_returns_200_compliance(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/agents")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_get_agents_returns_at_least_2_seeded(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/agents")
        data = resp.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 2, f"Expected >= 2 agents, got {len(data)}"

    def test_get_agents_has_island_capital(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/agents")
        names = [ag["agent_name"] for ag in resp.json()]
        assert any("Island Capital" in n for n in names), f"Island Capital Advisors not found. Got: {names}"

    def test_get_agents_has_caribbean_wealth(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/agents")
        names = [ag["agent_name"] for ag in resp.json()]
        assert any("Caribbean" in n for n in names), f"Caribbean Wealth Partners not found. Got: {names}"

    def test_get_agents_has_linked_investors_count(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/agents")
        for ag in resp.json():
            assert "linked_investors" in ag, f"Agent {ag.get('agent_name')} missing linked_investors"
            assert isinstance(ag["linked_investors"], (int, float)), "linked_investors should be numeric"

    def test_get_agents_has_total_fees_invoiced(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/agents")
        for ag in resp.json():
            assert "total_fees_invoiced" in ag, f"Agent {ag.get('agent_name')} missing total_fees_invoiced"

    def test_get_agents_risk_can_access(self, risk_session):
        resp = risk_session.get(f"{BASE_URL}/api/agents")
        assert resp.status_code == 200, f"Risk should access agents; got {resp.status_code}"

    def test_post_agent_creates_new_compliance_only(self, compliance_session):
        payload = {
            "agent_name": "TEST_Agent Alpha",
            "company_name": "TEST_Agent Alpha Ltd",
            "email": "test_alpha@agent.com",
            "phone": "+1 242-555-0999",
            "bank_name": "TEST Bank",
            "bank_account_number": "TEST12345",
            "swift_code": "TESTSWFT",
            "vat_registered": False,
            "vat_number": None
        }
        resp = compliance_session.post(f"{BASE_URL}/api/agents", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["agent_name"] == "TEST_Agent Alpha"
        assert "id" in data

    def test_post_agent_forbidden_for_risk(self, risk_session):
        payload = {
            "agent_name": "TEST_Risk Agent",
            "company_name": "TEST_Risk Agent Ltd",
            "email": "risktest@agent.com",
            "phone": "+1 242-555-0001",  # Required field
            "bank_name": "TestBank",
            "bank_account_number": "12345",
            "swift_code": "SWFT1234",
            "vat_registered": False,
            "vat_number": None
        }
        resp = risk_session.post(f"{BASE_URL}/api/agents", json=payload)
        assert resp.status_code == 403, f"Risk should not create agents; got {resp.status_code}"

    def test_get_agent_by_id_returns_detail(self, compliance_session):
        agent_ids = get_agent_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/agents/{agent_ids[0]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "agent_name" in data
        assert "linked_investors" in data
        assert isinstance(data["linked_investors"], list), "linked_investors should be list on detail"
        assert "invoices" in data

    def test_get_agent_by_id_island_capital_has_invoice(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/agents")
        agents = resp.json()
        island = next((ag for ag in agents if "Island Capital" in ag.get("agent_name", "")), None)
        if island is None:
            pytest.skip("Island Capital agent not found in DB")
        detail = compliance_session.get(f"{BASE_URL}/api/agents/{island['id']}")
        assert detail.status_code == 200
        data = detail.json()
        assert len(data.get("invoices", [])) >= 1, "Island Capital should have at least 1 invoice"

    def test_patch_agent_updates_field(self, compliance_session):
        agent_ids = get_agent_ids(compliance_session)
        resp = compliance_session.patch(
            f"{BASE_URL}/api/agents/{agent_ids[0]}",
            json={"phone": "+1 999-555-0001"}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"


# ─── Fund Participation Tests ─────────────────────────────────────────────────

class TestFundParticipation:
    """PATCH /api/investors/{id}/fund-participation"""

    def get_approved_investor_id(self, session):
        resp = session.get(f"{BASE_URL}/api/investors")
        assert resp.status_code == 200
        investors = resp.json()
        if isinstance(investors, dict):
            investors = investors.get("investors", [])
        approved = [i for i in investors if i.get("kyc_status") == "approved"]
        if not approved:
            pytest.skip("No approved investors found")
        return approved[0]["id"]

    def test_fund_participation_update_compliance(self, compliance_session):
        investor_id = self.get_approved_investor_id(compliance_session)
        payload = {
            "share_class": "A",
            "committed_capital": 750000,
            "deal_associations": [],
            "placement_agent_id": None
        }
        resp = compliance_session.patch(
            f"{BASE_URL}/api/investors/{investor_id}/fund-participation",
            json=payload
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data.get("share_class") == "A"
        assert data.get("committed_capital") == 750000

    def test_fund_participation_forbidden_for_risk(self, risk_session):
        resp = risk_session.get(f"{BASE_URL}/api/investors")
        investors = resp.json()
        if isinstance(investors, dict):
            investors = investors.get("investors", [])
        if not investors:
            pytest.skip("No investors found")
        investor_id = investors[0]["id"]
        resp = risk_session.patch(
            f"{BASE_URL}/api/investors/{investor_id}/fund-participation",
            json={"share_class": "B", "committed_capital": 100000}
        )
        assert resp.status_code == 403, f"Risk should not update fund participation; got {resp.status_code}"


# ─── Capital Call Tests ───────────────────────────────────────────────────────

class TestCapitalCalls:
    """Capital call CRUD and state management"""

    def test_get_capital_calls_compliance_200(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_get_capital_calls_returns_2_seeded(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2, f"Expected >= 2 capital calls, got {len(data)}"

    def test_get_capital_calls_risk_200(self, risk_session):
        resp = risk_session.get(f"{BASE_URL}/api/capital-calls")
        assert resp.status_code == 200, f"Risk should access capital calls; got {resp.status_code}"

    def test_get_capital_calls_manager_403(self, manager_session):
        resp = manager_session.get(f"{BASE_URL}/api/capital-calls")
        assert resp.status_code == 403, f"Manager should not access capital calls; got {resp.status_code}"

    def test_get_capital_calls_has_q1_drawdown(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls")
        names = [c["call_name"] for c in resp.json()]
        assert any("Q1" in n or "Initial" in n for n in names), f"Q1 drawdown not found. Got: {names}"

    def test_get_capital_calls_has_q2_harbour_house(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls")
        names = [c["call_name"] for c in resp.json()]
        assert any("Q2" in n or "Harbour" in n for n in names), f"Q2 Harbour House not found. Got: {names}"

    def test_get_capital_calls_has_pct_received(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls")
        for call in resp.json():
            assert "pct_received" in call, f"Capital call missing pct_received: {call.get('call_name')}"

    def test_post_capital_call_creates_draft(self, compliance_session):
        """POST /api/capital-calls creates draft with correct line items"""
        import datetime
        due = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        payload = {
            "call_name": "TEST_Q3 2026 Draft",
            "call_type": "fund_level",
            "target_classes": ["A"],
            "call_percentage": 10,
            "due_date": due,
            "deal_id": None
        }
        resp = compliance_session.post(f"{BASE_URL}/api/capital-calls", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["status"] == "draft", f"Expected draft status, got {data.get('status')}"
        assert data["call_name"] == "TEST_Q3 2026 Draft"
        assert "line_items" in data
        # Class A investors should appear in line items
        assert len(data["line_items"]) >= 2, f"Expected >=2 Class A investors, got {len(data['line_items'])}"
        return data["id"]

    def test_post_capital_call_line_items_have_correct_fields(self, compliance_session):
        import datetime
        due = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        payload = {
            "call_name": "TEST_Line Item Check",
            "call_type": "fund_level",
            "target_classes": ["A"],
            "call_percentage": 5,
            "due_date": due,
            "deal_id": None
        }
        resp = compliance_session.post(f"{BASE_URL}/api/capital-calls", json=payload)
        assert resp.status_code == 200
        for li in resp.json().get("line_items", []):
            assert "investor_id" in li
            assert "investor_name" in li
            assert "call_amount" in li
            assert "committed_capital" in li
            assert "status" in li
            assert li["status"] == "pending"

    def test_post_capital_call_forbidden_for_risk(self, risk_session):
        import datetime
        due = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        resp = risk_session.post(f"{BASE_URL}/api/capital-calls", json={
            "call_name": "TEST_Risk Call",
            "call_type": "fund_level",
            "target_classes": ["A"],
            "call_percentage": 10,
            "due_date": due,
        })
        assert resp.status_code == 403, f"Risk should not create capital calls; got {resp.status_code}"

    def test_issue_capital_call(self, compliance_session):
        """POST /api/capital-calls/{id}/issue issues a draft call"""
        import datetime
        due = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        # Create draft first
        create_resp = compliance_session.post(f"{BASE_URL}/api/capital-calls", json={
            "call_name": "TEST_Issue Call",
            "call_type": "fund_level",
            "target_classes": ["A"],
            "call_percentage": 1,
            "due_date": due,
        })
        assert create_resp.status_code == 200
        draft_id = create_resp.json()["id"]

        # Issue it
        issue_resp = compliance_session.post(f"{BASE_URL}/api/capital-calls/{draft_id}/issue")
        assert issue_resp.status_code == 200, f"Expected 200, got {issue_resp.status_code}: {issue_resp.text}"

        # Verify it's now issued
        get_resp = compliance_session.get(f"{BASE_URL}/api/capital-calls/{draft_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["status"] == "issued", f"Expected issued, got {get_resp.json().get('status')}"

    def test_issue_already_issued_call_fails(self, compliance_session):
        """Cannot re-issue an already issued capital call"""
        call_ids = get_capital_call_ids(compliance_session)
        # Try to re-issue an already-issued call
        resp = compliance_session.post(f"{BASE_URL}/api/capital-calls/{call_ids[0]}/issue")
        assert resp.status_code == 400, f"Re-issuing should fail with 400; got {resp.status_code}"

    def test_get_capital_call_by_id_returns_detail(self, compliance_session):
        call_ids = get_capital_call_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls/{call_ids[0]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "line_items" in data
        assert "status" in data
        assert "call_name" in data
        assert len(data["line_items"]) > 0

    def test_get_capital_call_line_items_have_accrued_interest_for_defaulted(self, compliance_session):
        """GET /api/capital-calls/{id} returns accrued_interest for defaulted items"""
        call_ids = get_capital_call_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls/{call_ids[0]}")
        assert resp.status_code == 200
        for li in resp.json().get("line_items", []):
            assert "accrued_interest" in li, f"Line item missing accrued_interest: {li.get('investor_name')}"
            assert "days_overdue" in li

    def test_patch_line_item_mark_received(self, compliance_session):
        """PATCH /api/capital-calls/{id}/line-items/{investor_id} marks as received"""
        call_ids = get_capital_call_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls/{call_ids[0]}")
        assert resp.status_code == 200
        line_items = resp.json().get("line_items", [])
        if not line_items:
            pytest.skip("No line items found")
        # Find a line item to update
        li = line_items[0]
        investor_id = li["investor_id"]
        patch_resp = compliance_session.patch(
            f"{BASE_URL}/api/capital-calls/{call_ids[0]}/line-items/{investor_id}",
            json={"status": "received"}
        )
        assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}: {patch_resp.text}"

    def test_patch_line_item_mark_defaulted(self, compliance_session):
        """PATCH /api/capital-calls/{id}/line-items/{investor_id} marks as defaulted"""
        call_ids = get_capital_call_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls/{call_ids[0]}")
        assert resp.status_code == 200
        line_items = resp.json().get("line_items", [])
        if not line_items:
            pytest.skip("No line items found")
        li = line_items[0]
        investor_id = li["investor_id"]
        patch_resp = compliance_session.patch(
            f"{BASE_URL}/api/capital-calls/{call_ids[0]}/line-items/{investor_id}",
            json={"status": "defaulted"}
        )
        assert patch_resp.status_code == 200, f"Expected 200, got {patch_resp.status_code}: {patch_resp.text}"
        # Reset to received
        compliance_session.patch(
            f"{BASE_URL}/api/capital-calls/{call_ids[0]}/line-items/{investor_id}",
            json={"status": "received"}
        )

    def test_patch_line_item_forbidden_for_risk(self, risk_session, compliance_session):
        """Risk cannot update line item status"""
        call_ids = get_capital_call_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls/{call_ids[0]}")
        line_items = resp.json().get("line_items", [])
        if not line_items:
            pytest.skip("No line items found")
        investor_id = line_items[0]["investor_id"]
        patch_resp = risk_session.patch(
            f"{BASE_URL}/api/capital-calls/{call_ids[0]}/line-items/{investor_id}",
            json={"status": "received"}
        )
        assert patch_resp.status_code == 403, f"Risk should not update line items; got {patch_resp.status_code}"

    def test_get_notices_returns_pdf_or_zip(self, compliance_session):
        """GET /api/capital-calls/{id}/notices returns PDF or ZIP"""
        call_ids = get_capital_call_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls/{call_ids[0]}/notices")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        ct = resp.headers.get("content-type", "")
        assert "pdf" in ct.lower() or "zip" in ct.lower(), f"Expected PDF or ZIP content-type, got {ct}"
        assert len(resp.content) > 0, "Notice download is empty"

    def test_get_export_csv_returns_csv(self, compliance_session):
        """GET /api/capital-calls/{id}/export-csv returns CSV download"""
        call_ids = get_capital_call_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/capital-calls/{call_ids[0]}/export-csv")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        ct = resp.headers.get("content-type", "")
        assert "csv" in ct.lower() or "text" in ct.lower(), f"Expected CSV content-type, got {ct}"
        assert len(resp.content) > 0, "CSV export is empty"


# ─── Trailer Fee Tests ────────────────────────────────────────────────────────

class TestTrailerFees:
    """Trailer fee invoice generation and management"""

    def test_get_trailer_fees_returns_200(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/trailer-fees")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_get_trailer_fees_has_seeded_invoice(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/trailer-fees")
        data = resp.json()
        assert isinstance(data, list), "Expected list of trailer fees"
        assert len(data) >= 1, f"Expected >= 1 seeded invoice, got {len(data)}"

    def test_get_trailer_fees_has_island_capital_invoice(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/trailer-fees")
        agent_names = [tf.get("agent_name", "") for tf in resp.json()]
        assert any("Island Capital" in n for n in agent_names), f"Island Capital invoice not found. Got: {agent_names}"

    def test_get_trailer_fee_by_id(self, compliance_session):
        tf_ids = get_trailer_fee_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/trailer-fees/{tf_ids[0]}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "agent_name" in data
        assert "total_due" in data
        assert "status" in data

    def test_generate_trailer_fees_creates_drafts(self, compliance_session):
        """POST /api/trailer-fees/generate creates draft invoices for Class C investors"""
        resp = compliance_session.post(
            f"{BASE_URL}/api/trailer-fees/generate",
            json={"year": 2024, "agent_ids": None}
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "count" in data, "Response should have 'count' field"
        assert "invoices" in data, "Response should have 'invoices' list"

    def test_generate_trailer_fees_forbidden_for_risk(self, risk_session):
        resp = risk_session.post(
            f"{BASE_URL}/api/trailer-fees/generate",
            json={"year": 2024, "agent_ids": None}
        )
        assert resp.status_code == 403, f"Risk should not generate trailer fees; got {resp.status_code}"

    def test_get_trailer_fee_pdf_returns_pdf(self, compliance_session):
        """GET /api/trailer-fees/{id}/pdf returns PDF download"""
        tf_ids = get_trailer_fee_ids(compliance_session)
        resp = compliance_session.get(f"{BASE_URL}/api/trailer-fees/{tf_ids[0]}/pdf")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        ct = resp.headers.get("content-type", "")
        assert "pdf" in ct.lower(), f"Expected PDF content-type, got {ct}"
        assert len(resp.content) > 0, "PDF download is empty"

    def test_issue_trailer_fee(self, compliance_session):
        """POST /api/trailer-fees/{id}/issue sets status to issued"""
        # Generate a new draft first
        gen_resp = compliance_session.post(
            f"{BASE_URL}/api/trailer-fees/generate",
            json={"year": 2023, "agent_ids": None}
        )
        assert gen_resp.status_code == 200
        generated = gen_resp.json()
        if generated.get("count", 0) == 0:
            pytest.skip("No trailer fee invoices generated (no eligible Class C investors)")

        invoices = generated.get("invoices", [])
        # Get the first draft invoice ID
        all_tf = compliance_session.get(f"{BASE_URL}/api/trailer-fees").json()
        draft_tf = [tf for tf in all_tf if tf.get("status") == "draft"]
        if not draft_tf:
            pytest.skip("No draft trailer fee invoices to issue")
        tf_id = draft_tf[0]["id"]

        issue_resp = compliance_session.post(f"{BASE_URL}/api/trailer-fees/{tf_id}/issue")
        assert issue_resp.status_code == 200, f"Expected 200, got {issue_resp.status_code}: {issue_resp.text}"

        # Verify it's now issued
        get_resp = compliance_session.get(f"{BASE_URL}/api/trailer-fees/{tf_id}")
        assert get_resp.json().get("status") == "issued", "Trailer fee should be issued"


# ─── Dashboard Stats KPI Tests ────────────────────────────────────────────────

class TestDashboardStats:
    """GET /api/dashboard/stats — capital KPIs"""

    def test_dashboard_stats_returns_200(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_dashboard_stats_has_capital_kpis(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/dashboard/stats")
        data = resp.json()
        assert "total_committed_capital" in data, "Missing total_committed_capital"
        assert "total_capital_called" in data, "Missing total_capital_called"
        assert "total_uncalled" in data, "Missing total_uncalled"
        assert "call_rate" in data, "Missing call_rate"

    def test_dashboard_stats_committed_capital_positive(self, compliance_session):
        """total_committed_capital should be >= 1.4M (approved investors Cayman+Nassau+Marcus)"""
        resp = compliance_session.get(f"{BASE_URL}/api/dashboard/stats")
        data = resp.json()
        committed = data.get("total_committed_capital", 0)
        assert committed >= 1400000.0, f"Expected at least $1,400,000 committed, got ${committed:,.0f}"

    def test_dashboard_stats_called_capital_positive(self, compliance_session):
        """total_capital_called should be >= 630K (two issued capital calls in seed)"""
        resp = compliance_session.get(f"{BASE_URL}/api/dashboard/stats")
        data = resp.json()
        called = data.get("total_capital_called", 0)
        assert called >= 630000.0, f"Expected at least $630,000 called, got ${called:,.0f}"

    def test_dashboard_stats_uncalled_non_negative(self, compliance_session):
        """total_uncalled should equal committed - called"""
        resp = compliance_session.get(f"{BASE_URL}/api/dashboard/stats")
        data = resp.json()
        uncalled = data.get("total_uncalled", -1)
        committed = data.get("total_committed_capital", 0)
        called = data.get("total_capital_called", 0)
        assert uncalled >= 0, f"total_uncalled must be non-negative, got {uncalled}"
        assert abs(uncalled - (committed - called)) < 1.0, f"uncalled ({uncalled}) != committed ({committed}) - called ({called})"

    def test_dashboard_stats_call_rate_valid(self, compliance_session):
        """Call rate should be between 0 and 100 and > 0 since calls have been issued"""
        resp = compliance_session.get(f"{BASE_URL}/api/dashboard/stats")
        data = resp.json()
        call_rate = data.get("call_rate", -1)
        assert 0 < call_rate <= 100, f"Call rate should be 0-100% (issued calls exist), got {call_rate}%"


# ─── Portfolio Summary capital_by_class Tests ─────────────────────────────────

class TestPortfolioCapitalByClass:
    """GET /api/portfolio/summary — capital_by_class chart data"""

    def test_portfolio_summary_returns_200(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_portfolio_summary_has_capital_by_class(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        data = resp.json()
        assert "charts" in data, "Missing charts in portfolio summary"
        charts = data["charts"]
        assert "capital_by_class" in charts, "Missing capital_by_class in charts"

    def test_portfolio_capital_by_class_has_classes(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        capital_by_class = resp.json()["charts"]["capital_by_class"]
        assert isinstance(capital_by_class, list), "capital_by_class should be a list"
        assert len(capital_by_class) >= 2, f"Expected >=2 classes, got {len(capital_by_class)}"

    def test_portfolio_capital_by_class_has_called_uncalled(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        capital_by_class = resp.json()["charts"]["capital_by_class"]
        for cls in capital_by_class:
            assert "class_label" in cls, f"Missing class_label in {cls}"
            assert "called" in cls, f"Missing called in {cls}"
            assert "uncalled" in cls, f"Missing uncalled in {cls}"

    def test_portfolio_kpi_has_total_committed(self, compliance_session):
        """Portfolio page kpi-total-committed = sum of all share class called+uncalled"""
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        capital_by_class = resp.json()["charts"]["capital_by_class"]
        total = sum((c.get("called", 0) or 0) + (c.get("uncalled", 0) or 0) for c in capital_by_class)
        assert total > 0, f"Total committed capital should be > 0, got {total}"

    def test_portfolio_capital_by_class_includes_class_a(self, compliance_session):
        resp = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        capital_by_class = resp.json()["charts"]["capital_by_class"]
        labels = [c.get("class_label", "") for c in capital_by_class]
        assert any("A" in l for l in labels), f"Class A not found in capital_by_class. Labels: {labels}"


# ─── Unauthorized Access Tests ────────────────────────────────────────────────

class TestUnauthorizedAccess:
    """Tests that unauthenticated requests return 401"""

    def test_agents_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/agents")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_capital_calls_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/capital-calls")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    def test_trailer_fees_requires_auth(self):
        resp = requests.get(f"{BASE_URL}/api/trailer-fees")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
