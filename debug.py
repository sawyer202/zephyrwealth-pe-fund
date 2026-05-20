#!/usr/bin/env python3
"""
🔍 ZephyrWealth Back-Office Data Debug Script (Python)
Diagnoses why back-office dashboard shows no data while investor portal works.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# Color codes
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}🔍 {text}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")

def print_section(text):
    print(f"\n{CYAN}▶ {text}{RESET}")
    print(f"{CYAN}{'-'*70}{RESET}")

def check_pass(text):
    print(f"{GREEN}✓{RESET} {text}")

def check_fail(text, action):
    print(f"{RED}✗{RESET} {text}")
    print(f"{YELLOW}  Action: {action}{RESET}")

def check_warn(text, action=""):
    print(f"{YELLOW}⚠{RESET} {text}")
    if action:
        print(f"{YELLOW}  Action: {action}{RESET}")

def load_env():
    """Load environment variables from .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        check_fail("Missing .env file", "Copy .env.example to .env and fill in values")
        return None
    
    env = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, val = line.split('=', 1)
            env[key.strip()] = val.strip()
    
    return env

def check_mongodb(mongo_url, db_name):
    """Check MongoDB connectivity and data."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def check():
            try:
                client = AsyncIOMotorClient(mongo_url)
                db = client[db_name]
                
                # Test connection
                await db.command('ping')
                
                # Get counts
                users = await db.users.count_documents({})
                investors = await db.investors.count_documents({})
                deals = await db.deals.count_documents({})
                
                # Get sample user
                sample_user = await db.users.find_one({})
                
                client.close()
                
                return {
                    'connected': True,
                    'users': users,
                    'investors': investors,
                    'deals': deals,
                    'sample_user': sample_user
                }
            except Exception as e:
                return {
                    'connected': False,
                    'error': str(e)
                }
        
        # Run async check
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(check())
        loop.close()
        
        return result
    
    except ImportError:
        check_warn("Motor library not installed", "Run: pip install motor")
        return {'connected': False, 'error': 'Motor not installed'}
    except Exception as e:
        return {'connected': False, 'error': str(e)}

def check_backend(backend_url):
    """Check if backend is running."""
    try:
        import requests
        response = requests.get(f"{backend_url}/health", timeout=2)
        if response.status_code == 200:
            return {'running': True, 'response': response.json()}
        else:
            return {'running': False, 'status': response.status_code}
    except Exception as e:
        return {'running': False, 'error': str(e)}

def test_login(backend_url, email, password):
    """Test back-office login."""
    try:
        import requests
        response = requests.post(
            f"{backend_url}/api/auth/login",
            json={"email": email, "password": password},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return {'success': True, 'user': data}
        else:
            return {'success': False, 'status': response.status_code, 'response': response.text}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def test_api(backend_url, endpoint, cookies=None):
    """Test API endpoint."""
    try:
        import requests
        response = requests.get(
            f"{backend_url}{endpoint}",
            cookies=cookies,
            timeout=5
        )
        if response.status_code == 200:
            return {'success': True, 'data': response.json()}
        else:
            return {'success': False, 'status': response.status_code, 'response': response.text}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def main():
    print_header("ZephyrWealth Back-Office Data Debug")
    
    # Step 1: Load environment
    print_section("Step 1: Environment Variables")
    env = load_env()
    if not env:
        sys.exit(1)
    
    mongo_url = env.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = env.get('DB_NAME', 'zephyrwealth')
    backend_url = env.get('REACT_APP_BACKEND_URL', 'http://localhost:5000')
    
    check_pass(f"MONGO_URL: {mongo_url}")
    check_pass(f"DB_NAME: {db_name}")
    check_pass(f"Backend URL: {backend_url}")
    
    # Step 2: Check backend
    print_section("Step 2: Backend Status")
    backend_status = check_backend(backend_url)
    if backend_status['running']:
        check_pass(f"Backend running at {backend_url}")
        check_pass(f"Version: {backend_status['response'].get('version', 'N/A')}")
    else:
        check_fail(
            f"Backend not responding at {backend_url}",
            f"Start backend: cd backend && python3 -m uvicorn server:app --reload --port 5000"
        )
        sys.exit(1)
    
    # Step 3: Check MongoDB
    print_section("Step 3: MongoDB Status")
    mongo_status = check_mongodb(mongo_url, db_name)
    
    if not mongo_status['connected']:
        check_fail(
            f"MongoDB connection failed: {mongo_status.get('error')}",
            "Start MongoDB or check connection string"
        )
        sys.exit(1)
    
    users_count = mongo_status['users']
    investors_count = mongo_status['investors']
    deals_count = mongo_status['deals']
    
    check_pass(f"MongoDB connected to {db_name}")
    
    if users_count >= 3:
        check_pass(f"Back-office users: {users_count} ✓")
    else:
        check_fail(
            f"Back-office users: {users_count} (expected 3+)",
            "See reseed instructions below"
        )
    
    if investors_count >= 6:
        check_pass(f"Investors: {investors_count} ✓")
    else:
        check_fail(
            f"Investors: {investors_count} (expected 6+)",
            "See reseed instructions below"
        )
    
    if deals_count >= 5:
        check_pass(f"Deals: {deals_count} ✓")
    else:
        check_fail(
            f"Deals: {deals_count} (expected 5+)",
            "See reseed instructions below"
        )
    
    # Show sample user
    if mongo_status.get('sample_user'):
        print(f"\n  Sample user: {mongo_status['sample_user'].get('email', 'N/A')} ({mongo_status['sample_user'].get('role', 'N/A')})")
    
    # Step 4: Test login
    print_section("Step 4: Back-Office Authentication")
    login_result = test_login(backend_url, "compliance@zephyrwealth.ai", "Comply1234!")
    
    if login_result['success']:
        check_pass("Login successful")
        user = login_result['user']
        check_pass(f"Logged in as: {user.get('name', 'Unknown')} ({user.get('role', 'N/A')})")
        token = user.get('access_token', '')
    else:
        check_fail(
            f"Login failed: {login_result.get('status') or login_result.get('error')}",
            "Check if users are seeded or credentials are correct"
        )
        if login_result.get('response'):
            print(f"  Response: {login_result['response'][:200]}")
        token = None
    
    # Step 5: Test APIs
    if token:
        print_section("Step 5: Back-Office APIs")
        
        cookies = {'access_token': token}
        
        # Test dashboard stats
        print(f"\n  Testing GET /api/dashboard/stats...")
        stats_result = test_api(backend_url, '/api/dashboard/stats', cookies)
        if stats_result['success']:
            stats = stats_result['data']
            check_pass(f"Dashboard stats OK")
            check_pass(f"  • Total investors: {stats.get('total_investors', 0)}")
            check_pass(f"  • Pending KYC: {stats.get('pending_kyc', 0)}")
            check_pass(f"  • Deals in pipeline: {stats.get('deals_in_pipeline', 0)}")
            check_pass(f"  • Total committed capital: ${stats.get('total_committed_capital', 0):,.0f}")
        else:
            check_fail(
                f"Dashboard stats failed: {stats_result.get('status') or stats_result.get('error')}",
                "Check backend logs"
            )
        
        # Test investors
        print(f"\n  Testing GET /api/investors...")
        investors_result = test_api(backend_url, '/api/investors', cookies)
        if investors_result['success']:
            investors_list = investors_result['data']
            if isinstance(investors_list, list) and len(investors_list) > 0:
                check_pass(f"Investors endpoint OK ({len(investors_list)} records)")
                first_inv = investors_list[0]
                check_pass(f"  • First investor: {first_inv.get('name', 'N/A')}")
            else:
                check_fail(
                    "Investors endpoint returned empty array",
                    "Database has investors but API returns empty list"
                )
        else:
            check_fail(
                f"Investors endpoint failed: {investors_result.get('status') or investors_result.get('error')}",
                "Check backend logs"
            )
        
        # Test deals
        print(f"\n  Testing GET /api/deals...")
        deals_result = test_api(backend_url, '/api/deals', cookies)
        if deals_result['success']:
            deals_list = deals_result['data']
            if isinstance(deals_list, list) and len(deals_list) > 0:
                check_pass(f"Deals endpoint OK ({len(deals_list)} records)")
                first_deal = deals_list[0]
                check_pass(f"  • First deal: {first_deal.get('company_name', 'N/A')}")
            else:
                check_fail(
                    "Deals endpoint returned empty array",
                    "Database has deals but API returns empty list"
                )
        else:
            check_fail(
                f"Deals endpoint failed: {deals_result.get('status') or deals_result.get('error')}",
                "Check backend logs"
            )
    
    # Step 6: Recommendations
    print_section("Step 6: Recommendations")
    
    if users_count < 3 or investors_count < 6 or deals_count < 5:
        print(f"\n{YELLOW}⚠ DATA NOT FULLY SEEDED{RESET}\n")
        print("Force reseed with these steps:")
        print("  1. Stop the backend (Ctrl+C)")
        print("  2. Delete database:")
        print("     $ mongo")
        print("     > use zephyrwealth")
        print("     > db.dropDatabase()")
        print("     > exit")
        print("  3. Start backend again:")
        print("     $ cd backend")
        print("     $ python3 -m uvicorn server:app --reload --port 5000")
        print("  4. Wait for: 'ZephyrWealth API v6 ready — Investor Portal enabled'")
    
    if token:
        print(f"\n{GREEN}✓ READY TO USE!{RESET}\n")
        print("The back-office dashboard should now display data:")
        print("  1. Open: http://localhost:3000")
        print("  2. Login with:")
        print("     • Email: compliance@zephyrwealth.ai")
        print("     • Password: Comply1234!")
        print("  3. You should see dashboard with stats and charts")
    
    print_section("Debug Complete")
    print(f"{GREEN}✓ All diagnostics finished{RESET}\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Debug interrupted by user{RESET}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
