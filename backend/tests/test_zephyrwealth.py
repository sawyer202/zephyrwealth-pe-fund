"""ZephyrWealth API backend tests"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# ─── Health ──────────────────────────────────────────────────────────────────
class TestHealth:
    def test_health_returns_ok(self):
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ok"

# ─── Auth ────────────────────────────────────────────────────────────────────
class TestAuth:
    def test_me_without_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401

    def test_login_compliance_success(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "compliance@zephyrwealth.ai",
            "password": "Comply1234!"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "compliance@zephyrwealth.ai"
        assert data["role"] == "compliance"
        assert "id" in data

    def test_login_risk_success(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "risk@zephyrwealth.ai",
            "password": "Risk1234!"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "risk"

    def test_login_manager_success(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "manager@zephyrwealth.ai",
            "password": "Manager1234!"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "manager"

    def test_login_wrong_credentials_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "compliance@zephyrwealth.ai",
            "password": "WrongPassword!"
        })
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_me_with_auth_returns_user(self):
        session = requests.Session()
        session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "compliance@zephyrwealth.ai",
            "password": "Comply1234!"
        })
        r = session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == "compliance@zephyrwealth.ai"

# ─── Dashboard & Data ─────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def auth_session():
    session = requests.Session()
    session.post(f"{BASE_URL}/api/auth/login", json={
        "email": "compliance@zephyrwealth.ai",
        "password": "Comply1234!"
    })
    return session

class TestDashboard:
    def test_stats_without_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/dashboard/stats")
        assert r.status_code == 401

    def test_stats_with_auth(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/dashboard/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["total_investors"] == 3
        assert data["pending_kyc"] == 1
        assert data["deals_in_pipeline"] == 2
        assert data["flagged_items"] == 1

    def test_investors_with_auth(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 200
        investors = r.json()
        assert len(investors) == 3
        names = [i["name"] for i in investors]
        assert "Castlebrook Family Office" in names
        # Verify scorecard_completed for Castlebrook
        castlebrook = next(i for i in investors if i["name"] == "Castlebrook Family Office")
        assert castlebrook["scorecard_completed"] is True

    def test_deals_with_auth(self, auth_session):
        r = auth_session.get(f"{BASE_URL}/api/deals")
        assert r.status_code == 200
        deals = r.json()
        assert len(deals) == 2

    def test_investors_without_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/investors")
        assert r.status_code == 401

    def test_deals_without_auth_returns_401(self):
        r = requests.get(f"{BASE_URL}/api/deals")
        assert r.status_code == 401
