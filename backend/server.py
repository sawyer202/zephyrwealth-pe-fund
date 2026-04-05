from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel
import os
import jwt
import bcrypt
import secrets
import shutil
import uuid
import json
from pathlib import Path
from bson import ObjectId
from emergentintegrations.llm.chat import LlmChat, UserMessage

app = FastAPI(title="ZephyrWealth API", version="2.0.0")

# ─── Constants ───────────────────────────────────────────────────────────────
DOCUMENTS_DIR = Path("/documents")

# ─── CORS ───────────────────────────────────────────────────────────────────
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database ────────────────────────────────────────────────────────────────
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# ─── Config ──────────────────────────────────────────────────────────────────
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

SCORECARD_SYSTEM_PROMPT = """You are a KYC/AML Compliance Analyst for a licensed Bahamian Private Equity fund operating under FTRA 2018. Review this investor profile and produce a structured Compliance Scorecard. Return ONLY a valid JSON object with no extra text, markdown, or explanation:

{
  "sanctions_status": "Clear | Pending | Flagged",
  "identity_status": "Verified | Partial | Unverified",
  "document_status": "Complete | Partial | Missing",
  "source_of_funds": "Clear | Requires Clarification | Unexplained",
  "pep_status": "No | Possible | Confirmed",
  "mandate_status": "In Mandate | Exception | Blocked",
  "identity_confidence_score": 0-100,
  "score_breakdown": {
    "documents": 0-30,
    "source_of_wealth": 0-25,
    "sanctions": 0-25,
    "nationality_risk": 0-20
  },
  "risk_rating": "Low | Medium | High",
  "edd_required": true or false,
  "overall_rating": "Low Risk | Medium Risk | High Risk",
  "recommendation": "Approve | Review | Reject",
  "summary": "2-3 sentence plain English summary of key findings"
}"""

# ─── Password Helpers ────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def validate_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

