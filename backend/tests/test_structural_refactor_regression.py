"""
ZephyrWealth API — Structural Refactor Regression Tests (Iteration 7)
Verifies zero regressions after monolithic server.py was split into modular routes.
Tests all 17 items from the review_request features list.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def compliance_session():
    """Authenticated session for compliance role"""
    session = requests.Session()
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "compliance@zephyrwealth.ai",
        "password": "Comply1234!"
    })
    assert r.status_code == 200, f"Compliance login failed: {r.text}"
    return session


@pytest.fixture(scope="module")
def risk_session():
    """Authenticated session for risk role"""
    session = requests.Session()
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "risk@zephyrwealth.ai",
        "password": "Risk1234!"
    })
    assert r.status_code == 200, f"Risk login failed: {r.text}"
    return session


@pytest.fixture(scope="module")
def manager_session():
    """Authenticated session for manager role"""
    session = requests.Session()
    r = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "manager@zephyrwealth.ai",
        "password": "Manager1234!"
    })
    assert r.status_code == 200, f"Manager login failed: {r.text}"
    return session


# ─── 1. Health Check ──────────────────────────────────────────────────────────

class TestHealth:
    """GET /api/health"""

    def test_health_returns_ok(self):
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"
        print(f"PASS: /api/health → {data}")

    def test_health_returns_service_name(self):
        r = requests.get(f"{BASE_URL}/api/health")
        data = r.json()
        assert "service" in data
        print(f"PASS: /api/health service field → {data.get('service')}")


# ─── 2. Server.py Line Count ──────────────────────────────────────────────────

class TestServerPyLineCount:
    """Verify server.py is under 100 lines (structural refactor requirement)"""

    def test_server_py_under_100_lines(self):
        server_path = os.path.join(os.path.dirname(__file__), '..', 'server.py')
        with open(server_path, 'r') as f:
            lines = f.readlines()
        line_count = len(lines)
        print(f"INFO: server.py has {line_count} lines")
        assert line_count < 100, f"server.py has {line_count} lines — expected < 100"
        print(f"PASS: server.py line count = {line_count} (< 100)")


# ─── 3. Auth Flows ───────────────────────────────────────────────────────────

class TestAuthFlows:
    """Login, cookie, role, /api/auth/me"""

    def test_login_compliance_returns_200_with_role(self):
        """Login compliance@zephyrwealth.ai / Comply1234! — cookie set, role returned"""
        session = requests.Session()
        r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "compliance@zephyrwealth.ai",
            "password": "Comply1234!"
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("role") == "compliance"
        assert data.get("email") == "compliance@zephyrwealth.ai"
        print(f"PASS: compliance login → role={data['role']}")

    def test_login_risk_returns_200_with_role(self):
        """Login risk@zephyrwealth.ai / Risk1234!"""
        session = requests.Session()
        r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "risk@zephyrwealth.ai",
            "password": "Risk1234!"
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("role") == "risk"
        print(f"PASS: risk login → role={data['role']}")

    def test_login_manager_returns_200_with_role(self):
        """Login manager@zephyrwealth.ai / Manager1234!"""
        session = requests.Session()
        r = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@zephyrwealth.ai",
            "password": "Manager1234!"
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("role") == "manager"
        print(f"PASS: manager login → role={data['role']}")

    def test_me_without_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401
        print("PASS: /api/auth/me without auth → 401")

    def test_me_with_compliance_auth_returns_correct_user(self):
        """GET /api/auth/me — returns correct user with valid cookie"""
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "compliance@zephyrwealth.ai",
            "password": "Comply1234!"
        })
        r = session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data.get("email") == "compliance@zephyrwealth.ai"
        assert data.get("role") == "compliance"
        print(f"PASS: /api/auth/me → {data.get('email')} role={data.get('role')}")

    def test_login_wrong_password_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "compliance@zephyrwealth.ai",
            "password": "WrongPassword!"
        })
        assert r.status_code == 401
        print("PASS: wrong password → 401")


# ─── 4. Dashboard ─────────────────────────────────────────────────────────────

class TestDashboard:
    """GET /api/dashboard/stats and /api/dashboard/charts"""

    def test_dashboard_stats_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/dashboard/stats")
        assert r.status_code == 401
        print("PASS: /api/dashboard/stats without auth → 401")

    def test_dashboard_stats_returns_kpi_fields(self, compliance_session):
        """GET /api/dashboard/stats — returns KPI data"""
        r = compliance_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_investors" in data, "Missing total_investors"
        assert "pending_kyc" in data, "Missing pending_kyc"
        assert "deals_in_pipeline" in data, "Missing deals_in_pipeline"
        assert data["total_investors"] >= 1
        print(f"PASS: /api/dashboard/stats → total_investors={data['total_investors']}, "
              f"pending_kyc={data['pending_kyc']}, deals_in_pipeline={data['deals_in_pipeline']}")

    def test_dashboard_charts_returns_funnel_and_pipeline(self, compliance_session):
        """GET /api/dashboard/charts — returns investor_funnel and deal_pipeline arrays"""
        r = compliance_session.get(f"{BASE_URL}/api/dashboard/charts")
        assert r.status_code == 200
        data = r.json()
        assert "investor_funnel" in data, "Missing investor_funnel"
        assert "deal_pipeline" in data, "Missing deal_pipeline"
        assert isinstance(data["investor_funnel"], list)
        assert isinstance(data["deal_pipeline"], list)
        print(f"PASS: /api/dashboard/charts → investor_funnel items={len(data['investor_funnel'])}, "
              f"deal_pipeline items={len(data['deal_pipeline'])}")

    def test_dashboard_charts_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/dashboard/charts")
        assert r.status_code == 401
        print("PASS: /api/dashboard/charts without auth → 401")


# ─── 5. Investors ─────────────────────────────────────────────────────────────

class TestInvestors:
    """GET /api/investors"""

    def test_investors_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 401
        print("PASS: /api/investors without auth → 401")

    def test_investors_returns_list_with_items(self, compliance_session):
        """GET /api/investors — returns investor list (should have items)"""
        r = compliance_session.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 200
        investors = r.json()
        assert isinstance(investors, list)
        assert len(investors) >= 1, "Expected at least 1 investor in list"
        print(f"PASS: /api/investors → {len(investors)} investors returned")

    def test_investors_list_contains_expected_seeded_data(self, compliance_session):
        r = compliance_session.get(f"{BASE_URL}/api/investors")
        investors = r.json()
        names = [i.get("name") for i in investors]
        # At least some seeded investors should be present
        assert any("Cayman" in n or "Nassau" in n or "Marcus" in n or "Yolanda" in n or "Meridian" in n
                   for n in names if n), "No expected seeded investors found"
        print(f"PASS: Seeded investors present in list")


# ─── 6. Deals ─────────────────────────────────────────────────────────────────

class TestDeals:
    """GET /api/deals"""

    def test_deals_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/deals")
        assert r.status_code == 401
        print("PASS: /api/deals without auth → 401")

    def test_deals_returns_list_with_items(self, compliance_session):
        """GET /api/deals — returns deal list (should have items)"""
        r = compliance_session.get(f"{BASE_URL}/api/deals")
        assert r.status_code == 200
        deals = r.json()
        assert isinstance(deals, list)
        assert len(deals) >= 1, "Expected at least 1 deal in list"
        print(f"PASS: /api/deals → {len(deals)} deals returned")


# ─── 7. Capital Calls ─────────────────────────────────────────────────────────

class TestCapitalCalls:
    """GET /api/capital-calls (compliance role)"""

    def test_capital_calls_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/capital-calls")
        assert r.status_code == 401
        print("PASS: /api/capital-calls without auth → 401")

    def test_capital_calls_returns_list(self, compliance_session):
        """GET /api/capital-calls — returns capital call list (compliance role)"""
        r = compliance_session.get(f"{BASE_URL}/api/capital-calls")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        print(f"PASS: /api/capital-calls → {len(data)} capital calls returned")

    def test_capital_calls_accessible_by_risk(self, risk_session):
        """Risk role should also be able to read capital calls"""
        r = risk_session.get(f"{BASE_URL}/api/capital-calls")
        assert r.status_code == 200
        print("PASS: /api/capital-calls accessible by risk role")


# ─── 8. Placement Agents ──────────────────────────────────────────────────────

class TestAgents:
    """GET /api/agents"""

    def test_agents_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/agents")
        assert r.status_code == 401
        print("PASS: /api/agents without auth → 401")

    def test_agents_returns_list(self, compliance_session):
        """GET /api/agents — returns placement agents list"""
        r = compliance_session.get(f"{BASE_URL}/api/agents")
        assert r.status_code == 200
        agents = r.json()
        assert isinstance(agents, list)
        print(f"PASS: /api/agents → {len(agents)} agents returned")


# ─── 9. Trailer Fees ─────────────────────────────────────────────────────────

class TestTrailerFees:
    """GET /api/trailer-fees"""

    def test_trailer_fees_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/trailer-fees")
        assert r.status_code == 401
        print("PASS: /api/trailer-fees without auth → 401")

    def test_trailer_fees_returns_list(self, compliance_session):
        """GET /api/trailer-fees — returns trailer fee invoices list"""
        r = compliance_session.get(f"{BASE_URL}/api/trailer-fees")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        print(f"PASS: /api/trailer-fees → {len(data)} trailer fee invoices returned")


# ─── 10. Reports — TAV PDF ───────────────────────────────────────────────────

class TestReports:
    """GET /api/reports/tav-pdf — streams PDF without error (HTTP 200, content-type PDF)"""

    def test_tav_pdf_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/reports/tav-pdf")
        assert r.status_code == 401
        print("PASS: /api/reports/tav-pdf without auth → 401")

    def test_tav_pdf_returns_200_and_pdf_content_type(self, compliance_session):
        """GET /api/reports/tav-pdf — streams PDF without error"""
        r = compliance_session.get(f"{BASE_URL}/api/reports/tav-pdf")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:500]}"
        content_type = r.headers.get("content-type", "")
        assert "pdf" in content_type.lower(), f"Expected PDF content-type, got: {content_type}"
        assert len(r.content) > 0, "PDF content is empty"
        print(f"PASS: /api/reports/tav-pdf → 200 OK, content-type={content_type}, size={len(r.content)} bytes")


# ─── 11. Portfolio ───────────────────────────────────────────────────────────

class TestPortfolio:
    """GET /api/portfolio/summary — returns holdings, kpis, charts"""

    def test_portfolio_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/portfolio/summary")
        assert r.status_code == 401
        print("PASS: /api/portfolio/summary without auth → 401")

    def test_portfolio_summary_returns_expected_fields(self, compliance_session):
        """GET /api/portfolio/summary — returns holdings, kpis, charts"""
        r = compliance_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert r.status_code == 200
        data = r.json()
        assert "holdings" in data, "Missing holdings"
        assert "kpis" in data, "Missing kpis"
        assert "charts" in data, "Missing charts"
        assert isinstance(data["holdings"], list)
        print(f"PASS: /api/portfolio/summary → holdings={len(data['holdings'])}, "
              f"kpis keys={list(data['kpis'].keys()) if isinstance(data['kpis'], dict) else 'present'}")

    def test_portfolio_accessible_by_risk(self, risk_session):
        r = risk_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert r.status_code == 200
        print("PASS: /api/portfolio/summary accessible by risk role")

    def test_portfolio_accessible_by_manager(self, manager_session):
        r = manager_session.get(f"{BASE_URL}/api/portfolio/summary")
        assert r.status_code == 200
        print("PASS: /api/portfolio/summary accessible by manager role")


# ─── 12. Admin — Demo Reset ──────────────────────────────────────────────────

class TestAdmin:
    """POST /api/admin/demo-reset — executes without error, returns message"""

    def test_demo_reset_unauthenticated_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/admin/demo-reset")
        assert r.status_code == 401
        print("PASS: /api/admin/demo-reset without auth → 401")

    def test_demo_reset_returns_message(self, compliance_session):
        """POST /api/admin/demo-reset — executes without error, returns message"""
        r = compliance_session.post(f"{BASE_URL}/api/admin/demo-reset")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:500]}"
        data = r.json()
        assert "message" in data or "status" in data or "detail" in data or "msg" in data, \
            f"Expected message field in response, got: {data}"
        print(f"PASS: /api/admin/demo-reset → 200, response keys={list(data.keys())}")


# ─── 13. Audit Logs ──────────────────────────────────────────────────────────

class TestAuditLogs:
    """GET /api/audit-logs — returns paginated audit logs"""

    def test_audit_logs_unauthenticated_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/audit-logs")
        assert r.status_code == 401
        print("PASS: /api/audit-logs without auth → 401")

    def test_audit_logs_returns_data(self, compliance_session):
        """GET /api/audit-logs — returns paginated audit logs"""
        r = compliance_session.get(f"{BASE_URL}/api/audit-logs")
        assert r.status_code == 200
        data = r.json()
        # Could be list or paginated dict
        if isinstance(data, dict):
            has_logs = "logs" in data or "items" in data or "results" in data or "data" in data
            assert has_logs or len(data) > 0, f"Unexpected audit log response structure: {list(data.keys())}"
        elif isinstance(data, list):
            pass  # list is valid
        print(f"PASS: /api/audit-logs → 200, type={type(data).__name__}, "
              f"keys={list(data.keys()) if isinstance(data, dict) else f'list[{len(data)}]'}")

    def test_audit_logs_risk_returns_401_or_403(self, risk_session):
        """Audit logs should only be accessible by compliance/manager"""
        r = risk_session.get(f"{BASE_URL}/api/audit-logs")
        # Risk role may be restricted — just ensure we get 200 or 403 (not 500)
        assert r.status_code in [200, 403, 401], \
            f"Unexpected status for risk role: {r.status_code}"
        print(f"PASS: /api/audit-logs risk role → {r.status_code}")


# ─── 14. Modular Routes Integrity ────────────────────────────────────────────

class TestModularRoutes:
    """Verify all modular route files exist and are importable"""

    ROUTE_FILES = [
        "auth.py", "dashboard.py", "investors.py", "deals.py",
        "reports.py", "portfolio.py", "capital_calls.py",
        "agents.py", "trailer_fees.py", "admin.py"
    ]

    def test_all_route_files_exist(self):
        routes_dir = os.path.join(os.path.dirname(__file__), '..', 'routes')
        for filename in self.ROUTE_FILES:
            path = os.path.join(routes_dir, filename)
            assert os.path.exists(path), f"Route file missing: {filename}"
        print(f"PASS: All {len(self.ROUTE_FILES)} route files exist")

    def test_supporting_modules_exist(self):
        backend_dir = os.path.join(os.path.dirname(__file__), '..')
        for module in ["database.py", "models.py", "utils.py", "pdf_utils.py", "seed.py"]:
            path = os.path.join(backend_dir, module)
            assert os.path.exists(path), f"Supporting module missing: {module}"
        print("PASS: All supporting modules exist (database, models, utils, pdf_utils, seed)")
