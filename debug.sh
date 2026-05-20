#!/bin/bash
# 🔍 ZephyrWealth Back-Office Data Debug Script
# This script diagnoses why the back-office dashboard shows no data
# while the investor portal works fine.

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
  echo ""
  echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}🔍 $1${NC}"
  echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
  echo ""
}

print_section() {
  echo ""
  echo -e "${CYAN}▶ $1${NC}"
  echo -e "${CYAN}────────────────────────────────────────────────────────────────${NC}"
}

check_pass() {
  echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
  echo -e "${RED}✗${NC} $1"
  echo -e "${YELLOW}  Action: $2${NC}"
}

check_warn() {
  echo -e "${YELLOW}⚠${NC} $1"
  if [ -n "$2" ]; then
    echo -e "${YELLOW}  Action: $2${NC}"
  fi
}

# ═══════════════════════════════════════════════════════════════
# MAIN SCRIPT
# ═══════════════════════════════════════════════════════════════

print_header "ZephyrWealth Back-Office Data Debug"

# Check .env exists
print_section "Step 1: Environment Variables"

if [ ! -f ".env" ]; then
  check_fail "Missing .env file" "cp .env.example .env && edit .env with your values"
  exit 1
fi

check_pass ".env file exists"

# Load environment variables
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs) 2>/dev/null || true
fi

# Check required variables
MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
DB_NAME="${DB_NAME:-zephyrwealth}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
REACT_APP_BACKEND_URL="${REACT_APP_BACKEND_URL:-http://localhost:5000}"

check_pass "MONGO_URL: $MONGO_URL"
check_pass "DB_NAME: $DB_NAME"
check_pass "FRONTEND_URL: $FRONTEND_URL"
check_pass "Backend URL: $REACT_APP_BACKEND_URL"

# ═══════════════════════════════════════════════════════════════
# Step 2: Check Backend
# ═══════════════════════════════════════════════════════════════

print_section "Step 2: Backend Status"

HEALTH=$(curl -s -X GET "$REACT_APP_BACKEND_URL/health" 2>/dev/null || echo "")

if [ -z "$HEALTH" ]; then
  check_fail "Backend not responding at $REACT_APP_BACKEND_URL" \
    "cd backend && python3 -m uvicorn server:app --reload --port 5000"
  exit 1
fi