# ─── JWT Helpers ─────────────────────────────────────────────────────────────
def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ─── Pydantic Models ─────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class AddressModel(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str

class UBODeclaration(BaseModel):
    name: str
    nationality: str
    ownership_percentage: float

class InvestorCreateRequest(BaseModel):
    entity_type: str
    legal_name: str
    dob: Optional[str] = None
    nationality: str
    residence_country: str
    email: str
    phone: str
    address: AddressModel
    net_worth: float
    annual_income: float
    source_of_wealth: str
    investment_experience: str
    classification: str
    ubo_declarations: Optional[List[UBODeclaration]] = []
    accredited_declaration: Optional[bool] = False
    terms_accepted: bool

class DecisionRequest(BaseModel):
    decision: str
    notes: Optional[str] = None

# ─── Helpers ─────────────────────────────────────────────────────────────────
def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-safe dict."""
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    for key, val in list(doc.items()):
        if isinstance(val, datetime):
            doc[key] = val.isoformat()
        elif isinstance(val, ObjectId):
            doc[key] = str(val)
    return doc

# ─── Seeding ─────────────────────────────────────────────────────────────────
SEED_USERS = [
    {
        "email": "compliance@zephyrwealth.ai",
        "password": "Comply1234!",
        "role": "compliance",
        "name": "Sarah Chen",
        "title": "Chief Compliance Officer",
    },
    {
        "email": "risk@zephyrwealth.ai",
        "password": "Risk1234!",
        "role": "risk",
        "name": "Marcus Webb",
        "title": "Head of Risk",
    },
    {
        "email": "manager@zephyrwealth.ai",
        "password": "Manager1234!",
        "role": "manager",
        "name": "Jonathan Morrow",
        "title": "Fund Manager",
    },
]

async def seed_users():
    for u in SEED_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        if existing is None:
            await db.users.insert_one({
                "email": u["email"],
                "password_hash": hash_password(u["password"]),
                "role": u["role"],
                "name": u["name"],
                "title": u["title"],
                "created_at": datetime.now(timezone.utc),
            })
        elif not verify_password(u["password"], existing["password_hash"]):
            await db.users.update_one(
                {"email": u["email"]},
                {"$set": {"password_hash": hash_password(u["password"])}},
            )

async def seed_demo_data():
    # ── Phase 1: Basic investors ──────────────────────────────────────────────
    if await db.investors.count_documents({}) == 0:
        await db.investors.insert_many([
            {
                "name": "Harrington & Associates LLC",
                "type": "Corporate Entity",
                "submitted_date": datetime(2025, 1, 15, tzinfo=timezone.utc),
                "risk_rating": "medium",
                "kyc_status": "pending",
                "scorecard_completed": False,
                "country": "Cayman Islands",
                "investment_amount": 5000000,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "name": "Castlebrook Family Office",
                "type": "Family Office",
                "submitted_date": datetime(2025, 2, 3, tzinfo=timezone.utc),
                "risk_rating": "low",
                "kyc_status": "approved",
                "scorecard_completed": True,
                "country": "Bahamas",
                "investment_amount": 12000000,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "name": "Meridian Capital Fund III",
                "type": "Investment Fund",
                "submitted_date": datetime(2025, 2, 18, tzinfo=timezone.utc),
                "risk_rating": "high",
                "kyc_status": "flagged",
                "scorecard_completed": False,
                "country": "British Virgin Islands",
                "investment_amount": 8500000,
                "created_at": datetime.now(timezone.utc),
            },
        ])

    # ── Phase 1: Deals ────────────────────────────────────────────────────────
    if await db.deals.count_documents({}) == 0:
        await db.deals.insert_many([
            {
                "name": "Nassau Waterfront Development",
                "type": "Real Estate",
                "submitted_date": datetime(2025, 1, 20, tzinfo=timezone.utc),
                "risk_rating": "medium",
                "stage": "due_diligence",
                "scorecard_completed": False,
                "target_return": "18%",
                "deal_size": 25000000,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "name": "Caribbean Logistics Group",
                "type": "Private Equity",
                "submitted_date": datetime(2025, 2, 10, tzinfo=timezone.utc),
                "risk_rating": "low",
                "stage": "term_sheet",
                "scorecard_completed": True,
                "target_return": "22%",
                "deal_size": 15000000,
                "created_at": datetime.now(timezone.utc),
            },
        ])

    # ── Phase 2: Full-schema investors ────────────────────────────────────────
    if await db.investors.count_documents({"legal_name": {"$exists": True}}) == 0:
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

        # Investor 1: Approved individual, Low risk
        inv1_id = ObjectId()
        inv1_str = str(inv1_id)
        await db.investors.insert_one({
            "_id": inv1_id,
            "legal_name": "Victoria Pemberton",
            "name": "Victoria Pemberton",
            "entity_type": "individual",
            "type": "Individual",
            "dob": "1982-07-14",
            "nationality": "United Kingdom",
            "residence_country": "Bahamas",
            "email": "v.pemberton@privatemail.com",
            "phone": "+1 242-555-0191",
            "address": {"street": "14 Ocean Club Estates", "city": "Nassau", "postal_code": "N-4861", "country": "Bahamas"},
            "net_worth": 8500000,
            "annual_income": 950000,
            "source_of_wealth": "Investment",
            "investment_experience": "5+ years",
            "classification": "individual_accredited",
            "ubo_declarations": [],
            "accredited_declaration": True,
            "risk_rating": "low",
            "kyc_status": "approved",
            "scorecard_completed": True,
            "investment_amount": 3000000,
            "submitted_date": datetime(2025, 1, 10, tzinfo=timezone.utc),
            "submitted_at": datetime(2025, 1, 10, tzinfo=timezone.utc),
            "country": "Bahamas",
            "created_at": datetime.now(timezone.utc),
        })
        for doc_type, fname in [
            ("passport", "passport_victoria_pemberton.pdf"),
            ("proof_of_address", "utility_bill_jan2025.pdf"),
            ("source_of_wealth_doc", "investment_portfolio_statement.pdf"),
        ]:
            p = DOCUMENTS_DIR / inv1_str / doc_type
            p.mkdir(parents=True, exist_ok=True)
            fp = p / fname
            fp.write_bytes(b"[Seeded placeholder document - ZephyrWealth]")
            await db.documents.insert_one({
                "entity_id": inv1_str, "document_type": doc_type,
                "file_path": str(fp), "file_name": fname,
                "file_size": 43, "uploaded_at": datetime(2025, 1, 10, tzinfo=timezone.utc),
            })
        await db.compliance_scorecards.insert_one({
            "entity_id": inv1_str, "entity_type": "investor",
            "scorecard_data": {
                "sanctions_status": "Clear", "identity_status": "Verified",
                "document_status": "Complete", "source_of_funds": "Clear",
                "pep_status": "No", "mandate_status": "In Mandate",
                "identity_confidence_score": 91,
                "score_breakdown": {"documents": 28, "source_of_wealth": 23, "sanctions": 24, "nationality_risk": 16},
                "risk_rating": "Low", "edd_required": False,
                "overall_rating": "Low Risk", "recommendation": "Approve",
                "summary": "Victoria Pemberton presents a low-risk profile with verified UK identity and clean sanctions screening. Source of wealth through investment activities is well-documented and consistent with declared net worth. All required KYC documents are complete and no adverse findings noted.",
            },
            "recommendation": "Approve",
            "generated_at": datetime(2025, 1, 12, tzinfo=timezone.utc),
            "reviewed_by": None, "decision": "approve",
            "decision_at": datetime(2025, 1, 15, tzinfo=timezone.utc),
        })

        # Investor 2: Pending corporate, Medium risk
        inv2_id = ObjectId()
        inv2_str = str(inv2_id)
        await db.investors.insert_one({
            "_id": inv2_id,
            "legal_name": "Apex Meridian Holdings Ltd",
            "name": "Apex Meridian Holdings Ltd",
            "entity_type": "corporate",
            "type": "Corporate Entity",
            "dob": None,
            "nationality": "British Virgin Islands",
            "residence_country": "British Virgin Islands",
            "email": "compliance@apexmeridian.com",
            "phone": "+1 284-555-0147",
            "address": {"street": "Wickhams Cay II, Road Town", "city": "Road Town", "postal_code": "VG1110", "country": "British Virgin Islands"},
            "net_worth": 45000000,
            "annual_income": 6200000,
            "source_of_wealth": "Business",
            "investment_experience": "5+ years",
            "classification": "institutional",
            "ubo_declarations": [
                {"name": "Richard Apex", "nationality": "United Kingdom", "ownership_percentage": 55.0},
                {"name": "Sarah Meridian", "nationality": "Canada", "ownership_percentage": 45.0},
            ],
            "accredited_declaration": False,
            "risk_rating": "medium",
            "kyc_status": "pending",
            "scorecard_completed": False,
            "investment_amount": 15000000,
            "submitted_date": datetime(2025, 2, 1, tzinfo=timezone.utc),
            "submitted_at": datetime(2025, 2, 1, tzinfo=timezone.utc),
            "country": "British Virgin Islands",
            "created_at": datetime.now(timezone.utc),
        })
        for doc_type, fname in [
            ("passport", "certificate_of_incorporation.pdf"),
            ("proof_of_address", "registered_office_proof.pdf"),
            ("source_of_wealth_doc", "audited_financials_2024.pdf"),
            ("corporate_documents", "memorandum_and_articles.pdf"),
        ]:
            p = DOCUMENTS_DIR / inv2_str / doc_type
            p.mkdir(parents=True, exist_ok=True)
            fp = p / fname
            fp.write_bytes(b"[Seeded placeholder document - ZephyrWealth]")
            await db.documents.insert_one({
                "entity_id": inv2_str, "document_type": doc_type,
                "file_path": str(fp), "file_name": fname,
                "file_size": 43, "uploaded_at": datetime(2025, 2, 1, tzinfo=timezone.utc),
            })

        # Investor 3: Flagged individual, High risk
        inv3_id = ObjectId()
        inv3_str = str(inv3_id)
        await db.investors.insert_one({
            "_id": inv3_id,
            "legal_name": "Dmitri Volkov",
            "name": "Dmitri Volkov",
            "entity_type": "individual",
            "type": "Individual",
            "dob": "1975-03-22",
            "nationality": "Russia",
            "residence_country": "Cyprus",
            "email": "d.volkov@privatemail.ru",
            "phone": "+357 99-555-0188",
            "address": {"street": "12 Limassol Marina", "city": "Limassol", "postal_code": "3601", "country": "Cyprus"},
            "net_worth": 22000000,
            "annual_income": 1800000,
            "source_of_wealth": "Business",
            "investment_experience": "5+ years",
            "classification": "individual_accredited",
            "ubo_declarations": [],
            "accredited_declaration": True,
            "risk_rating": "high",
            "kyc_status": "flagged",
            "scorecard_completed": True,
            "investment_amount": 8000000,
            "submitted_date": datetime(2025, 2, 10, tzinfo=timezone.utc),
            "submitted_at": datetime(2025, 2, 10, tzinfo=timezone.utc),
            "country": "Cyprus",
            "created_at": datetime.now(timezone.utc),
        })
        for doc_type, fname in [
            ("passport", "passport_dmitri_volkov.pdf"),
            ("proof_of_address", "bank_statement_cyprus.pdf"),
        ]:
            p = DOCUMENTS_DIR / inv3_str / doc_type
            p.mkdir(parents=True, exist_ok=True)
            fp = p / fname
            fp.write_bytes(b"[Seeded placeholder document - ZephyrWealth]")
            await db.documents.insert_one({
                "entity_id": inv3_str, "document_type": doc_type,
                "file_path": str(fp), "file_name": fname,
                "file_size": 43, "uploaded_at": datetime(2025, 2, 10, tzinfo=timezone.utc),
            })
        await db.compliance_scorecards.insert_one({
            "entity_id": inv3_str, "entity_type": "investor",
            "scorecard_data": {
                "sanctions_status": "Flagged", "identity_status": "Partial",
                "document_status": "Partial", "source_of_funds": "Unexplained",
                "pep_status": "Possible", "mandate_status": "Blocked",
                "identity_confidence_score": 34,
                "score_breakdown": {"documents": 12, "source_of_wealth": 6, "sanctions": 8, "nationality_risk": 8},
                "risk_rating": "High", "edd_required": True,
                "overall_rating": "High Risk", "recommendation": "Reject",
                "summary": "Dmitri Volkov presents a high-risk profile with Russian nationality and Cyprus residency, a combination that triggers enhanced due diligence requirements under FTRA 2018. Sanctions screening has returned a potential match requiring further investigation, and the declared source of business wealth cannot be adequately substantiated with the provided documentation. Recommendation is Reject pending full sanctions clearance and comprehensive source of wealth evidence.",
            },
            "recommendation": "Reject",
            "generated_at": datetime(2025, 2, 12, tzinfo=timezone.utc),
            "reviewed_by": None, "decision": None, "decision_at": None,
        })

# ─── Startup ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index("last_attempt", expireAfterSeconds=3600)
    await db.documents.create_index("entity_id")
    await db.compliance_scorecards.create_index("entity_id")
    await seed_users()
    await seed_demo_data()
    print("✅ ZephyrWealth API v2 ready")

# ─── Health ──────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ZephyrWealth API", "version": "2.0.0"}

# ─── Auth: Login ─────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
async def login(request: Request, response: Response, body: LoginRequest):
    email = body.email.lower().strip()
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{email}"

    attempt_doc = await db.login_attempts.find_one({"identifier": identifier})
    if attempt_doc:
        locked_until = attempt_doc.get("locked_until")
        if locked_until and datetime.now(timezone.utc) < locked_until:
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
            raise HTTPException(status_code=429, detail=f"Account locked. Try again in {remaining} minute(s).")

    user = await db.users.find_one({"email": email})

    if not user or not verify_password(body.password, user["password_hash"]):
        now = datetime.now(timezone.utc)
        if attempt_doc:
            new_count = attempt_doc.get("failed_count", 0) + 1
            update_data = {"failed_count": new_count, "last_attempt": now}
            if new_count >= 5:
                update_data["locked_until"] = now + timedelta(minutes=15)
            await db.login_attempts.update_one({"identifier": identifier}, {"$set": update_data})
        else:
            await db.login_attempts.insert_one({"identifier": identifier, "failed_count": 1, "last_attempt": now})
        raise HTTPException(status_code=401, detail="Invalid email or password")

    await db.login_attempts.delete_one({"identifier": identifier})

    user_id = str(user["_id"])
    access_token = create_access_token(user_id, user["email"], user["role"])
    refresh_token = create_refresh_token(user_id)

    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=28800, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")

    await db.audit_logs.insert_one({
        "user_id": user_id, "action": "login", "target_id": None,
        "target_type": "auth", "timestamp": datetime.now(timezone.utc),
        "notes": f"Login from {client_ip}",
    })

    return {"id": user_id, "email": user["email"], "role": user["role"], "name": user.get("name", ""), "title": user.get("title", "")}

# ─── Auth: Logout ─────────────────────────────────────────────────────────────
@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

# ─── Auth: Me ────────────────────────────────────────────────────────────────
@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ─── Auth: Refresh ───────────────────────────────────────────────────────────
@app.post("/api/auth/refresh")
async def refresh_token_endpoint(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user_id = str(user["_id"])
        new_token = create_access_token(user_id, user["email"], user["role"])
        response.set_cookie(key="access_token", value=new_token, httponly=True, secure=False, samesite="lax", max_age=28800, path="/")
        return {"message": "Token refreshed"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# ─── Dashboard: Stats ────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    total_investors = await db.investors.count_documents({})
    pending_kyc = await db.investors.count_documents({"kyc_status": "pending"})
    deals_in_pipeline = await db.deals.count_documents({})
    flagged_investors = await db.investors.count_documents({"risk_rating": "high"})
    flagged_deals = await db.deals.count_documents({"risk_rating": "high"})
    return {
        "total_investors": total_investors,
        "pending_kyc": pending_kyc,
        "deals_in_pipeline": deals_in_pipeline,
        "flagged_items": flagged_investors + flagged_deals,
    }

# ─── Investors: List ─────────────────────────────────────────────────────────
@app.get("/api/investors")
async def get_investors(current_user: dict = Depends(get_current_user)):
    investors = []
    async for doc in db.investors.find().sort("submitted_date", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        for k in ("submitted_date", "submitted_at", "created_at", "reviewed_at"):
            if isinstance(doc.get(k), datetime):
                doc[k] = doc[k].isoformat()
        investors.append(doc)
    return investors

# ─── Investors: Create ───────────────────────────────────────────────────────
@app.post("/api/investors")
async def create_investor(body: InvestorCreateRequest, current_user: dict = Depends(get_current_user)):
    doc = {
        "legal_name": body.legal_name,
        "name": body.legal_name,
        "entity_type": body.entity_type,
        "type": "Individual" if body.entity_type == "individual" else "Corporate Entity",
        "dob": body.dob,
        "nationality": body.nationality,
        "residence_country": body.residence_country,
        "email": body.email,
        "phone": body.phone,
        "address": body.address.dict(),
        "net_worth": body.net_worth,
        "annual_income": body.annual_income,
        "source_of_wealth": body.source_of_wealth,
        "investment_experience": body.investment_experience,
        "classification": body.classification,
        "ubo_declarations": [u.dict() for u in (body.ubo_declarations or [])],
        "accredited_declaration": body.accredited_declaration,
        "risk_rating": "medium",
        "kyc_status": "pending",
        "scorecard_completed": False,
        "investment_amount": 0,
        "submitted_date": datetime.now(timezone.utc),
        "submitted_at": datetime.now(timezone.utc),
        "country": body.residence_country,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.investors.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["submitted_date"] = doc["submitted_date"].isoformat()
    doc["submitted_at"] = doc["submitted_at"].isoformat()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.audit_logs.insert_one({
        "user_id": current_user["_id"],
        "action": "investor_created",
        "target_id": doc["id"],
        "target_type": "investor",
        "timestamp": datetime.now(timezone.utc),
        "notes": f"New investor onboarded: {body.legal_name}",
    })
    return doc

# ─── Investors: Get One ───────────────────────────────────────────────────────
@app.get("/api/investors/{investor_id}")
async def get_investor(investor_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")
    doc = await db.investors.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Investor not found")
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    for k in ("submitted_date", "submitted_at", "created_at", "reviewed_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return doc

# ─── Documents: Upload ───────────────────────────────────────────────────────
@app.post("/api/investors/{investor_id}/documents")
async def upload_document(
    investor_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    current_user: dict = Depends(get_current_user),
):
    allowed_mime = {"application/pdf", "image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in allowed_mime:
        raise HTTPException(400, "Only PDF, JPEG, PNG files are allowed")

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "File size must be under 5MB")

    safe_name = file.filename.replace(" ", "_")
    doc_path = DOCUMENTS_DIR / investor_id / document_type
    doc_path.mkdir(parents=True, exist_ok=True)
    file_path = doc_path / safe_name
    file_path.write_bytes(content)

    record = {
        "entity_id": investor_id,
        "document_type": document_type,
        "file_path": str(file_path),
        "file_name": safe_name,
        "file_size": len(content),
        "uploaded_at": datetime.now(timezone.utc),
    }
    result = await db.documents.insert_one(record)
    record["id"] = str(result.inserted_id)
    record.pop("_id", None)
    record["uploaded_at"] = record["uploaded_at"].isoformat()
    return record

# ─── Documents: List ─────────────────────────────────────────────────────────
@app.get("/api/investors/{investor_id}/documents")
async def list_documents(investor_id: str, current_user: dict = Depends(get_current_user)):
    docs = []
    async for doc in db.documents.find({"entity_id": investor_id}).sort("uploaded_at", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("uploaded_at"), datetime):
            doc["uploaded_at"] = doc["uploaded_at"].isoformat()
        docs.append(doc)
    return docs

# ─── Documents: Download ─────────────────────────────────────────────────────
@app.get("/api/investors/{investor_id}/documents/{document_id}/download")
async def download_document(
    investor_id: str,
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(document_id)
    except Exception:
        raise HTTPException(400, "Invalid document ID")
    doc = await db.documents.find_one({"_id": oid, "entity_id": investor_id})
    if not doc:
        raise HTTPException(404, "Document not found")
    file_path = Path(doc["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "File not found on server")
    return FileResponse(path=str(file_path), filename=doc["file_name"], media_type="application/octet-stream")

# ─── Scorecard: Generate ──────────────────────────────────────────────────────
@app.post("/api/investors/{investor_id}/scorecard")
async def generate_scorecard(investor_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")
    investor = await db.investors.find_one({"_id": oid})
    if not investor:
        raise HTTPException(404, "Investor not found")

    # Gather documents uploaded
    docs_uploaded = []
    async for doc in db.documents.find({"entity_id": investor_id}):
        docs_uploaded.append(doc["document_type"])

    investor_profile = {
        "legal_name": investor.get("legal_name") or investor.get("name", ""),
        "entity_type": investor.get("entity_type", "individual"),
        "nationality": investor.get("nationality", ""),
        "residence_country": investor.get("residence_country") or investor.get("country", ""),
        "source_of_wealth": investor.get("source_of_wealth", ""),
        "net_worth_usd": investor.get("net_worth", 0),
        "annual_income_usd": investor.get("annual_income", 0),
        "classification": investor.get("classification", ""),
        "investment_experience": investor.get("investment_experience", ""),
        "ubo_declarations": investor.get("ubo_declarations", []),
        "documents_uploaded": docs_uploaded,
    }

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=str(uuid.uuid4()),
        system_message=SCORECARD_SYSTEM_PROMPT,
    ).with_model("anthropic", "claude-4-sonnet-20250514")

    user_msg = UserMessage(text=f"Review this investor profile and generate the compliance scorecard:\n\n{json.dumps(investor_profile, default=str, indent=2)}")
    response = await chat.send_message(user_msg)

    # Parse Claude response — strip markdown fences if present
    raw = response.strip()
    if "```" in raw:
        parts = raw.split("```")
        for part in parts:
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{"):
                raw = candidate
                break
    try:
        scorecard_data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Failed to parse AI scorecard response: {str(e)}")

    scorecard_doc = {
        "entity_id": investor_id,
        "entity_type": "investor",
        "scorecard_data": scorecard_data,
        "recommendation": scorecard_data.get("recommendation", "Review"),
        "generated_at": datetime.now(timezone.utc),
        "reviewed_by": current_user.get("_id"),
        "decision": None,
        "decision_at": None,
    }
    result = await db.compliance_scorecards.insert_one(scorecard_doc)

    # Mark investor scorecard as completed
    await db.investors.update_one({"_id": oid}, {"$set": {"scorecard_completed": True}})

    scorecard_doc["id"] = str(result.inserted_id)
    scorecard_doc.pop("_id", None)
    scorecard_doc["generated_at"] = scorecard_doc["generated_at"].isoformat()
    return scorecard_doc

# ─── Scorecard: Get Latest ────────────────────────────────────────────────────
@app.get("/api/investors/{investor_id}/scorecard")
async def get_scorecard(investor_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.compliance_scorecards.find_one(
        {"entity_id": investor_id},
        sort=[("generated_at", -1)],
    )
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    if isinstance(doc.get("generated_at"), datetime):
        doc["generated_at"] = doc["generated_at"].isoformat()
    if isinstance(doc.get("decision_at"), datetime):
        doc["decision_at"] = doc["decision_at"].isoformat()
    return doc

# ─── Investors: Decision ──────────────────────────────────────────────────────
@app.post("/api/investors/{investor_id}/decision")
async def investor_decision(
    investor_id: str,
    body: DecisionRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")
    investor = await db.investors.find_one({"_id": oid})
    if not investor:
        raise HTTPException(404, "Investor not found")

    status_map = {"approve": "approved", "reject": "rejected", "more_info": "pending"}
    new_status = status_map.get(body.decision, "pending")

    await db.investors.update_one(
        {"_id": oid},
        {"$set": {"kyc_status": new_status, "reviewed_at": datetime.now(timezone.utc), "reviewed_by": current_user.get("_id")}},
    )
    await db.compliance_scorecards.update_many(
        {"entity_id": investor_id},
        {"$set": {"decision": body.decision, "decision_at": datetime.now(timezone.utc), "reviewed_by": current_user.get("_id")}},
    )
    action_labels = {"approve": "investor_approved", "reject": "investor_rejected", "more_info": "investor_more_info_requested"}
    await db.audit_logs.insert_one({
        "user_id": current_user.get("_id"),
        "action": action_labels.get(body.decision, "investor_decision"),
        "target_id": investor_id,
        "target_type": "investor",
        "timestamp": datetime.now(timezone.utc),
        "notes": body.notes or f"Decision: {body.decision} for {investor.get('legal_name') or investor.get('name', '')}",
    })
    return {"message": f"Investor decision recorded: {body.decision}", "status": new_status}

# ─── Deals ───────────────────────────────────────────────────────────────────
@app.get("/api/deals")
async def get_deals(current_user: dict = Depends(get_current_user)):
    deals = []
    async for doc in db.deals.find().sort("submitted_date", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("submitted_date"), datetime):
            doc["submitted_date"] = doc["submitted_date"].isoformat()
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        deals.append(doc)
    return deals

# ─── Audit Logs ───────────────────────────────────────────────────────────────
@app.get("/api/audit-logs")
async def get_audit_logs(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "manager"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    logs = []
    async for doc in db.audit_logs.find().sort("timestamp", -1).limit(100):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("timestamp"), datetime):
            doc["timestamp"] = doc["timestamp"].isoformat()
        logs.append(doc)
    return logs
