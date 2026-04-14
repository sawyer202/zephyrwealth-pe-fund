from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import db, DOCUMENTS_DIR
from seed import seed_users, seed_demo_data, seed_demo_phase4, seed_demo_phase5, seed_portal_users

from routes.auth import router as auth_router
from routes.dashboard import router as dashboard_router
from routes.investors import router as investors_router
from routes.deals import router as deals_router
from routes.reports import router as reports_router
from routes.portfolio import router as portfolio_router
from routes.capital_calls import router as capital_calls_router
from routes.agents import router as agents_router
from routes.trailer_fees import router as trailer_fees_router
from routes.admin import router as admin_router
from routes.portal_auth import router as portal_auth_router
from routes.portal import router as portal_router
from routes.distributions import router as distributions_router

app = FastAPI(title="ZephyrWealth API", version="3.0.0")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# EMERGENT_ORIGIN: set to the Emergent preview URL when FRONTEND_URL is a custom domain.
# This ensures the Emergent preview and .emergent.host domains stay in the CORS allowlist
# even after FRONTEND_URL is updated to a custom domain (e.g. zephyrtrustai.com).
EMERGENT_ORIGIN = os.environ.get("EMERGENT_ORIGIN", "")

_allowed_origins = [FRONTEND_URL]

# Auto-derive Emergent preview ↔ production counterpart for whichever URL is primary.
for _origin in [FRONTEND_URL, EMERGENT_ORIGIN]:
    if not _origin:
        continue
    if _origin not in _allowed_origins:
        _allowed_origins.append(_origin)
    if ".preview.emergentagent.com" in _origin:
        _companion = _origin.replace(".preview.emergentagent.com", ".emergent.host")
        if _companion not in _allowed_origins:
            _allowed_origins.append(_companion)
    elif ".emergent.host" in _origin:
        _companion = _origin.replace(".emergent.host", ".preview.emergentagent.com")
        if _companion not in _allowed_origins:
            _allowed_origins.append(_companion)

# Custom production domains — always present regardless of FRONTEND_URL value.
for _custom in ["https://zephyrtrustai.com", "https://www.zephyrtrustai.com"]:
    if _custom not in _allowed_origins:
        _allowed_origins.append(_custom)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(investors_router)
app.include_router(deals_router)
app.include_router(reports_router)
app.include_router(portfolio_router)
app.include_router(capital_calls_router)
app.include_router(agents_router)
app.include_router(trailer_fees_router)
app.include_router(admin_router)
app.include_router(portal_auth_router)
app.include_router(portal_router)
app.include_router(distributions_router)


@app.on_event("startup")
async def startup():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index("last_attempt", expireAfterSeconds=3600)
    await db.documents.create_index("entity_id")
    await db.compliance_scorecards.create_index("entity_id")
    await db.deals.create_index("pipeline_stage")
    await seed_users()
    await seed_demo_data()
    await seed_demo_phase4()
    await seed_demo_phase5()
    await seed_portal_users()
    await db.investor_users.create_index("email", unique=True)
    await db.investor_users.create_index("investor_id")
    print("ZephyrWealth API v6 ready — Investor Portal enabled")


@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ZephyrWealth API", "version": "3.0.0"}