if echo "$HEALTH" | grep -q '"status":"ok"'; then
  check_pass "Backend running at $REACT_APP_BACKEND_URL"
  check_pass "Service: $(echo "$HEALTH" | grep -o '"service":"[^"]*' | cut -d'"' -f4)"
else
  check_fail "Backend responded but not healthy" "Check backend logs"
  exit 1
fi

# ═══════════════════════════════════════════════════════════════
# Step 3: Check MongoDB
# ═══════════════════════════════════════════════════════════════

print_section "Step 3: MongoDB Status"

# Extract host and port from MONGO_URL
MONGO_HOST=$(echo "$MONGO_URL" | sed -E 's/mongodb:\/\/(.*):([0-9]+).*/\1/' || echo "localhost")
MONGO_PORT=$(echo "$MONGO_URL" | sed -E 's/mongodb:\/\/(.*):([0-9]+).*/\2/' || echo "27017")

# Check if mongo command exists
if ! command -v mongosh &> /dev/null && ! command -v mongo &> /dev/null; then
  check_warn "MongoDB CLI not available (mongosh/mongo not found)" \
    "Install MongoDB Client Tools or check manually in MongoDB Compass"
  MONGO_CLI=""
else
  if command -v mongosh &> /dev/null; then
    MONGO_CLI="mongosh"
  else
    MONGO_CLI="mongo"
  fi
fi

# Try to get counts
if [ -n "$MONGO_CLI" ]; then
  USERS_COUNT=$($MONGO_CLI "$MONGO_URL/$DB_NAME" --quiet --eval "db.users.count()" 2>/dev/null || echo "0")
  INVESTORS_COUNT=$($MONGO_CLI "$MONGO_URL/$DB_NAME" --quiet --eval "db.investors.count()" 2>/dev/null || echo "0")
  DEALS_COUNT=$($MONGO_CLI "$MONGO_URL/$DB_NAME" --quiet --eval "db.deals.count()" 2>/dev/null || echo "0")
else
  check_warn "Skipping MongoDB data check (CLI not available)"
  USERS_COUNT=0
  INVESTORS_COUNT=0
  DEALS_COUNT=0
fi

if [ "$USERS_COUNT" -lt 3 ]; then
  check_fail "Back-office users not seeded (found $USERS_COUNT, expected 3)" \
    "Restart backend to trigger auto-seed or see reseed instructions"
else
  check_pass "Back-office users: $USERS_COUNT ✓"
fi

if [ "$INVESTORS_COUNT" -lt 6 ]; then
  check_fail "Investors not seeded (found $INVESTORS_COUNT, expected 6+)" \
    "Restart backend or manually reseed"
else
  check_pass "Investors: $INVESTORS_COUNT ✓"
fi

if [ "$DEALS_COUNT" -lt 5 ]; then
  check_fail "Deals not seeded (found $DEALS_COUNT, expected 5+)" \
    "Restart backend or manually reseed"
else
  check_pass "Deals: $DEALS_COUNT ✓"
fi

# ═══════════════════════════════════════════════════════════════
# Step 4: Test Login
# ═══════════════════════════════════════════════════════════════

print_section "Step 4: Back-Office Authentication"

LOGIN_RESPONSE=$(curl -s -X POST "$REACT_APP_BACKEND_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"compliance@zephyrwealth.ai","password":"Comply1234!"}' \
  -c /tmp/bo_cookies.txt 2>&1)

if echo "$LOGIN_RESPONSE" | grep -q '"access_token"'; then
  check_pass "Login successful"
  
  # Extract user info
  USER_NAME=$(echo "$LOGIN_RESPONSE" | grep -o '"name":"[^"]*' | head -1 | cut -d'"' -f4)
  USER_ROLE=$(echo "$LOGIN_RESPONSE" | grep -o '"role":"[^"]*' | head -1 | cut -d'"' -f4)
  
  check_pass "Logged in as: $USER_NAME ($USER_ROLE)"
else
  check_fail "Login failed" \
    "Check credentials or if users exist in database"
  echo "Response: $(echo "$LOGIN_RESPONSE" | head -c 200)..."
fi

# ═══════════════════════════════════════════════════════════════
# Step 5: Test API Endpoints
# ═══════════════════════════════════════════════════════════════

print_section "Step 5: Back-Office API Endpoints"

if [ -f /tmp/bo_cookies.txt ]; then
  
  # Test dashboard stats
  echo ""
  echo "Testing GET /api/dashboard/stats..."
  STATS=$(curl -s -b /tmp/bo_cookies.txt "$REACT_APP_BACKEND_URL/api/dashboard/stats" 2>&1)
  
  if echo "$STATS" | grep -q '"total_investors"'; then
    check_pass "Dashboard stats OK"
    
    TOTAL_INV=$(echo "$STATS" | grep -o '"total_investors":[0-9]*' | cut -d':' -f2)
    PENDING_KYC=$(echo "$STATS" | grep -o '"pending_kyc":[0-9]*' | cut -d':' -f2)
    DEALS_PIPELINE=$(echo "$STATS" | grep -o '"deals_in_pipeline":[0-9]*' | cut -d':' -f2)
    COMMITTED=$(echo "$STATS" | grep -o '"total_committed_capital":[0-9.]*' | cut -d':' -f2)
    
    check_pass "  • Total investors: $TOTAL_INV"
    check_pass "  • Pending KYC: $PENDING_KYC"
    check_pass "  • Deals in pipeline: $DEALS_PIPELINE"
    check_pass "  • Total committed capital: \$$COMMITTED"
  else
    check_fail "Dashboard stats returned no data" \
      "Check backend logs"
  fi
  
  # Test investors
  echo ""
  echo "Testing GET /api/investors..."
  INVESTORS=$(curl -s -b /tmp/bo_cookies.txt "$REACT_APP_BACKEND_URL/api/investors" 2>&1)
  
  if echo "$INVESTORS" | grep -q '\['; then
    INV_COUNT=$(echo "$INVESTORS" | grep -o '"id"' | wc -l)
    if [ "$INV_COUNT" -gt 0 ]; then
      check_pass "Investors endpoint OK ($INV_COUNT records)"
    else
      check_fail "Investors endpoint returned empty array" \
        "Database has investors but API returns empty"
    fi
  else
    check_fail "Investors endpoint error" \
      "Check backend logs and CORS config"
  fi
  
  # Test deals
  echo ""
  echo "Testing GET /api/deals..."
  DEALS=$(curl -s -b /tmp/bo_cookies.txt "$REACT_APP_BACKEND_URL/api/deals" 2>&1)
  
  if echo "$DEALS" | grep -q '\['; then
    DEALS_COUNT=$(echo "$DEALS" | grep -o '"id"' | wc -l)
    if [ "$DEALS_COUNT" -gt 0 ]; then
      check_pass "Deals endpoint OK ($DEALS_COUNT records)"
    else
      check_fail "Deals endpoint returned empty array" \
        "Database has deals but API returns empty"
    fi
  else
    check_fail "Deals endpoint error" \
      "Check backend logs"
  fi
  
else
  check_fail "Could not test API (login failed)" \
    "Fix authentication first"
fi

# ═══════════════════════════════════════════════════════════════
# Step 6: Recommendations
# ═══════════════════════════════════════════════════════════════

print_section "Step 6: Summary & Recommendations"

echo ""
if [ "$USERS_COUNT" -lt 3 ] || [ "$INVESTORS_COUNT" -lt 6 ] || [ "$DEALS_COUNT" -lt 5 ]; then
  echo -e "${RED}⚠ DATA NOT FULLY SEEDED${NC}"
  echo ""
  echo "To force reseed:"
  echo "  1. Stop backend (Ctrl+C)"
  echo "  2. Clear database:"
  echo "     $ $MONGO_CLI"
  echo "     > use $DB_NAME"
  echo "     > db.dropDatabase()"
  echo "     > exit"
  echo "  3. Start backend:"
  echo "     $ cd backend"
  echo "     $ python3 -m uvicorn server:app --reload --port 5000"
  echo "  4. Wait for: 'ZephyrWealth API v6 ready'"
  echo ""
else
  echo -e "${GREEN}✓ All data seeded successfully${NC}"
fi

if [ -f /tmp/bo_cookies.txt ]; then
  echo -e "${GREEN}✓ BACK-OFFICE DASHBOARD SHOULD NOW WORK!${NC}"
  echo ""
  echo "To verify:"
  echo "  1. Open http://localhost:3000"
  echo "  2. Login:"
  echo "     Email: compliance@zephyrwealth.ai"
  echo "     Password: Comply1234!"
  echo "  3. Dashboard should show stats and charts"
  echo ""
  echo "If still no data:"
  echo "  • Check browser DevTools → Network tab (look for 401, 404, 500)"
  echo "  • Check browser DevTools → Console tab (CORS, auth errors)"
  echo "  • Check backend logs (terminal running uvicorn)"
fi

print_section "✅ Debug Complete"
echo ""
