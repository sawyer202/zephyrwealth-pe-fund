from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response, Depends, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
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
import zipfile
from pathlib import Path
from bson import ObjectId
from emergentintegrations.llm.chat import LlmChat, UserMessage
from io import BytesIO
from functools import partial as _partial
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm

app = FastAPI(title="ZephyrWealth API", version="3.0.0")

DOCUMENTS_DIR = Path("/documents")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

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

OLD_DEAL_STAGE_MAP = {"term_sheet": "ic_review", "due_diligence": "due_diligence", "prospecting": "leads", "closed": "closing"}
STAGE_LABELS = {"leads": "Leads", "due_diligence": "Due Diligence", "ic_review": "IC Review", "closing": "Closing"}

# ─── Password Helpers ────────────────────────────────────────────────────────
def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

# ─── JWT Helpers ─────────────────────────────────────────────────────────────
def create_access_token(user_id: str, email: str, role: str) -> str:
    return jwt.encode({
        "sub": user_id, "email": email, "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "type": "access",
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    return jwt.encode({
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh",
    }, JWT_SECRET, algorithm=JWT_ALGORITHM)

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

class DealCreateRequest(BaseModel):
    company_name: str
    sector: str
    geography: str
    asset_class: str
    expected_irr: float
    entry_valuation: float
    entity_type: str  # IBC | ICON

class DealStageUpdate(BaseModel):
    stage: str
    override_note: Optional[str] = None

# ─── Phase 5 Pydantic Models ──────────────────────────────────────────────────
class PlacementAgentCreate(BaseModel):
    agent_name: str
    company_name: str
    email: str
    phone: str
    bank_name: str
    bank_account_number: str
    swift_code: str
    vat_registered: bool
    vat_number: Optional[str] = None

class PlacementAgentUpdate(BaseModel):
    agent_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    swift_code: Optional[str] = None
    vat_registered: Optional[bool] = None
    vat_number: Optional[str] = None

class FundParticipationUpdate(BaseModel):
    share_class: str
    committed_capital: float
    placement_agent_id: Optional[str] = None
    deal_associations: Optional[List[str]] = []

class CapitalCallCreate(BaseModel):
    call_name: str
    call_type: str
    target_classes: List[str]
    call_percentage: float
    due_date: str
    deal_id: Optional[str] = None

class LineItemStatusUpdate(BaseModel):
    status: str

class TrailerFeeGenerateRequest(BaseModel):
    year: int
    agent_ids: Optional[List[str]] = None

# ─── Deal Helpers ─────────────────────────────────────────────────────────────
async def check_deal_mandate(sector: str, geography: str, irr: float) -> str:
    mandate = await db.fund_mandate.find_one({})
    if not mandate:
        return "In Mandate"
    in_sector = sector in mandate.get("allowed_sectors", [])
    in_geo = geography in mandate.get("allowed_geographies", [])
    in_irr = mandate.get("irr_min", 0) <= irr <= mandate.get("irr_max", 100)
    return "In Mandate" if (in_sector and in_geo and in_irr) else "Exception"

def normalize_deal(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    doc["company_name"] = doc.get("company_name") or doc.get("name", "")
    doc["pipeline_stage"] = doc.get("pipeline_stage") or OLD_DEAL_STAGE_MAP.get(doc.get("stage", ""), "leads")
    doc["entity_type"] = doc.get("entity_type", "IBC")
    doc["mandate_status"] = doc.get("mandate_status", "In Mandate")
    raw_irr = doc.get("expected_irr")
    if raw_irr is None and doc.get("target_return"):
        try:
            raw_irr = float(str(doc["target_return"]).replace("%", ""))
        except (ValueError, TypeError):
            raw_irr = 0
    doc["expected_irr"] = raw_irr or 0
    doc["entry_valuation"] = doc.get("entry_valuation") or doc.get("deal_size", 0)
    doc["sector"] = doc.get("sector") or doc.get("type", "")
    for k in ("submitted_date", "created_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return doc

def generate_subscription_agreement(company_name, entry_val, irr, stamp_duty, date, deal_id):
    return f"""================================================================================
SUBSCRIPTION AGREEMENT -- DRAFT STUB
================================================================================
ZEPHYRWEALTH CAPITAL FUND I
Registered under the International Business Companies Act (Ch. 309), Bahamas

Date: {date.strftime('%d %B %Y')}
Reference: ZWF1-IBC-{deal_id[:8].upper()}

PARTIES
-------
1. ZephyrWealth Capital Fund I ("the Fund")
   Registered Office: Nassau, New Providence, Commonwealth of The Bahamas

2. {company_name} ("the Subscriber")
   Entity Type: International Business Company (IBC)

INVESTMENT TERMS
----------------
Company:           {company_name}
Entry Valuation:   USD {entry_val:,.0f}
Expected IRR:      {irr}%
Stamp Duty Est.:   USD {stamp_duty:,.0f} (0.5% of entry valuation)

STAMP DUTY NOTICE
-----------------
The stamp duty estimate above (0.5% of entry valuation = USD {stamp_duty:,.0f}) is
provided for INDICATIVE PURPOSES ONLY. The actual stamp duty payable will depend
on the nature of the instruments, applicable exemptions, and the Stamp Act (Ch. 370).
YOU MUST CONFIRM THE EXACT AMOUNT WITH BAHAMIAN COUNSEL before execution.

REPRESENTATIONS AND WARRANTIES
--------------------------------
The Subscriber represents and warrants that:
1. It is duly incorporated and in good standing under applicable law.
2. It qualifies as a Sophisticated Investor per the Investment Funds Act, 2020.
3. Subscription funds have a clear and lawful source of wealth.
4. Full KYC/AML documentation has been accepted per FTRA 2018.
5. It has reviewed the Fund's Offering Memorandum and constitutive documents.

CLOSING CONDITIONS
------------------
1. Satisfactory completion of all KYC/AML due diligence.
2. Receipt of all required Securities Commission approvals.
3. Execution of all ancillary documentation required by legal counsel.
4. Payment of subscription amount and applicable stamp duty.

[DRAFT STUB -- REQUIRES REVIEW AND APPROVAL BY LEGAL COUNSEL BEFORE EXECUTION]

Fund Authorised Signatory: _______________________  Date: __________

Subscriber Authorised Signatory: _______________________  Date: __________
================================================================================
ZephyrWealth.ai Back-Office Platform | Investment Funds Act 2020 | FTRA 2018
================================================================================
"""

def generate_participation_agreement(company_name, entry_val, irr, stamp_duty, date, deal_id):
    return f"""================================================================================
PARTICIPATION AGREEMENT -- DRAFT STUB
================================================================================
ZEPHYRWEALTH CAPITAL FUND I
Investment Condominium Structure

================================================================================
!! ADMINISTRATOR ACTION REQUIRED !!
Pursuant to the Investment Condominium Act 2014 and the Fund's constitutive
documents, the Fund Administrator MUST update the Register of Participants
upon execution of this Participation Agreement.

REQUIRED ACTIONS:
  - Update the official Register of Participants with participant details
  - File notification with the Securities Commission of The Bahamas
  - Issue updated participation certificate to participant
================================================================================

Date: {date.strftime('%d %B %Y')}
Reference: ZWF1-ICON-{deal_id[:8].upper()}

PARTIES
-------
1. ZephyrWealth Capital Fund I -- Investment Condominium ("the Fund")
   Structured as Investment Condominium per Investment Condominium Act 2014

2. {company_name} ("the Participant")

PARTICIPATION TERMS
--------------------
Company:             {company_name}
Entry Valuation:     USD {entry_val:,.0f}
Expected IRR:        {irr}%
Stamp Duty Est.:     USD {stamp_duty:,.0f} (0.5% of entry valuation)

STAMP DUTY NOTICE
-----------------
Stamp duty (0.5% = USD {stamp_duty:,.0f}) is INDICATIVE ONLY.
CONFIRM WITH BAHAMIAN COUNSEL before execution.

INVESTMENT CONDOMINIUM PROVISIONS (Investment Condominium Act 2014)
-------------------------------------------------------------------
1. Participant acquires undivided co-ownership interest in the Fund assets.
2. Participation interests governed by the Fund Offering Memorandum.
3. Administrator must maintain Register of Participants at all times.
4. Transfer of interests requires prior written Administrator notification.
5. Valuation of interests per Fund constitutive documents.

REPRESENTATIONS AND WARRANTIES
--------------------------------
The Participant represents and warrants that:
1. Qualifies as a Sophisticated Investor per the Investment Funds Act, 2020.
2. Funds represent lawful assets with clear source of wealth documentation.
3. Full KYC/AML documentation provided and accepted per FTRA 2018.
4. Acknowledges the illiquid nature of participation interests.

CLOSING CONDITIONS
------------------
1. Completion of KYC/AML due diligence per FTRA 2018.
2. Administrator update of Register of Participants.
3. Notification filed with Securities Commission of The Bahamas.
4. Payment of participation amount and applicable stamp duty.

[DRAFT STUB -- REQUIRES REVIEW BY LEGAL COUNSEL BEFORE EXECUTION]
[ADMINISTRATOR: UPDATE REGISTER OF PARTICIPANTS UPON EXECUTION]

Fund Administrator: _______________________  Date: __________

Participant Authorised Signatory: _______________________  Date: __________
================================================================================
ZephyrWealth.ai | Investment Condominium Act 2014 | Investment Funds Act 2020
================================================================================
"""

# ─── PDF Helpers ─────────────────────────────────────────────────────────────
def _hf_callback(canvas, doc, *, title_line2, user_name, user_role, ts):
    """Draw branded header and footer on every page."""
    page_w, page_h = A4
    canvas.saveState()
    canvas.setFillColor(rl_colors.HexColor('#1B3A6B'))
    canvas.rect(0, page_h - 28*mm, page_w, 28*mm, fill=True, stroke=False)
    canvas.setFillColor(rl_colors.white)
    canvas.setFont('Helvetica-Bold', 13)
    canvas.drawString(15*mm, page_h - 11*mm, 'ZephyrWealth.ai')
    canvas.setFillColor(rl_colors.HexColor('#00A8C6'))
    canvas.setFont('Helvetica', 8)
    canvas.drawString(15*mm, page_h - 19*mm, 'Private Equity Back-Office Platform')
    canvas.setFillColor(rl_colors.HexColor('#C9A84C'))
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawRightString(page_w - 15*mm, page_h - 11*mm, title_line2)
    canvas.setFillColor(rl_colors.HexColor('#9CA3AF'))
    canvas.setFont('Helvetica', 7)
    canvas.drawRightString(page_w - 15*mm, page_h - 19*mm, f'Generated: {ts}')
    canvas.setFillColor(rl_colors.HexColor('#F8F9FA'))
    canvas.rect(0, 0, page_w, 15*mm, fill=True, stroke=False)
    canvas.setStrokeColor(rl_colors.HexColor('#E5E7EB'))
    canvas.line(0, 15*mm, page_w, 15*mm)
    canvas.setFillColor(rl_colors.HexColor('#6B7280'))
    canvas.setFont('Helvetica', 7)
    canvas.drawString(15*mm, 6*mm, f'Prepared by ZephyrWealth.ai  |  Confidential — For Regulatory Submission Only  |  {user_name} ({user_role})')
    canvas.drawRightString(page_w - 15*mm, 6*mm, f'Page {doc.page}')
    canvas.restoreState()

def _pdf_styles():
    ss = getSampleStyleSheet()
    return {
        'h1': ParagraphStyle('zwh1', parent=ss['Normal'], fontSize=18, textColor=rl_colors.HexColor('#1B3A6B'), fontName='Helvetica-Bold', spaceAfter=4),
        'h2': ParagraphStyle('zwh2', parent=ss['Normal'], fontSize=12, textColor=rl_colors.HexColor('#1B3A6B'), fontName='Helvetica-Bold', spaceAfter=3, spaceBefore=8),
        'h3': ParagraphStyle('zwh3', parent=ss['Normal'], fontSize=10, textColor=rl_colors.HexColor('#374151'), fontName='Helvetica-Bold', spaceAfter=2, spaceBefore=4),
        'body': ParagraphStyle('zwbody', parent=ss['Normal'], fontSize=9, textColor=rl_colors.HexColor('#374151'), fontName='Helvetica', spaceAfter=2),
        'small': ParagraphStyle('zwsmall', parent=ss['Normal'], fontSize=7.5, textColor=rl_colors.HexColor('#6B7280'), fontName='Helvetica', spaceAfter=1),
        'center': ParagraphStyle('zwcenter', parent=ss['Normal'], fontSize=9, alignment=1, textColor=rl_colors.HexColor('#374151'), fontName='Helvetica'),
        'cover_title': ParagraphStyle('zwcvt', parent=ss['Normal'], fontSize=26, textColor=rl_colors.HexColor('#1B3A6B'), alignment=1, fontName='Helvetica-Bold', spaceAfter=6),
        'cover_sub': ParagraphStyle('zwcvs', parent=ss['Normal'], fontSize=13, textColor=rl_colors.HexColor('#00A8C6'), alignment=1, fontName='Helvetica', spaceAfter=4),
        'cover_body': ParagraphStyle('zwcvb', parent=ss['Normal'], fontSize=10, textColor=rl_colors.HexColor('#6B7280'), alignment=1, fontName='Helvetica', spaceAfter=3),
    }

def _tbl_style():
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1B3A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.HexColor('#374151')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#F8F9FA')]),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])

_PDF_HC = {
    'Low': '#10B981', 'High': '#EF4444', 'Medium': '#F59E0B',
    'Aligned': '#10B981', 'Misaligned': '#EF4444',
    'Complete': '#10B981', 'Partial': '#F59E0B', 'Missing': '#EF4444',
    'In Mandate': '#10B981', 'Exception': '#EF4444', 'Exception Cleared': '#F59E0B',
    'Recommend Approve': '#10B981', 'Review': '#F59E0B', 'Block': '#EF4444',
    'Approve': '#10B981', 'Reject': '#EF4444', 'Review_rec': '#F59E0B',
}


SEED_USERS = [
    {"email": "compliance@zephyrwealth.ai", "password": "Comply1234!", "role": "compliance", "name": "Sarah Chen", "title": "Chief Compliance Officer"},
    {"email": "risk@zephyrwealth.ai", "password": "Risk1234!", "role": "risk", "name": "Marcus Webb", "title": "Head of Risk"},
    {"email": "manager@zephyrwealth.ai", "password": "Manager1234!", "role": "manager", "name": "Jonathan Morrow", "title": "Fund Manager"},
]

async def seed_users():
    for u in SEED_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        if existing is None:
            await db.users.insert_one({"email": u["email"], "password_hash": hash_password(u["password"]), "role": u["role"], "name": u["name"], "title": u["title"], "created_at": datetime.now(timezone.utc)})
        elif not verify_password(u["password"], existing["password_hash"]):
            await db.users.update_one({"email": u["email"]}, {"$set": {"password_hash": hash_password(u["password"])}})

async def seed_demo_data():
    # Phase 1: Basic investors
    if await db.investors.count_documents({}) == 0:
        await db.investors.insert_many([
            {"name": "Harrington & Associates LLC", "type": "Corporate Entity", "submitted_date": datetime(2025, 1, 15, tzinfo=timezone.utc), "risk_rating": "medium", "kyc_status": "pending", "scorecard_completed": False, "country": "Cayman Islands", "investment_amount": 5000000, "created_at": datetime.now(timezone.utc)},
            {"name": "Castlebrook Family Office", "type": "Family Office", "submitted_date": datetime(2025, 2, 3, tzinfo=timezone.utc), "risk_rating": "low", "kyc_status": "approved", "scorecard_completed": True, "country": "Bahamas", "investment_amount": 12000000, "created_at": datetime.now(timezone.utc)},
            {"name": "Meridian Capital Fund III", "type": "Investment Fund", "submitted_date": datetime(2025, 2, 18, tzinfo=timezone.utc), "risk_rating": "high", "kyc_status": "flagged", "scorecard_completed": False, "country": "British Virgin Islands", "investment_amount": 8500000, "created_at": datetime.now(timezone.utc)},
        ])

    # Phase 1: Basic deals
    if await db.deals.count_documents({}) == 0:
        await db.deals.insert_many([
            {"name": "Nassau Waterfront Development", "type": "Real Estate", "submitted_date": datetime(2025, 1, 20, tzinfo=timezone.utc), "risk_rating": "medium", "stage": "due_diligence", "scorecard_completed": False, "target_return": "18%", "deal_size": 25000000, "created_at": datetime.now(timezone.utc)},
            {"name": "Caribbean Logistics Group", "type": "Private Equity", "submitted_date": datetime(2025, 2, 10, tzinfo=timezone.utc), "risk_rating": "low", "stage": "term_sheet", "scorecard_completed": True, "target_return": "22%", "deal_size": 15000000, "created_at": datetime.now(timezone.utc)},
        ])

    # Phase 2: Full-schema investors
    if await db.investors.count_documents({"legal_name": {"$exists": True}}) == 0:
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        inv1_id = ObjectId(); inv1_str = str(inv1_id)
        await db.investors.insert_one({"_id": inv1_id, "legal_name": "Victoria Pemberton", "name": "Victoria Pemberton", "entity_type": "individual", "type": "Individual", "dob": "1982-07-14", "nationality": "United Kingdom", "residence_country": "Bahamas", "email": "v.pemberton@privatemail.com", "phone": "+1 242-555-0191", "address": {"street": "14 Ocean Club Estates", "city": "Nassau", "postal_code": "N-4861", "country": "Bahamas"}, "net_worth": 8500000, "annual_income": 950000, "source_of_wealth": "Investment", "investment_experience": "5+ years", "classification": "individual_accredited", "ubo_declarations": [], "accredited_declaration": True, "risk_rating": "low", "kyc_status": "approved", "scorecard_completed": True, "investment_amount": 3000000, "submitted_date": datetime(2025, 1, 10, tzinfo=timezone.utc), "submitted_at": datetime(2025, 1, 10, tzinfo=timezone.utc), "country": "Bahamas", "created_at": datetime.now(timezone.utc)})
        for dt, fn in [("passport", "passport_victoria_pemberton.pdf"), ("proof_of_address", "utility_bill_jan2025.pdf"), ("source_of_wealth_doc", "investment_portfolio_statement.pdf")]:
            p = DOCUMENTS_DIR / inv1_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": inv1_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 1, 10, tzinfo=timezone.utc)})
        await db.compliance_scorecards.insert_one({"entity_id": inv1_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Clear", "identity_status": "Verified", "document_status": "Complete", "source_of_funds": "Clear", "pep_status": "No", "mandate_status": "In Mandate", "identity_confidence_score": 91, "score_breakdown": {"documents": 28, "source_of_wealth": 23, "sanctions": 24, "nationality_risk": 16}, "risk_rating": "Low", "edd_required": False, "overall_rating": "Low Risk", "recommendation": "Approve", "summary": "Victoria Pemberton presents a low-risk profile with verified UK identity and clean sanctions screening. Source of wealth through investment activities is well-documented and consistent with declared net worth. All required KYC documents are complete and no adverse findings noted."}, "recommendation": "Approve", "generated_at": datetime(2025, 1, 12, tzinfo=timezone.utc), "reviewed_by": None, "decision": "approve", "decision_at": datetime(2025, 1, 15, tzinfo=timezone.utc)})
        inv2_id = ObjectId(); inv2_str = str(inv2_id)
        await db.investors.insert_one({"_id": inv2_id, "legal_name": "Apex Meridian Holdings Ltd", "name": "Apex Meridian Holdings Ltd", "entity_type": "corporate", "type": "Corporate Entity", "dob": None, "nationality": "British Virgin Islands", "residence_country": "British Virgin Islands", "email": "compliance@apexmeridian.com", "phone": "+1 284-555-0147", "address": {"street": "Wickhams Cay II, Road Town", "city": "Road Town", "postal_code": "VG1110", "country": "British Virgin Islands"}, "net_worth": 45000000, "annual_income": 6200000, "source_of_wealth": "Business", "investment_experience": "5+ years", "classification": "institutional", "ubo_declarations": [{"name": "Richard Apex", "nationality": "United Kingdom", "ownership_percentage": 55.0}, {"name": "Sarah Meridian", "nationality": "Canada", "ownership_percentage": 45.0}], "accredited_declaration": False, "risk_rating": "medium", "kyc_status": "pending", "scorecard_completed": False, "investment_amount": 15000000, "submitted_date": datetime(2025, 2, 1, tzinfo=timezone.utc), "submitted_at": datetime(2025, 2, 1, tzinfo=timezone.utc), "country": "British Virgin Islands", "created_at": datetime.now(timezone.utc)})
        for dt, fn in [("passport", "certificate_of_incorporation.pdf"), ("proof_of_address", "registered_office_proof.pdf"), ("source_of_wealth_doc", "audited_financials_2024.pdf"), ("corporate_documents", "memorandum_and_articles.pdf")]:
            p = DOCUMENTS_DIR / inv2_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": inv2_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 2, 1, tzinfo=timezone.utc)})
        inv3_id = ObjectId(); inv3_str = str(inv3_id)
        await db.investors.insert_one({"_id": inv3_id, "legal_name": "Dmitri Volkov", "name": "Dmitri Volkov", "entity_type": "individual", "type": "Individual", "dob": "1975-03-22", "nationality": "Russia", "residence_country": "Cyprus", "email": "d.volkov@privatemail.ru", "phone": "+357 99-555-0188", "address": {"street": "12 Limassol Marina", "city": "Limassol", "postal_code": "3601", "country": "Cyprus"}, "net_worth": 22000000, "annual_income": 1800000, "source_of_wealth": "Business", "investment_experience": "5+ years", "classification": "individual_accredited", "ubo_declarations": [], "accredited_declaration": True, "risk_rating": "high", "kyc_status": "flagged", "scorecard_completed": True, "investment_amount": 8000000, "submitted_date": datetime(2025, 2, 10, tzinfo=timezone.utc), "submitted_at": datetime(2025, 2, 10, tzinfo=timezone.utc), "country": "Cyprus", "created_at": datetime.now(timezone.utc)})
        for dt, fn in [("passport", "passport_dmitri_volkov.pdf"), ("proof_of_address", "bank_statement_cyprus.pdf")]:
            p = DOCUMENTS_DIR / inv3_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": inv3_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 2, 10, tzinfo=timezone.utc)})
        await db.compliance_scorecards.insert_one({"entity_id": inv3_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Flagged", "identity_status": "Partial", "document_status": "Partial", "source_of_funds": "Unexplained", "pep_status": "Possible", "mandate_status": "Blocked", "identity_confidence_score": 34, "score_breakdown": {"documents": 12, "source_of_wealth": 6, "sanctions": 8, "nationality_risk": 8}, "risk_rating": "High", "edd_required": True, "overall_rating": "High Risk", "recommendation": "Reject", "summary": "Dmitri Volkov presents a high-risk profile with Russian nationality and Cyprus residency, triggering enhanced due diligence under FTRA 2018. Sanctions screening returned a potential match requiring further investigation, and source of business wealth cannot be substantiated. Recommendation is Reject pending full sanctions clearance."}, "recommendation": "Reject", "generated_at": datetime(2025, 2, 12, tzinfo=timezone.utc), "reviewed_by": None, "decision": None, "decision_at": None})

    # Phase 3: Fund mandate
    if await db.fund_mandate.count_documents({}) == 0:
        await db.fund_mandate.insert_one({
            "fund_name": "ZephyrWealth Capital Fund I",
            "allowed_sectors": ["Technology", "Financial Services"],
            "allowed_geographies": ["Caribbean", "Africa"],
            "irr_min": 15.0,
            "irr_max": 25.0,
            "max_single_investment": 25000000,
            "updated_at": datetime.now(timezone.utc),
        })

    # Phase 3: Full-schema deals
    if await db.deals.count_documents({"company_name": {"$exists": True}}) == 0:
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        d1_id = ObjectId(); d1_str = str(d1_id)
        await db.deals.insert_one({"_id": d1_id, "company_name": "NexaTech Caribbean Ltd", "name": "NexaTech Caribbean Ltd", "sector": "Technology", "geography": "Caribbean", "asset_class": "Private Equity", "expected_irr": 18.0, "entry_valuation": 8000000, "entity_type": "IBC", "mandate_status": "In Mandate", "pipeline_stage": "ic_review", "stage": "ic_review", "stamp_duty_estimate": 40000, "status": "active", "type": "Technology", "risk_rating": "low", "scorecard_completed": False, "deal_size": 8000000, "target_return": "18%", "submitted_date": datetime(2025, 1, 20, tzinfo=timezone.utc), "created_at": datetime.now(timezone.utc), "created_by": None})
        for dt, fn in [("financials", "nexatech_financials_2024.pdf"), ("cap_table", "nexatech_cap_table.pdf")]:
            p = DOCUMENTS_DIR / d1_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": d1_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 1, 22, tzinfo=timezone.utc)})
        d2_id = ObjectId(); d2_str = str(d2_id)
        await db.deals.insert_one({"_id": d2_id, "company_name": "West African Fintrust ICON", "name": "West African Fintrust ICON", "sector": "Fintech", "geography": "Africa", "asset_class": "Venture", "expected_irr": 12.0, "entry_valuation": 5000000, "entity_type": "ICON", "mandate_status": "Exception", "pipeline_stage": "due_diligence", "stage": "due_diligence", "stamp_duty_estimate": 25000, "status": "active", "type": "Fintech", "risk_rating": "medium", "scorecard_completed": False, "deal_size": 5000000, "target_return": "12%", "submitted_date": datetime(2025, 2, 5, tzinfo=timezone.utc), "created_at": datetime.now(timezone.utc), "created_by": None})
        for dt, fn in [("financials", "waf_financials.pdf")]:
            p = DOCUMENTS_DIR / d2_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": d2_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 2, 6, tzinfo=timezone.utc)})
        d3_id = ObjectId()
        await db.deals.insert_one({"_id": d3_id, "company_name": "Nassau Microfinance Co.", "name": "Nassau Microfinance Co.", "sector": "Financial Services", "geography": "Caribbean", "asset_class": "Private Equity", "expected_irr": 22.0, "entry_valuation": 3500000, "entity_type": "IBC", "mandate_status": "In Mandate", "pipeline_stage": "leads", "stage": "leads", "stamp_duty_estimate": 17500, "status": "active", "type": "Financial Services", "risk_rating": "low", "scorecard_completed": False, "deal_size": 3500000, "target_return": "22%", "submitted_date": datetime(2025, 2, 15, tzinfo=timezone.utc), "created_at": datetime.now(timezone.utc), "created_by": None})


async def seed_demo_phase4():
    """Feature 12 — idempotent demo seed. Guard: fund_profile fund_name."""
    if await db.fund_profile.find_one({"fund_name": "Zephyr Caribbean Growth Fund I"}):
        return

    now = datetime.now(timezone.utc)
    def dag(n): return now - timedelta(days=n)

    # ── Fund Profile ──────────────────────────────────────────────────────────
    await db.fund_profile.insert_one({
        "fund_name": "Zephyr Caribbean Growth Fund I",
        "license_number": "SCB-2024-PE-0042",
        "fund_manager": "Zephyr Asset Management Ltd",
        "mandate_sectors": ["Technology", "Financial Services"],
        "mandate_geographies": ["Caribbean", "Africa"],
        "irr_min": 15.0,
        "irr_max": 25.0,
        "created_at": now,
    })

    # ── Lookup user IDs ───────────────────────────────────────────────────────
    c_user = await db.users.find_one({"email": "compliance@zephyrwealth.ai"})
    r_user = await db.users.find_one({"email": "risk@zephyrwealth.ai"})
    m_user = await db.users.find_one({"email": "manager@zephyrwealth.ai"})
    c_id = str(c_user["_id"]) if c_user else "system"
    r_id = str(r_user["_id"]) if r_user else "system"
    m_id = str(m_user["_id"]) if m_user else "system"

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    def mk_doc(entity_id, doc_type, filename):
        p = DOCUMENTS_DIR / entity_id / doc_type
        p.mkdir(parents=True, exist_ok=True)
        fp = p / filename
        fp.write_bytes(b"[Demo seed placeholder - ZephyrWealth Phase 4]")
        return {"entity_id": entity_id, "document_type": doc_type, "file_path": str(fp), "file_name": filename, "file_size": 46, "uploaded_at": dag(45)}

    # ── Investors ─────────────────────────────────────────────────────────────
    inv1_id = ObjectId(); inv1_str = str(inv1_id)
    await db.investors.insert_one({
        "_id": inv1_id, "legal_name": "Cayman Tech Ventures SPV Ltd", "name": "Cayman Tech Ventures SPV Ltd",
        "entity_type": "corporate", "type": "Corporate Entity", "dob": None,
        "nationality": "Cayman Islands", "residence_country": "Cayman Islands",
        "email": "admin@caymantech.ky", "phone": "+1 345-555-0192",
        "address": {"street": "Windward 1, Regatta Office Park", "city": "Grand Cayman", "postal_code": "KY1-9006", "country": "Cayman Islands"},
        "net_worth": 50000000, "annual_income": 8000000, "source_of_wealth": "Investment",
        "investment_experience": "5+ years", "classification": "institutional",
        "ubo_declarations": [{"name": "James Caldwell", "nationality": "United Kingdom", "ownership_percentage": 60.0}, {"name": "Patricia Lau", "nationality": "Canada", "ownership_percentage": 40.0}],
        "accredited_declaration": True, "risk_rating": "low", "kyc_status": "approved",
        "scorecard_completed": True, "investment_amount": 5000000,
        "submitted_date": dag(50), "submitted_at": dag(50), "country": "Cayman Islands", "created_at": dag(50),
        "reviewed_at": dag(46), "reviewed_by": c_id,
    })
    for dt, fn in [("passport", "cert_of_incorporation_cayman_tech.pdf"), ("proof_of_address", "registered_office_cayman.pdf"), ("source_of_wealth_doc", "audited_financials_cayman_tech.pdf")]:
        await db.documents.insert_one(mk_doc(inv1_str, dt, fn))
    await db.compliance_scorecards.insert_one({
        "entity_id": inv1_str, "entity_type": "investor",
        "scorecard_data": {"sanctions_status": "Clear", "identity_status": "Verified", "document_status": "Complete", "source_of_funds": "Clear", "pep_status": "No", "mandate_status": "In Mandate", "identity_confidence_score": 88, "score_breakdown": {"documents": 27, "source_of_wealth": 22, "sanctions": 23, "nationality_risk": 16}, "risk_rating": "Low", "edd_required": False, "overall_rating": "Low Risk", "recommendation": "Approve", "summary": "Cayman Tech Ventures SPV Ltd is a well-structured Cayman SPV with verified institutional UBOs from low-risk jurisdictions. All KYC documentation is complete and source of wealth through technology investment activities is fully substantiated. Sanctions screening returned no adverse findings."},
        "recommendation": "Approve", "generated_at": dag(47), "reviewed_by": c_id, "decision": "approve", "decision_at": dag(46),
    })

    inv2_id = ObjectId(); inv2_str = str(inv2_id)
    await db.investors.insert_one({
        "_id": inv2_id, "legal_name": "Nassau Capital Partners IBC", "name": "Nassau Capital Partners IBC",
        "entity_type": "corporate", "type": "Corporate Entity", "dob": None,
        "nationality": "Bahamas", "residence_country": "Bahamas",
        "email": "compliance@nassaucapital.bs", "phone": "+1 242-555-0184",
        "address": {"street": "Bay Street Financial Centre, Suite 401", "city": "Nassau", "postal_code": "N-1234", "country": "Bahamas"},
        "net_worth": 25000000, "annual_income": 3500000, "source_of_wealth": "Business",
        "investment_experience": "5+ years", "classification": "institutional",
        "ubo_declarations": [{"name": "Reginald Thompson", "nationality": "Bahamas", "ownership_percentage": 100.0}],
        "accredited_declaration": True, "risk_rating": "low", "kyc_status": "approved",
        "scorecard_completed": True, "investment_amount": 3000000,
        "submitted_date": dag(44), "submitted_at": dag(44), "country": "Bahamas", "created_at": dag(44),
        "reviewed_at": dag(40), "reviewed_by": c_id,
    })
    for dt, fn in [("corporate_documents", "nassau_capital_ibc_cert.pdf"), ("proof_of_address", "nassau_registered_office.pdf"), ("source_of_wealth_doc", "nassau_capital_financials_2024.pdf")]:
        await db.documents.insert_one(mk_doc(inv2_str, dt, fn))
    await db.compliance_scorecards.insert_one({
        "entity_id": inv2_str, "entity_type": "investor",
        "scorecard_data": {"sanctions_status": "Clear", "identity_status": "Verified", "document_status": "Complete", "source_of_funds": "Clear", "pep_status": "No", "mandate_status": "In Mandate", "identity_confidence_score": 84, "score_breakdown": {"documents": 26, "source_of_wealth": 22, "sanctions": 24, "nationality_risk": 12}, "risk_rating": "Low", "edd_required": False, "overall_rating": "Low Risk", "recommendation": "Approve", "summary": "Nassau Capital Partners IBC is a locally-registered Bahamian entity with a single verified beneficial owner and complete KYC documentation. Business income is well-documented and consistent with declared net worth. No adverse sanctions findings."},
        "recommendation": "Approve", "generated_at": dag(42), "reviewed_by": c_id, "decision": "approve", "decision_at": dag(40),
    })

    inv3_id = ObjectId(); inv3_str = str(inv3_id)
    await db.investors.insert_one({
        "_id": inv3_id, "legal_name": "Marcus Harrington", "name": "Marcus Harrington",
        "entity_type": "individual", "type": "Individual", "dob": "1978-04-22",
        "nationality": "Barbados", "residence_country": "Barbados",
        "email": "m.harrington@privatemail.bb", "phone": "+1 246-555-0177",
        "address": {"street": "12 Rockley Golf Estate", "city": "Christ Church", "postal_code": "BB15008", "country": "Barbados"},
        "net_worth": 12000000, "annual_income": 1800000, "source_of_wealth": "Business",
        "investment_experience": "5+ years", "classification": "individual_accredited",
        "ubo_declarations": [], "accredited_declaration": True, "risk_rating": "low", "kyc_status": "approved",
        "scorecard_completed": True, "investment_amount": 1500000,
        "submitted_date": dag(38), "submitted_at": dag(38), "country": "Barbados", "created_at": dag(38),
        "reviewed_at": dag(35), "reviewed_by": c_id,
    })
    for dt, fn in [("passport", "harrington_passport.pdf"), ("proof_of_address", "harrington_utility_barbados.pdf")]:
        await db.documents.insert_one(mk_doc(inv3_str, dt, fn))
    await db.compliance_scorecards.insert_one({
        "entity_id": inv3_str, "entity_type": "investor",
        "scorecard_data": {"sanctions_status": "Clear", "identity_status": "Verified", "document_status": "Complete", "source_of_funds": "Clear", "pep_status": "No", "mandate_status": "In Mandate", "identity_confidence_score": 82, "score_breakdown": {"documents": 25, "source_of_wealth": 21, "sanctions": 24, "nationality_risk": 12}, "risk_rating": "Low", "edd_required": False, "overall_rating": "Low Risk", "recommendation": "Approve", "summary": "Marcus Harrington is a Barbadian national with a clean KYC profile and verified business income. Two KYC documents on file are complete for an individual investor. No PEP or sanctions exposure."},
        "recommendation": "Approve", "generated_at": dag(37), "reviewed_by": c_id, "decision": "approve", "decision_at": dag(35),
    })

    inv4_id = ObjectId(); inv4_str = str(inv4_id)
    await db.investors.insert_one({
        "_id": inv4_id, "legal_name": "Yolanda Santos", "name": "Yolanda Santos",
        "entity_type": "individual", "type": "Individual", "dob": "1990-11-03",
        "nationality": "Trinidad and Tobago", "residence_country": "Trinidad and Tobago",
        "email": "y.santos@tntmail.tt", "phone": "+1 868-555-0165",
        "address": {"street": "7 Federation Park", "city": "Port of Spain", "postal_code": "TT100100", "country": "Trinidad and Tobago"},
        "net_worth": 3000000, "annual_income": 420000, "source_of_wealth": "Salary",
        "investment_experience": "1-3 years", "classification": "individual_accredited",
        "ubo_declarations": [], "accredited_declaration": True, "risk_rating": "medium", "kyc_status": "pending",
        "scorecard_completed": False, "investment_amount": 500000,
        "submitted_date": dag(20), "submitted_at": dag(20), "country": "Trinidad and Tobago", "created_at": dag(20),
    })
    for dt, fn in [("passport", "santos_passport.pdf")]:
        await db.documents.insert_one(mk_doc(inv4_str, dt, fn))

    inv5_id = ObjectId(); inv5_str = str(inv5_id)
    await db.investors.insert_one({
        "_id": inv5_id, "legal_name": "Meridian Global Holdings Ltd", "name": "Meridian Global Holdings Ltd",
        "entity_type": "corporate", "type": "Corporate Entity", "dob": None,
        "nationality": "Panama", "residence_country": "Panama",
        "email": "admin@meridianglobal.pa", "phone": "+507-555-0144",
        "address": {"street": "Calle 50, Torres de las Americas", "city": "Panama City", "postal_code": "0810", "country": "Panama"},
        "net_worth": 15000000, "annual_income": 2200000, "source_of_wealth": "Business",
        "investment_experience": "5+ years", "classification": "institutional",
        "ubo_declarations": [{"name": "Viktor Stanev", "nationality": "Bulgaria", "ownership_percentage": 72.0}],
        "accredited_declaration": False, "risk_rating": "high", "kyc_status": "flagged",
        "scorecard_completed": True, "investment_amount": 4000000,
        "submitted_date": dag(30), "submitted_at": dag(30), "country": "Panama", "created_at": dag(30),
    })
    for dt, fn in [("passport", "meridian_cert_of_incorporation.pdf"), ("proof_of_address", "meridian_registered_office.pdf")]:
        await db.documents.insert_one(mk_doc(inv5_str, dt, fn))
    await db.compliance_scorecards.insert_one({
        "entity_id": inv5_str, "entity_type": "investor",
        "scorecard_data": {"sanctions_status": "Pending", "identity_status": "Partial", "document_status": "Partial", "source_of_funds": "Requires Clarification", "pep_status": "Possible", "mandate_status": "Exception", "identity_confidence_score": 42, "score_breakdown": {"documents": 14, "source_of_wealth": 10, "sanctions": 10, "nationality_risk": 8}, "risk_rating": "High", "edd_required": True, "overall_rating": "High Risk", "recommendation": "Review", "summary": "Meridian Global Holdings Ltd presents elevated AML risk. Panama registration with a Bulgarian UBO triggers enhanced due diligence under FTRA 2018. Source of business wealth is insufficiently documented. Potential PEP linkage noted — full sanctions clearance required before proceeding."},
        "recommendation": "Review", "generated_at": dag(28), "reviewed_by": c_id, "decision": None, "decision_at": None,
    })

    inv6_id = ObjectId(); inv6_str = str(inv6_id)
    await db.investors.insert_one({
        "_id": inv6_id, "legal_name": "Olympus Private Capital Ltd", "name": "Olympus Private Capital Ltd",
        "entity_type": "corporate", "type": "Corporate Entity", "dob": None,
        "nationality": "British Virgin Islands", "residence_country": "British Virgin Islands",
        "email": "contact@olympusprivate.vg", "phone": "+1 284-555-0133",
        "address": {"street": "Wickhams Cay I", "city": "Road Town", "postal_code": "VG1110", "country": "British Virgin Islands"},
        "net_worth": 8000000, "annual_income": 1100000, "source_of_wealth": "Business",
        "investment_experience": "3-5 years", "classification": "institutional",
        "ubo_declarations": [{"name": "Unknown Beneficial Owner", "nationality": "Unknown", "ownership_percentage": 100.0}],
        "accredited_declaration": False, "risk_rating": "high", "kyc_status": "rejected",
        "scorecard_completed": True, "investment_amount": 0,
        "submitted_date": dag(25), "submitted_at": dag(25), "country": "British Virgin Islands", "created_at": dag(25),
        "reviewed_at": dag(20), "reviewed_by": c_id,
    })
    for dt, fn in [("passport", "olympus_cert_of_incorporation.pdf")]:
        await db.documents.insert_one(mk_doc(inv6_str, dt, fn))
    await db.compliance_scorecards.insert_one({
        "entity_id": inv6_str, "entity_type": "investor",
        "scorecard_data": {"sanctions_status": "Flagged", "identity_status": "Unverified", "document_status": "Partial", "source_of_funds": "Unexplained", "pep_status": "Confirmed", "mandate_status": "Blocked", "identity_confidence_score": 18, "score_breakdown": {"documents": 6, "source_of_wealth": 3, "sanctions": 4, "nationality_risk": 5}, "risk_rating": "High", "edd_required": True, "overall_rating": "High Risk", "recommendation": "Reject", "summary": "Olympus Private Capital Ltd fails the KYC/AML compliance threshold. UBO identity cannot be verified; BVI registration with undisclosed beneficial ownership. Sanctions flag raised. Source of wealth is entirely unexplained. Decision: Reject."},
        "recommendation": "Reject", "generated_at": dag(22), "reviewed_by": c_id, "decision": "reject", "decision_at": dag(20),
    })

    # ── Deals ─────────────────────────────────────────────────────────────────
    dd1_id = ObjectId(); dd1_str = str(dd1_id)
    await db.deals.insert_one({
        "_id": dd1_id, "company_name": "CaribPay Solutions Ltd", "name": "CaribPay Solutions Ltd",
        "sector": "Technology", "geography": "Caribbean", "asset_class": "Private Equity",
        "expected_irr": 19.0, "entry_valuation": 4200000, "entity_type": "IBC",
        "mandate_status": "In Mandate", "pipeline_stage": "closing", "stage": "closing",
        "stamp_duty_estimate": 21000, "status": "active", "type": "Technology", "risk_rating": "low",
        "scorecard_completed": True, "deal_size": 4200000, "target_return": "19%",
        "submitted_date": dag(55), "created_at": dag(55), "created_by": c_id,
    })
    for dt, fn in [("financials", "caribpay_financials_2024.pdf"), ("cap_table", "caribpay_cap_table.pdf"), ("im", "caribpay_information_memorandum.pdf")]:
        await db.documents.insert_one(mk_doc(dd1_str, dt, fn))

    dd2_id = ObjectId(); dd2_str = str(dd2_id)
    await db.deals.insert_one({
        "_id": dd2_id, "company_name": "AgroHub Africa Ltd", "name": "AgroHub Africa Ltd",
        "sector": "Technology", "geography": "Africa", "asset_class": "Private Equity",
        "expected_irr": 22.0, "entry_valuation": 2800000, "entity_type": "IBC",
        "mandate_status": "In Mandate", "pipeline_stage": "ic_review", "stage": "ic_review",
        "stamp_duty_estimate": 14000, "status": "active", "type": "Technology", "risk_rating": "low",
        "scorecard_completed": True, "deal_size": 2800000, "target_return": "22%",
        "submitted_date": dag(45), "created_at": dag(45), "created_by": c_id,
    })
    for dt, fn in [("financials", "agrohub_financials.pdf"), ("cap_table", "agrohub_cap_table.pdf")]:
        await db.documents.insert_one(mk_doc(dd2_str, dt, fn))

    dd3_id = ObjectId(); dd3_str = str(dd3_id)
    await db.deals.insert_one({
        "_id": dd3_id, "company_name": "InsureSync Caribbean ICON", "name": "InsureSync Caribbean ICON",
        "sector": "Insurance", "geography": "Caribbean", "asset_class": "Venture",
        "expected_irr": 17.0, "entry_valuation": 3100000, "entity_type": "ICON",
        "mandate_status": "Exception", "pipeline_stage": "ic_review", "stage": "ic_review",
        "stamp_duty_estimate": 15500, "status": "active", "type": "Insurance", "risk_rating": "medium",
        "scorecard_completed": False, "deal_size": 3100000, "target_return": "17%",
        "submitted_date": dag(35), "created_at": dag(35), "created_by": c_id,
        "mandate_override_note": "IC approved sector exception — insurance SaaS classified as Financial Services adjacent. Risk Officer override applied.",
    })
    for dt, fn in [("financials", "insuresync_financials.pdf")]:
        await db.documents.insert_one(mk_doc(dd3_str, dt, fn))

    dd4_id = ObjectId(); dd4_str = str(dd4_id)
    await db.deals.insert_one({
        "_id": dd4_id, "company_name": "SaaSAfrica BV", "name": "SaaSAfrica BV",
        "sector": "Technology", "geography": "Africa", "asset_class": "Venture",
        "expected_irr": 24.0, "entry_valuation": 1500000, "entity_type": "IBC",
        "mandate_status": "In Mandate", "pipeline_stage": "due_diligence", "stage": "due_diligence",
        "stamp_duty_estimate": 7500, "status": "active", "type": "Technology", "risk_rating": "low",
        "scorecard_completed": False, "deal_size": 1500000, "target_return": "24%",
        "submitted_date": dag(25), "created_at": dag(25), "created_by": c_id,
    })
    for dt, fn in [("financials", "saasafrica_pitch_deck.pdf")]:
        await db.documents.insert_one(mk_doc(dd4_str, dt, fn))

    dd5_id = ObjectId(); dd5_str = str(dd5_id)
    await db.deals.insert_one({
        "_id": dd5_id, "company_name": "CariLogix Ltd", "name": "CariLogix Ltd",
        "sector": "Financial Services", "geography": "Caribbean", "asset_class": "Private Equity",
        "expected_irr": 12.0, "entry_valuation": 900000, "entity_type": "ICON",
        "mandate_status": "Exception", "pipeline_stage": "leads", "stage": "leads",
        "stamp_duty_estimate": 4500, "status": "active", "type": "Financial Services", "risk_rating": "medium",
        "scorecard_completed": False, "deal_size": 900000, "target_return": "12%",
        "submitted_date": dag(10), "created_at": dag(10), "created_by": c_id,
    })

    # ── Audit Log Entries (15 entries, last 60 days) ──────────────────────────
    await db.audit_logs.insert_many([
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "login", "target_id": None, "target_type": "auth", "timestamp": dag(60), "notes": "Login from 10.0.0.1"},
        {"user_id": r_id, "user_email": "risk@zephyrwealth.ai", "user_role": "risk", "user_name": "Marcus Webb", "action": "login", "target_id": None, "target_type": "auth", "timestamp": dag(58), "notes": "Login from 10.0.0.2"},
        {"user_id": m_id, "user_email": "manager@zephyrwealth.ai", "user_role": "manager", "user_name": "Jonathan Morrow", "action": "login", "target_id": None, "target_type": "auth", "timestamp": dag(56), "notes": "Login from 10.0.0.3"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_created", "target_id": inv1_str, "target_type": "investor", "timestamp": dag(50), "notes": "New investor: Cayman Tech Ventures SPV Ltd"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_approved", "target_id": inv1_str, "target_type": "investor", "timestamp": dag(46), "notes": "Decision: approve for Cayman Tech Ventures SPV Ltd"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_created", "target_id": inv2_str, "target_type": "investor", "timestamp": dag(44), "notes": "New investor: Nassau Capital Partners IBC"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "deal_created", "target_id": dd1_str, "target_type": "deal", "timestamp": dag(42), "notes": "New deal: CaribPay Solutions Ltd | In Mandate"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_approved", "target_id": inv2_str, "target_type": "investor", "timestamp": dag(40), "notes": "Decision: approve for Nassau Capital Partners IBC"},
        {"user_id": r_id, "user_email": "risk@zephyrwealth.ai", "user_role": "risk", "user_name": "Marcus Webb", "action": "deal_stage_moved", "target_id": dd1_str, "target_type": "deal", "timestamp": dag(35), "notes": "Moved to ic_review"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "login", "target_id": None, "target_type": "auth", "timestamp": dag(28), "notes": "Login from 10.0.0.1"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_rejected", "target_id": inv6_str, "target_type": "investor", "timestamp": dag(20), "notes": "Decision: reject for Olympus Private Capital Ltd"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "deal_stage_moved", "target_id": dd2_str, "target_type": "deal", "timestamp": dag(18), "notes": "Moved to ic_review"},
        {"user_id": r_id, "user_email": "risk@zephyrwealth.ai", "user_role": "risk", "user_name": "Marcus Webb", "action": "deal_stage_moved", "target_id": dd3_str, "target_type": "deal", "timestamp": dag(12), "notes": "Moved to ic_review | Override: IC approved sector exception — insurance SaaS classified as Financial Services adjacent. Risk Officer override applied."},
        {"user_id": r_id, "user_email": "risk@zephyrwealth.ai", "user_role": "risk", "user_name": "Marcus Webb", "action": "deal_stage_moved", "target_id": dd1_str, "target_type": "deal", "timestamp": dag(7), "notes": "Moved to closing"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "deal_executed", "target_id": dd1_str, "target_type": "deal", "timestamp": dag(5), "notes": "Transaction executed: CaribPay Solutions Ltd | IBC"},
    ])


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
    print("ZephyrWealth API v5 ready")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ZephyrWealth API", "version": "3.0.0"}

# ─── Auth ────────────────────────────────────────────────────────────────────
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
            nc = attempt_doc.get("failed_count", 0) + 1
            upd = {"failed_count": nc, "last_attempt": now}
            if nc >= 5:
                upd["locked_until"] = now + timedelta(minutes=15)
            await db.login_attempts.update_one({"identifier": identifier}, {"$set": upd})
        else:
            await db.login_attempts.insert_one({"identifier": identifier, "failed_count": 1, "last_attempt": now})
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": identifier})
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, user["email"], user["role"])
    refresh_token = create_refresh_token(user_id)
    cookie_secure = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=cookie_secure, samesite="lax", max_age=28800, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=cookie_secure, samesite="lax", max_age=604800, path="/")
    await db.audit_logs.insert_one({"user_id": user_id, "action": "login", "target_id": None, "target_type": "auth", "timestamp": datetime.now(timezone.utc), "notes": f"Login from {client_ip}"})
    return {"id": user_id, "email": user["email"], "role": user["role"], "name": user.get("name", ""), "title": user.get("title", "")}

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

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
        cookie_secure = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
        response.set_cookie(key="access_token", value=new_token, httponly=True, secure=cookie_secure, samesite="lax", max_age=28800, path="/")
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
    # Capital KPIs
    total_committed = 0.0
    total_called = 0.0
    async for inv in db.investors.find({"kyc_status": "approved", "committed_capital": {"$gt": 0}}):
        total_committed += inv.get("committed_capital", 0) or 0
        total_called += inv.get("capital_called", 0) or 0
    total_uncalled = max(0.0, total_committed - total_called)
    call_rate = round(total_called / total_committed * 100, 1) if total_committed > 0 else 0.0
    return {
        "total_investors": total_investors,
        "pending_kyc": pending_kyc,
        "deals_in_pipeline": deals_in_pipeline,
        "flagged_items": flagged_investors + flagged_deals,
        "total_committed_capital": total_committed,
        "total_capital_called": total_called,
        "total_uncalled": total_uncalled,
        "call_rate": call_rate,
    }

# ─── Dashboard: Charts ───────────────────────────────────────────────────────
@app.get("/api/dashboard/charts")
async def get_dashboard_charts(current_user: dict = Depends(get_current_user)):
    investor_funnel = []
    for status, color in [("pending", "#F59E0B"), ("approved", "#10B981"), ("flagged", "#EF4444"), ("rejected", "#6B7280")]:
        count = await db.investors.count_documents({"kyc_status": status})
        investor_funnel.append({"status": status.capitalize(), "count": count, "color": color})

    stage_counts = {"leads": 0, "due_diligence": 0, "ic_review": 0, "closing": 0}
    async for deal in db.deals.find():
        ps = deal.get("pipeline_stage") or OLD_DEAL_STAGE_MAP.get(deal.get("stage", ""), "leads")
        if ps in stage_counts:
            stage_counts[ps] += 1

    deal_pipeline = [
        {"stage": "Leads", "key": "leads", "count": stage_counts["leads"], "color": "#6B7280"},
        {"stage": "Due Diligence", "key": "due_diligence", "count": stage_counts["due_diligence"], "color": "#F59E0B"},
        {"stage": "IC Review", "key": "ic_review", "count": stage_counts["ic_review"], "color": "#1B3A6B"},
        {"stage": "Closing", "key": "closing", "count": stage_counts["closing"], "color": "#10B981"},
    ]
    return {"investor_funnel": investor_funnel, "deal_pipeline": deal_pipeline}

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
    doc = {"legal_name": body.legal_name, "name": body.legal_name, "entity_type": body.entity_type, "type": "Individual" if body.entity_type == "individual" else "Corporate Entity", "dob": body.dob, "nationality": body.nationality, "residence_country": body.residence_country, "email": body.email, "phone": body.phone, "address": body.address.dict(), "net_worth": body.net_worth, "annual_income": body.annual_income, "source_of_wealth": body.source_of_wealth, "investment_experience": body.investment_experience, "classification": body.classification, "ubo_declarations": [u.dict() for u in (body.ubo_declarations or [])], "accredited_declaration": body.accredited_declaration, "risk_rating": "medium", "kyc_status": "pending", "scorecard_completed": False, "investment_amount": 0, "submitted_date": datetime.now(timezone.utc), "submitted_at": datetime.now(timezone.utc), "country": body.residence_country, "created_at": datetime.now(timezone.utc)}
    result = await db.investors.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    for k in ("submitted_date", "submitted_at", "created_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    await db.audit_logs.insert_one({"user_id": current_user.get("_id"), "action": "investor_created", "target_id": doc["id"], "target_type": "investor", "timestamp": datetime.now(timezone.utc), "notes": f"New investor: {body.legal_name}"})
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
async def upload_investor_document(investor_id: str, file: UploadFile = File(...), document_type: str = Form(...), current_user: dict = Depends(get_current_user)):
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
    record = {"entity_id": investor_id, "document_type": document_type, "file_path": str(file_path), "file_name": safe_name, "file_size": len(content), "uploaded_at": datetime.now(timezone.utc)}
    result = await db.documents.insert_one(record)
    record["id"] = str(result.inserted_id)
    record.pop("_id", None)
    record["uploaded_at"] = record["uploaded_at"].isoformat()
    return record

# ─── Documents: List Investor ─────────────────────────────────────────────────
@app.get("/api/investors/{investor_id}/documents")
async def list_investor_documents(investor_id: str, current_user: dict = Depends(get_current_user)):
    docs = []
    async for doc in db.documents.find({"entity_id": investor_id}).sort("uploaded_at", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("uploaded_at"), datetime):
            doc["uploaded_at"] = doc["uploaded_at"].isoformat()
        docs.append(doc)
    return docs

# ─── Documents: Download Investor ─────────────────────────────────────────────
@app.get("/api/investors/{investor_id}/documents/{document_id}/download")
async def download_investor_document(investor_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
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

# ─── Scorecard: Generate ─────────────────────────────────────────────────────
@app.post("/api/investors/{investor_id}/scorecard")
async def generate_scorecard(investor_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")
    investor = await db.investors.find_one({"_id": oid})
    if not investor:
        raise HTTPException(404, "Investor not found")
    docs_uploaded = []
    async for doc in db.documents.find({"entity_id": investor_id}):
        docs_uploaded.append(doc["document_type"])
    investor_profile = {"legal_name": investor.get("legal_name") or investor.get("name", ""), "entity_type": investor.get("entity_type", "individual"), "nationality": investor.get("nationality", ""), "residence_country": investor.get("residence_country") or investor.get("country", ""), "source_of_wealth": investor.get("source_of_wealth", ""), "net_worth_usd": investor.get("net_worth", 0), "annual_income_usd": investor.get("annual_income", 0), "classification": investor.get("classification", ""), "investment_experience": investor.get("investment_experience", ""), "ubo_declarations": investor.get("ubo_declarations", []), "documents_uploaded": docs_uploaded}
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=str(uuid.uuid4()), system_message=SCORECARD_SYSTEM_PROMPT).with_model("anthropic", "claude-4-sonnet-20250514")
    response = await chat.send_message(UserMessage(text=f"Review this investor profile and generate the compliance scorecard:\n\n{json.dumps(investor_profile, default=str, indent=2)}"))
    raw = response.strip()
    if "```" in raw:
        for part in raw.split("```"):
            candidate = part.strip()
            if candidate.startswith("json"):
                candidate = candidate[4:].strip()
            if candidate.startswith("{"):
                raw = candidate
                break
    try:
        scorecard_data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"Failed to parse AI response: {str(e)}")
    scorecard_doc = {"entity_id": investor_id, "entity_type": "investor", "scorecard_data": scorecard_data, "recommendation": scorecard_data.get("recommendation", "Review"), "generated_at": datetime.now(timezone.utc), "reviewed_by": current_user.get("_id"), "decision": None, "decision_at": None}
    result = await db.compliance_scorecards.insert_one(scorecard_doc)
    await db.investors.update_one({"_id": oid}, {"$set": {"scorecard_completed": True}})
    scorecard_doc["id"] = str(result.inserted_id)
    scorecard_doc.pop("_id", None)
    scorecard_doc["generated_at"] = scorecard_doc["generated_at"].isoformat()
    return scorecard_doc

# ─── Scorecard: Get Latest ───────────────────────────────────────────────────
@app.get("/api/investors/{investor_id}/scorecard")
async def get_scorecard(investor_id: str, current_user: dict = Depends(get_current_user)):
    doc = await db.compliance_scorecards.find_one({"entity_id": investor_id}, sort=[("generated_at", -1)])
    if not doc:
        return None
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    for k in ("generated_at", "decision_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return doc

# ─── Investors: Decision ─────────────────────────────────────────────────────
@app.post("/api/investors/{investor_id}/decision")
async def investor_decision(investor_id: str, body: DecisionRequest, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")
    investor = await db.investors.find_one({"_id": oid})
    if not investor:
        raise HTTPException(404, "Investor not found")
    status_map = {"approve": "approved", "reject": "rejected", "more_info": "pending"}
    new_status = status_map.get(body.decision, "pending")
    await db.investors.update_one({"_id": oid}, {"$set": {"kyc_status": new_status, "reviewed_at": datetime.now(timezone.utc), "reviewed_by": current_user.get("_id")}})
    await db.compliance_scorecards.update_many({"entity_id": investor_id}, {"$set": {"decision": body.decision, "decision_at": datetime.now(timezone.utc), "reviewed_by": current_user.get("_id")}})
    action_labels = {"approve": "investor_approved", "reject": "investor_rejected", "more_info": "investor_more_info_requested"}
    await db.audit_logs.insert_one({"user_id": current_user.get("_id"), "action": action_labels.get(body.decision, "investor_decision"), "target_id": investor_id, "target_type": "investor", "timestamp": datetime.now(timezone.utc), "notes": body.notes or f"Decision: {body.decision} for {investor.get('legal_name') or investor.get('name', '')}"})
    return {"message": f"Decision recorded: {body.decision}", "status": new_status}

# ─── Deals: List ─────────────────────────────────────────────────────────────
@app.get("/api/deals")
async def get_deals(current_user: dict = Depends(get_current_user)):
    deals = []
    async for doc in db.deals.find().sort("submitted_date", -1):
        deals.append(normalize_deal(doc))
    return deals

# ─── Deals: Create ───────────────────────────────────────────────────────────
@app.post("/api/deals")
async def create_deal(body: DealCreateRequest, current_user: dict = Depends(get_current_user)):
    mandate_status = await check_deal_mandate(body.sector, body.geography, body.expected_irr)
    stamp_duty = body.entry_valuation * 0.005
    doc = {"company_name": body.company_name, "name": body.company_name, "sector": body.sector, "geography": body.geography, "asset_class": body.asset_class, "expected_irr": body.expected_irr, "entry_valuation": body.entry_valuation, "entity_type": body.entity_type, "mandate_status": mandate_status, "pipeline_stage": "leads", "stage": "leads", "stamp_duty_estimate": stamp_duty, "status": "active", "type": body.sector, "risk_rating": "medium", "scorecard_completed": False, "deal_size": body.entry_valuation, "target_return": f"{body.expected_irr}%", "submitted_date": datetime.now(timezone.utc), "created_at": datetime.now(timezone.utc), "created_by": current_user.get("_id")}
    result = await db.deals.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["submitted_date"] = doc["submitted_date"].isoformat()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.audit_logs.insert_one({"user_id": current_user.get("_id"), "action": "deal_created", "target_id": doc["id"], "target_type": "deal", "timestamp": datetime.now(timezone.utc), "notes": f"New deal: {body.company_name} | {mandate_status}"})
    return doc

# ─── Deals: Get One ──────────────────────────────────────────────────────────
@app.get("/api/deals/{deal_id}")
async def get_deal(deal_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(deal_id)
    except Exception:
        raise HTTPException(400, "Invalid deal ID")
    doc = await db.deals.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Deal not found")
    return normalize_deal(doc)

# ─── Deals: Move Stage ───────────────────────────────────────────────────────
@app.put("/api/deals/{deal_id}/stage")
async def update_deal_stage(deal_id: str, body: DealStageUpdate, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(deal_id)
    except Exception:
        raise HTTPException(400, "Invalid deal ID")
    deal = await db.deals.find_one({"_id": oid})
    if not deal:
        raise HTTPException(404, "Deal not found")
    STAGE_ORDER = {"leads": 0, "due_diligence": 1, "ic_review": 2, "closing": 3}
    current_stage = deal.get("pipeline_stage") or OLD_DEAL_STAGE_MAP.get(deal.get("stage", ""), "leads")
    is_advancing = STAGE_ORDER.get(body.stage, 0) > STAGE_ORDER.get(current_stage, 0)
    if deal.get("mandate_status") == "Exception" and is_advancing and not body.override_note:
        raise HTTPException(status_code=403, detail="mandate_exception_block")
    update_data: dict = {"pipeline_stage": body.stage, "stage": body.stage}
    new_mandate = deal.get("mandate_status", "In Mandate")
    if body.override_note:
        update_data["mandate_override_note"] = body.override_note
        update_data["mandate_status"] = "Exception Cleared"
        new_mandate = "Exception Cleared"
    await db.deals.update_one({"_id": oid}, {"$set": update_data})
    await db.audit_logs.insert_one({"user_id": current_user.get("_id"), "action": "deal_stage_moved", "target_id": deal_id, "target_type": "deal", "timestamp": datetime.now(timezone.utc), "notes": f"Moved to {body.stage}" + (f" | Override: {body.override_note}" if body.override_note else "")})
    return {"message": f"Deal moved to {body.stage}", "mandate_status": new_mandate, "pipeline_stage": body.stage}

# ─── Deals: Upload Document ───────────────────────────────────────────────────
@app.post("/api/deals/{deal_id}/documents")
async def upload_deal_document(deal_id: str, file: UploadFile = File(...), document_type: str = Form(...), current_user: dict = Depends(get_current_user)):
    allowed_mime = {"application/pdf", "image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in allowed_mime:
        raise HTTPException(400, "Only PDF, JPEG, PNG files are allowed")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "File size must be under 5MB")
    safe_name = file.filename.replace(" ", "_")
    doc_path = DOCUMENTS_DIR / deal_id / document_type
    doc_path.mkdir(parents=True, exist_ok=True)
    file_path = doc_path / safe_name
    file_path.write_bytes(content)
    record = {"entity_id": deal_id, "document_type": document_type, "file_path": str(file_path), "file_name": safe_name, "file_size": len(content), "uploaded_at": datetime.now(timezone.utc)}
    result = await db.documents.insert_one(record)
    record["id"] = str(result.inserted_id)
    record.pop("_id", None)
    record["uploaded_at"] = record["uploaded_at"].isoformat()
    return record

# ─── Deals: List Documents ────────────────────────────────────────────────────
@app.get("/api/deals/{deal_id}/documents")
async def list_deal_documents(deal_id: str, current_user: dict = Depends(get_current_user)):
    docs = []
    async for doc in db.documents.find({"entity_id": deal_id}).sort("uploaded_at", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("uploaded_at"), datetime):
            doc["uploaded_at"] = doc["uploaded_at"].isoformat()
        docs.append(doc)
    return docs

# ─── Deals: Download Document ────────────────────────────────────────────────
@app.get("/api/deals/{deal_id}/documents/{document_id}/download")
async def download_deal_document(deal_id: str, document_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(document_id)
    except Exception:
        raise HTTPException(400, "Invalid document ID")
    doc = await db.documents.find_one({"_id": oid, "entity_id": deal_id})
    if not doc:
        raise HTTPException(404, "Document not found")
    file_path = Path(doc["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "File not found on server")
    return FileResponse(path=str(file_path), filename=doc["file_name"], media_type="application/octet-stream")

# ─── Deals: Health Score ─────────────────────────────────────────────────────
@app.get("/api/deals/{deal_id}/health-score")
async def get_deal_health_score(deal_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(deal_id)
    except Exception:
        raise HTTPException(400, "Invalid deal ID")
    deal = await db.deals.find_one({"_id": oid})
    if not deal:
        raise HTTPException(404, "Deal not found")
    mandate = await db.fund_mandate.find_one({})
    doc_count = await db.documents.count_documents({"entity_id": deal_id})
    document_status = "Complete" if doc_count >= 3 else ("Partial" if doc_count >= 1 else "Missing")
    irr = float(deal.get("expected_irr") or 0)
    financial_alignment = "Aligned"
    if mandate:
        financial_alignment = "Aligned" if mandate["irr_min"] <= irr <= mandate["irr_max"] else "Misaligned"
    mandate_status = deal.get("mandate_status", "In Mandate")
    compliance_risk = {"In Mandate": "Low", "Exception Cleared": "Medium", "Exception": "High", "Blocked": "High"}.get(mandate_status, "Medium")
    entry_valuation = float(deal.get("entry_valuation") or deal.get("deal_size") or 0)
    stamp_duty = entry_valuation * 0.005
    if compliance_risk == "Low" and document_status != "Missing" and financial_alignment == "Aligned":
        overall = "Recommend Approve"
    elif compliance_risk == "High":
        overall = "Block"
    else:
        overall = "Review"
    return {"compliance_risk": compliance_risk, "financial_alignment": financial_alignment, "document_status": document_status, "mandate_status": mandate_status, "stamp_duty_estimate": stamp_duty, "stamp_duty_pct": "0.5%", "entry_valuation": entry_valuation, "overall": overall, "doc_count": doc_count}

# ─── Deals: Execute (Generate Agreement) ─────────────────────────────────────
@app.post("/api/deals/{deal_id}/execute")
async def execute_deal(deal_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(deal_id)
    except Exception:
        raise HTTPException(400, "Invalid deal ID")
    deal = await db.deals.find_one({"_id": oid})
    if not deal:
        raise HTTPException(404, "Deal not found")
    entity_type = deal.get("entity_type", "IBC")
    company_name = deal.get("company_name") or deal.get("name", "Unknown Company")
    entry_val = float(deal.get("entry_valuation") or deal.get("deal_size") or 0)
    irr = deal.get("expected_irr") or 0
    stamp_duty = entry_val * 0.005
    now = datetime.now(timezone.utc)
    if entity_type == "ICON":
        content = generate_participation_agreement(company_name, entry_val, irr, stamp_duty, now, deal_id)
        filename = f"Participation_Agreement_{company_name.replace(' ', '_')}.txt"
    else:
        content = generate_subscription_agreement(company_name, entry_val, irr, stamp_duty, now, deal_id)
        filename = f"Subscription_Agreement_{company_name.replace(' ', '_')}.txt"
    await db.deals.update_one({"_id": oid}, {"$set": {"pipeline_stage": "closing", "stage": "closing"}})
    u_email = current_user.get("email", "")
    u_role = current_user.get("role", "")
    u_name = current_user.get("name", "")
    await db.audit_logs.insert_one({"user_id": current_user.get("_id"), "user_email": u_email, "user_role": u_role, "user_name": u_name, "action": "deal_executed", "target_id": deal_id, "target_type": "deal", "timestamp": now, "notes": f"Transaction executed: {company_name} | {entity_type}"})
    from fastapi.responses import Response
    return Response(content=content.encode("utf-8"), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

# ─── Audit Logs ───────────────────────────────────────────────────────────────
@app.get("/api/audit-logs")
async def get_audit_logs(
    current_user: dict = Depends(get_current_user),
    action: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    if current_user["role"] not in ("compliance", "manager"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query: dict = {}
    if action:
        query["action"] = action
    if from_date or to_date:
        ts_filter: dict = {}
        if from_date:
            try:
                ts_filter["$gte"] = datetime.fromisoformat(from_date).replace(tzinfo=timezone.utc)
            except Exception:
                pass
        if to_date:
            try:
                ts_filter["$lte"] = datetime.fromisoformat(to_date).replace(tzinfo=timezone.utc) + timedelta(days=1)
            except Exception:
                pass
        if ts_filter:
            query["timestamp"] = ts_filter

    if role:
        role_user_ids = []
        async for u in db.users.find({"role": role}, {"_id": 1}):
            role_user_ids.append(str(u["_id"]))
        if not role_user_ids:
            return {"logs": [], "total": 0, "page": page, "limit": limit, "total_pages": 0}
        query["user_id"] = {"$in": role_user_ids}

    total = await db.audit_logs.count_documents(query)
    total_pages = max(1, (total + limit - 1) // limit)
    skip = (page - 1) * limit

    # Build user lookup map
    user_ids_in_page = set()
    raw_logs = []
    async for doc in db.audit_logs.find(query).sort("timestamp", -1).skip(skip).limit(limit):
        if doc.get("user_id"):
            user_ids_in_page.add(doc["user_id"])
        raw_logs.append(doc)

    user_map: dict = {}
    for uid in user_ids_in_page:
        if uid and uid != "system":
            try:
                u = await db.users.find_one({"_id": ObjectId(uid)}, {"_id": 0, "email": 1, "role": 1, "name": 1})
                if u:
                    user_map[uid] = u
            except Exception:
                pass

    logs = []
    for doc in raw_logs:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("timestamp"), datetime):
            doc["timestamp"] = doc["timestamp"].isoformat()
        uid = doc.get("user_id")
        u_info = user_map.get(uid or "", {})
        doc["user_email"] = doc.get("user_email") or u_info.get("email", "Unknown")
        doc["user_role"] = doc.get("user_role") or u_info.get("role", "unknown")
        doc["user_name"] = doc.get("user_name") or u_info.get("name", "")
        logs.append(doc)

    return {"logs": logs, "total": total, "page": page, "limit": limit, "total_pages": total_pages}


# ─── Deal PDF Export (Feature 8) ─────────────────────────────────────────────
@app.get("/api/deals/{deal_id}/export-pdf")
async def export_deal_pdf(deal_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    try:
        oid = ObjectId(deal_id)
    except Exception:
        raise HTTPException(400, "Invalid deal ID")
    deal = await db.deals.find_one({"_id": oid})
    if not deal:
        raise HTTPException(404, "Deal not found")
    deal = normalize_deal(deal)

    mandate = await db.fund_mandate.find_one({})
    doc_count = await db.documents.count_documents({"entity_id": deal_id})

    irr = float(deal.get("expected_irr") or 0)
    entry_val = float(deal.get("entry_valuation") or 0)
    stamp_duty = entry_val * 0.005
    mandate_status = deal.get("mandate_status", "In Mandate")
    document_status = "Complete" if doc_count >= 3 else ("Partial" if doc_count >= 1 else "Missing")
    financial_alignment = "Aligned"
    if mandate:
        financial_alignment = "Aligned" if mandate.get("irr_min", 0) <= irr <= mandate.get("irr_max", 100) else "Misaligned"
    compliance_risk = {"In Mandate": "Low", "Exception Cleared": "Medium", "Exception": "High", "Blocked": "High"}.get(mandate_status, "Medium")
    if compliance_risk == "Low" and document_status != "Missing" and financial_alignment == "Aligned":
        overall = "Recommend Approve"
    elif compliance_risk == "High":
        overall = "Block"
    else:
        overall = "Review"

    ts = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    S = _pdf_styles()
    u_name = current_user.get("name", current_user.get("email", "Unknown"))
    u_role = current_user["role"].title()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=33*mm, bottomMargin=22*mm, leftMargin=15*mm, rightMargin=15*mm)
    hf = _partial(_hf_callback, title_line2="Investment Committee Pack", user_name=u_name, user_role=u_role, ts=ts)

    story = []
    story.append(Paragraph(deal.get("company_name", ""), S['h1']))
    story.append(Paragraph("Investment Committee Pack — Confidential", S['small']))
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#1B3A6B'), spaceAfter=6))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Deal Overview", S['h2']))
    deal_tbl = Table([
        ['Field', 'Value'],
        ['Company Name', deal.get('company_name', '—')],
        ['Sector', deal.get('sector', '—')],
        ['Geography', deal.get('geography', '—')],
        ['Asset Class', deal.get('asset_class', '—')],
        ['Entity Type', deal.get('entity_type', '—')],
        ['Entry Valuation', f"USD {entry_val:,.0f}"],
        ['Expected IRR', f"{irr}%"],
        ['Pipeline Stage', STAGE_LABELS.get(deal.get('pipeline_stage', ''), deal.get('pipeline_stage', '—'))],
        ['Stamp Duty Estimate', f"USD {stamp_duty:,.0f} (0.5% of entry valuation)"],
    ], colWidths=[55*mm, 115*mm])
    deal_tbl.setStyle(_tbl_style())
    story.append(deal_tbl)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Mandate Check", S['h2']))
    if mandate:
        in_sec = deal.get('sector', '') in mandate.get('allowed_sectors', [])
        in_geo = deal.get('geography', '') in mandate.get('allowed_geographies', [])
        in_irr = mandate.get('irr_min', 0) <= irr <= mandate.get('irr_max', 100)
        m_data = [
            ['Criterion', 'Required', 'Deal Value', 'Result'],
            ['Sector', ', '.join(mandate.get('allowed_sectors', [])), deal.get('sector', '—'), 'PASS' if in_sec else 'FAIL'],
            ['Geography', ', '.join(mandate.get('allowed_geographies', [])), deal.get('geography', '—'), 'PASS' if in_geo else 'FAIL'],
            ['IRR Range', f"{mandate.get('irr_min', 0)}%–{mandate.get('irr_max', 100)}%", f"{irr}%", 'PASS' if in_irr else 'FAIL'],
        ]
        m_tbl = Table(m_data, colWidths=[40*mm, 60*mm, 40*mm, 30*mm])
        ms = _tbl_style()
        for ri, row in enumerate(m_data[1:], 1):
            c = rl_colors.HexColor('#10B981') if row[-1] == 'PASS' else rl_colors.HexColor('#EF4444')
            ms.add('TEXTCOLOR', (3, ri), (3, ri), c)
            ms.add('FONTNAME', (3, ri), (3, ri), 'Helvetica-Bold')
        m_tbl.setStyle(ms)
        story.append(m_tbl)
    mc = rl_colors.HexColor('#10B981') if mandate_status == 'In Mandate' else rl_colors.HexColor('#EF4444')
    ms_lbl = f"Overall Mandate Status: {mandate_status}"
    story.append(Spacer(1, 3*mm))
    ov_tbl = Table([[ms_lbl]], colWidths=[170*mm])
    ov_tbl.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), rl_colors.HexColor('#F8F9FA')), ('TEXTCOLOR', (0, 0), (0, 0), mc), ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (0, 0), 10), ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#E5E7EB')), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
    story.append(ov_tbl)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Deal Health Score", S['h2']))
    h_data = [
        ['Indicator', 'Assessment'],
        ['Compliance Risk', compliance_risk],
        ['Financial Alignment', financial_alignment],
        ['Document Status', document_status],
        ['Mandate Status', mandate_status],
        ['Documents on File', str(doc_count)],
        ['Overall Assessment', overall],
    ]
    h_tbl = Table(h_data, colWidths=[70*mm, 100*mm])
    hs = _tbl_style()
    for ri, row in enumerate(h_data[1:], 1):
        col_hex = _PDF_HC.get(row[1])
        if col_hex:
            hs.add('TEXTCOLOR', (1, ri), (1, ri), rl_colors.HexColor(col_hex))
            hs.add('FONTNAME', (1, ri), (1, ri), 'Helvetica-Bold')
    h_tbl.setStyle(hs)
    story.append(h_tbl)
    story.append(Spacer(1, 6*mm))

    if deal.get("mandate_override_note"):
        story.append(Paragraph("Risk Officer Override Note", S['h3']))
        story.append(Paragraph(deal["mandate_override_note"], S['body']))
        story.append(Spacer(1, 4*mm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=3))
    story.append(Paragraph("Rule-based assessment — human review required — ZephyrWealth Compliance Framework", S['small']))
    story.append(Paragraph(f"Report generated: {ts}  |  Prepared by: {u_name} ({u_role})", S['small']))

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    safe = deal.get('company_name', 'Deal').replace(' ', '_')
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="IC_Pack_{safe}.pdf"'})


# ─── Investor KYC PDF Export (Feature 9) ─────────────────────────────────────
@app.get("/api/investors/{investor_id}/export-pdf")
async def export_investor_pdf(investor_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(status_code=403, detail="Compliance role required")
    try:
        oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")
    investor = await db.investors.find_one({"_id": oid})
    if not investor:
        raise HTTPException(404, "Investor not found")
    investor["id"] = str(investor["_id"])
    investor.pop("_id", None)

    docs = []
    async for d in db.documents.find({"entity_id": investor_id}):
        d["id"] = str(d["_id"])
        d.pop("_id", None)
        docs.append(d)

    sc_doc = await db.compliance_scorecards.find_one({"entity_id": investor_id})
    sc = sc_doc.get("scorecard_data") if sc_doc else None

    ts = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    S = _pdf_styles()
    u_name = current_user.get("name", current_user.get("email", "Unknown"))
    u_role = current_user["role"].title()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=33*mm, bottomMargin=22*mm, leftMargin=15*mm, rightMargin=15*mm)
    hf = _partial(_hf_callback, title_line2="KYC Compliance Pack", user_name=u_name, user_role=u_role, ts=ts)

    story = []
    inv_name = investor.get("legal_name") or investor.get("name", "Unknown")
    story.append(Paragraph(inv_name, S['h1']))
    story.append(Paragraph("KYC Compliance Pack — Confidential", S['small']))
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#1B3A6B'), spaceAfter=6))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Investor Profile", S['h2']))
    kyc_status = investor.get("kyc_status", "pending")
    sc_tbl = Table([
        ['Field', 'Value'],
        ['Legal Name', inv_name],
        ['Entity Type', investor.get('entity_type', '—').title()],
        ['Nationality', investor.get('nationality', '—')],
        ['Residence', investor.get('residence_country') or investor.get('country', '—')],
        ['KYC Status', kyc_status.upper()],
        ['Risk Rating', (investor.get('risk_rating') or '—').upper()],
        ['Classification', investor.get('classification', '—')],
        ['Investment Amount', f"USD {investor.get('investment_amount', 0):,}" if investor.get('investment_amount') else '—'],
    ], colWidths=[55*mm, 115*mm])
    sc_tbl.setStyle(_tbl_style())
    story.append(sc_tbl)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph(f"KYC Document Checklist ({len(docs)} document{'s' if len(docs) != 1 else ''} on file)", S['h2']))
    DOC_LABELS = {"passport": "Passport / National ID", "proof_of_address": "Proof of Address", "source_of_wealth_doc": "Source of Wealth Declaration", "corporate_documents": "Corporate / Incorporation Documents", "cap_table": "Cap Table", "financials": "Financial Statements"}
    if docs:
        d_rows = [['Document Type', 'File Name', 'Upload Date']]
        for d in docs:
            d_rows.append([DOC_LABELS.get(d.get('document_type', ''), d.get('document_type', '—')), d.get('file_name', '—'), datetime.fromisoformat(str(d.get('uploaded_at', ''))).strftime('%d %b %Y') if d.get('uploaded_at') else '—'])
        d_tbl = Table(d_rows, colWidths=[60*mm, 70*mm, 40*mm])
        d_tbl.setStyle(_tbl_style())
        story.append(d_tbl)
    else:
        story.append(Paragraph("No documents uploaded.", S['body']))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("AI Compliance Scorecard", S['h2']))
    if sc:
        score = sc.get('identity_confidence_score', 0)
        score_col = rl_colors.HexColor('#10B981') if score >= 70 else (rl_colors.HexColor('#F59E0B') if score >= 40 else rl_colors.HexColor('#EF4444'))
        sc_rows = [
            ['Indicator', 'Status'],
            ['Sanctions Status', sc.get('sanctions_status', '—')],
            ['Identity / UBO', sc.get('identity_status', '—')],
            ['Document Status', sc.get('document_status', '—')],
            ['Source of Funds', sc.get('source_of_funds', '—')],
            ['PEP Status', sc.get('pep_status', '—')],
            ['Fund Mandate', sc.get('mandate_status', '—')],
        ]
        sc_tbl2 = Table(sc_rows, colWidths=[70*mm, 100*mm])
        ss2 = _tbl_style()
        for ri, row in enumerate(sc_rows[1:], 1):
            col_hex = _PDF_HC.get(row[1])
            if col_hex:
                ss2.add('TEXTCOLOR', (1, ri), (1, ri), rl_colors.HexColor(col_hex))
                ss2.add('FONTNAME', (1, ri), (1, ri), 'Helvetica-Bold')
        sc_tbl2.setStyle(ss2)
        story.append(sc_tbl2)
        story.append(Spacer(1, 3*mm))

        rec = sc.get('recommendation', '—')
        rec_col = rl_colors.HexColor(_PDF_HC.get(rec, '#374151'))
        rec_tbl = Table([[f"Recommendation: {rec}  |  Score: {score}/100  |  {sc.get('overall_rating', '')}  |  EDD: {'YES' if sc.get('edd_required') else 'NO'}"]], colWidths=[170*mm])
        rec_tbl.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), rl_colors.HexColor('#252523')), ('TEXTCOLOR', (0, 0), (0, 0), rec_col), ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (0, 0), 9), ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
        story.append(rec_tbl)
        story.append(Spacer(1, 3*mm))
        if sc.get('summary'):
            story.append(Paragraph("Analysis Summary", S['h3']))
            story.append(Paragraph(sc['summary'], S['body']))
    else:
        story.append(Paragraph("No AI Compliance Scorecard has been generated for this investor.", S['body']))
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph("Approval / Decision History", S['h2']))
    dec_rows = [['Date', 'Action', 'Officer']]
    if sc_doc and sc_doc.get("decision"):
        dec_date = sc_doc.get("decision_at")
        dec_str = datetime.fromisoformat(str(dec_date)).strftime('%d %b %Y') if dec_date else '—'
        dec_rows.append([dec_str, sc_doc["decision"].title(), u_name])
    if investor.get("reviewed_at"):
        r_date = datetime.fromisoformat(str(investor["reviewed_at"])).strftime('%d %b %Y')
        dec_rows.append([r_date, f"KYC Status set to {kyc_status.title()}", u_name])
    if len(dec_rows) == 1:
        dec_rows.append(['—', 'No decisions recorded', '—'])
    dec_tbl = Table(dec_rows, colWidths=[40*mm, 90*mm, 40*mm])
    dec_tbl.setStyle(_tbl_style())
    story.append(dec_tbl)

    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=3))
    story.append(Paragraph(f"Report generated: {ts}  |  Prepared by: {u_name} ({u_role})", S['small']))

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    safe = inv_name.replace(' ', '_')
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="KYC_Pack_{safe}.pdf"'})


# ─── TAV Regulatory Report PDF (Feature 11) ──────────────────────────────────
@app.get("/api/reports/tav-pdf")
async def export_tav_pdf(
    current_user: dict = Depends(get_current_user),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
):
    if current_user["role"] != "compliance":
        raise HTTPException(status_code=403, detail="Compliance role required")

    from datetime import date as ddate
    now_dt = datetime.now(timezone.utc)
    if from_date and to_date:
        period_from = from_date
        period_to = to_date
    else:
        m = now_dt.month
        q = (m - 1) // 3
        period_from = ddate(now_dt.year, q * 3 + 1, 1).isoformat()
        qe_month = q * 3 + 3
        qe_year = now_dt.year
        import calendar
        period_to = ddate(qe_year, qe_month, calendar.monthrange(qe_year, qe_month)[1]).isoformat()

    q_num = (datetime.fromisoformat(period_from).month - 1) // 3 + 1
    q_year = datetime.fromisoformat(period_from).year
    quarter_label = f"Q{q_num} {q_year}"

    fund_profile = await db.fund_profile.find_one({}) or {}
    mandate = await db.fund_mandate.find_one({}) or {}

    active_deals = []
    async for d in db.deals.find({"pipeline_stage": {"$in": ["closing", "ic_review"]}}):
        d["id"] = str(d["_id"])
        d.pop("_id", None)
        active_deals.append(d)

    total_tav = sum(float(d.get("entry_valuation") or 0) for d in active_deals)

    sector_breakdown: dict = {}
    entity_breakdown: dict = {}
    for d in active_deals:
        sec = d.get("sector", "Other")
        sector_breakdown[sec] = sector_breakdown.get(sec, 0) + float(d.get("entry_valuation") or 0)
        et = d.get("entity_type", "IBC")
        entity_breakdown[et] = entity_breakdown.get(et, 0) + float(d.get("entry_valuation") or 0)

    total_inv = await db.investors.count_documents({})
    approved_inv = await db.investors.count_documents({"kyc_status": "approved"})
    pending_inv = await db.investors.count_documents({"kyc_status": "pending"})
    flagged_inv = await db.investors.count_documents({"kyc_status": "flagged"})
    rejected_inv = await db.investors.count_documents({"kyc_status": "rejected"})
    ind_inv = await db.investors.count_documents({"entity_type": "individual"})
    corp_inv = await db.investors.count_documents({"entity_type": "corporate"})
    total_sc = await db.compliance_scorecards.count_documents({})
    mandate_exceptions = await db.deals.count_documents({"mandate_status": "Exception"})

    ts = now_dt.strftime("%d %b %Y, %H:%M UTC")
    S = _pdf_styles()
    u_name = current_user.get("name", current_user.get("email", "Unknown"))
    u_role = current_user["role"].title()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=33*mm, bottomMargin=22*mm, leftMargin=15*mm, rightMargin=15*mm)
    hf = _partial(_hf_callback, title_line2=f"TAV Report — {quarter_label}", user_name=u_name, user_role=u_role, ts=ts)

    story = []

    # ── Cover Page ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph(fund_profile.get("fund_name", "Zephyr Caribbean Growth Fund I"), S['cover_title']))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="80%", thickness=2, color=rl_colors.HexColor('#00A8C6'), spaceAfter=8, hAlign='CENTER'))
    story.append(Paragraph(f"Total Asset Value Report — {quarter_label}", S['cover_sub']))
    story.append(Spacer(1, 8*mm))
    cover_data = [
        ['Reporting Period', f"{period_from}  to  {period_to}"],
        ['Generation Date', ts],
        ['Prepared By', f"{u_name} ({u_role})"],
        ['Fund License', fund_profile.get("license_number", "SCB-2024-PE-0042")],
        ['Fund Manager', fund_profile.get("fund_manager", "Zephyr Asset Management Ltd")],
    ]
    cv_tbl = Table(cover_data, colWidths=[55*mm, 105*mm])
    cv_tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), rl_colors.HexColor('#6B7280')),
        ('TEXTCOLOR', (1, 0), (1, -1), rl_colors.HexColor('#1F2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('BACKGROUND', (0, 0), (0, -1), rl_colors.HexColor('#F8F9FA')),
    ]))
    story.append(cv_tbl)
    story.append(Spacer(1, 16*mm))
    story.append(Paragraph("CONFIDENTIAL — FOR REGULATORY SUBMISSION ONLY", ParagraphStyle('conf', parent=S['small'], alignment=1, textColor=rl_colors.HexColor('#EF4444'), fontName='Helvetica-Bold', fontSize=9)))
    story.append(PageBreak())

    # ── Section 1: Fund Overview ──────────────────────────────────────────────
    story.append(Paragraph("Section 1 — Fund Overview", S['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=4))
    s1_data = [
        ['Parameter', 'Details'],
        ['Fund Name', fund_profile.get("fund_name", "Zephyr Caribbean Growth Fund I")],
        ['Fund Manager', fund_profile.get("fund_manager", "Zephyr Asset Management Ltd")],
        ['License Number', fund_profile.get("license_number", "SCB-2024-PE-0042")],
        ['Allowed Sectors', ', '.join(fund_profile.get("mandate_sectors", mandate.get("allowed_sectors", [])))],
        ['Allowed Geographies', ', '.join(fund_profile.get("mandate_geographies", mandate.get("allowed_geographies", [])))],
        ['Target IRR Range', f"{fund_profile.get('irr_min', mandate.get('irr_min', 15))}% – {fund_profile.get('irr_max', mandate.get('irr_max', 25))}%"],
    ]
    s1_tbl = Table(s1_data, colWidths=[55*mm, 115*mm])
    s1_tbl.setStyle(_tbl_style())
    story.append(s1_tbl)
    story.append(Spacer(1, 8*mm))

    # ── Section 2: Portfolio Summary Table ───────────────────────────────────
    story.append(Paragraph("Section 2 — Portfolio Summary (Active Deals)", S['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=4))
    if active_deals:
        p2_rows = [['Company', 'Sector', 'Geography', 'Type', 'Valuation (USD)', 'IRR%', 'Mandate']]
        for d in active_deals:
            p2_rows.append([
                d.get('company_name', '—'), d.get('sector', '—'), d.get('geography', '—'),
                d.get('entity_type', '—'), f"${float(d.get('entry_valuation') or 0):,.0f}",
                f"{d.get('expected_irr', 0)}%", d.get('mandate_status', '—'),
            ])
        p2_tbl = Table(p2_rows, colWidths=[40*mm, 28*mm, 25*mm, 16*mm, 28*mm, 16*mm, 17*mm])
        ps2 = _tbl_style()
        for ri, row in enumerate(p2_rows[1:], 1):
            ms = row[-1]
            c = rl_colors.HexColor('#10B981') if ms == 'In Mandate' else rl_colors.HexColor('#EF4444')
            ps2.add('TEXTCOLOR', (6, ri), (6, ri), c)
            ps2.add('FONTNAME', (6, ri), (6, ri), 'Helvetica-Bold')
        p2_tbl.setStyle(ps2)
        story.append(p2_tbl)
    else:
        story.append(Paragraph("No active deals in Closing or IC Review at this time.", S['body']))
    story.append(Spacer(1, 8*mm))

    # ── Section 3: Total Asset Value ──────────────────────────────────────────
    story.append(Paragraph("Section 3 — Total Asset Value", S['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=4))
    tav_highlight = Table([[f"USD {total_tav:,.0f}", "Total Asset Value"]], colWidths=[85*mm, 85*mm])
    tav_highlight.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), rl_colors.HexColor('#1B3A6B')),
        ('TEXTCOLOR', (0, 0), (0, 0), rl_colors.white),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (0, 0), 18),
        ('BACKGROUND', (1, 0), (1, 0), rl_colors.HexColor('#00A8C6')),
        ('TEXTCOLOR', (1, 0), (1, 0), rl_colors.white),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica'), ('FONTSIZE', (1, 0), (1, 0), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(tav_highlight)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Breakdown by Sector", S['h3']))
    sec_rows = [['Sector', 'Total Valuation (USD)', '% of TAV']]
    for sec, val in sorted(sector_breakdown.items(), key=lambda x: -x[1]):
        pct = (val / total_tav * 100) if total_tav else 0
        sec_rows.append([sec, f"${val:,.0f}", f"{pct:.1f}%"])
    sec_tbl = Table(sec_rows, colWidths=[70*mm, 60*mm, 40*mm])
    sec_tbl.setStyle(_tbl_style())
    story.append(sec_tbl)
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("Breakdown by Entity Type (IBC vs ICON)", S['h3']))
    ent_rows = [['Entity Type', 'Total Valuation (USD)', '% of TAV']]
    for et, val in sorted(entity_breakdown.items(), key=lambda x: -x[1]):
        pct = (val / total_tav * 100) if total_tav else 0
        ent_rows.append([et, f"${val:,.0f}", f"{pct:.1f}%"])
    ent_tbl = Table(ent_rows, colWidths=[70*mm, 60*mm, 40*mm])
    ent_tbl.setStyle(_tbl_style())
    story.append(ent_tbl)
    story.append(Spacer(1, 8*mm))

    # ── Section 4: Investor Base Summary ─────────────────────────────────────
    story.append(Paragraph("Section 4 — Investor Base Summary", S['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=4))
    s4_data = [
        ['Metric', 'Count'],
        ['Total Investors', str(total_inv)],
        ['Approved', str(approved_inv)],
        ['Individual Investors', str(ind_inv)],
        ['Corporate / Institutional', str(corp_inv)],
    ]
    s4_tbl = Table(s4_data, colWidths=[100*mm, 70*mm])
    s4_tbl.setStyle(_tbl_style())
    story.append(s4_tbl)
    story.append(Spacer(1, 8*mm))

    # ── Section 5: Compliance Summary ────────────────────────────────────────
    story.append(Paragraph("Section 5 — Compliance Summary", S['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=4))
    sc_rate = f"{(total_sc / max(total_inv, 1) * 100):.0f}%" if total_inv else "N/A"
    s5_data = [
        ['Compliance Metric', 'Value'],
        ['Investors Approved', str(approved_inv)],
        ['Investors Pending KYC', str(pending_inv)],
        ['Investors Flagged (AML/KYC)', str(flagged_inv)],
        ['Investors Rejected', str(rejected_inv)],
        ['Mandate Exceptions (Active Deals)', str(mandate_exceptions)],
        ['AI Scorecard Completion Rate', sc_rate],
    ]
    s5_tbl = Table(s5_data, colWidths=[100*mm, 70*mm])
    s5s = _tbl_style()
    for ri, row in enumerate(s5_data[1:], 1):
        v = row[1]
        if v not in ('0', 'N/A', '100%') and ri in [3, 4, 5, 6]:
            s5s.add('TEXTCOLOR', (1, ri), (1, ri), rl_colors.HexColor('#EF4444'))
            s5s.add('FONTNAME', (1, ri), (1, ri), 'Helvetica-Bold')
    s5_tbl.setStyle(s5s)
    story.append(s5_tbl)

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    fname = f"TAV_Report_{quarter_label.replace(' ', '_')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ─── Demo Reset (Feature: Demo Reset Button) ──────────────────────────────────
@app.post("/api/admin/demo-reset")
async def demo_reset(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(status_code=403, detail="Compliance role required")

    cleaned: dict = {}

    # 1. TEST_ prefixed investors + related data
    test_inv_ids = []
    async for inv in db.investors.find({"$or": [
        {"name": {"$regex": "^TEST_", "$options": "i"}},
        {"legal_name": {"$regex": "^TEST_", "$options": "i"}},
        {"name": "Test API User"},
    ]}):
        test_inv_ids.append(str(inv["_id"]))
    if test_inv_ids:
        await db.documents.delete_many({"entity_id": {"$in": test_inv_ids}})
        await db.compliance_scorecards.delete_many({"entity_id": {"$in": test_inv_ids}})
        r = await db.investors.delete_many({"_id": {"$in": [ObjectId(i) for i in test_inv_ids]}})
        cleaned["test_investors_removed"] = r.deleted_count

    # 2. TEST_ prefixed deals + related data
    test_deal_ids = []
    async for deal in db.deals.find({"$or": [
        {"company_name": {"$regex": "^TEST_", "$options": "i"}},
        {"name": {"$regex": "^TEST_", "$options": "i"}},
    ]}):
        test_deal_ids.append(str(deal["_id"]))
    if test_deal_ids:
        await db.documents.delete_many({"entity_id": {"$in": test_deal_ids}})
        r = await db.deals.delete_many({"_id": {"$in": [ObjectId(i) for i in test_deal_ids]}})
        cleaned["test_deals_removed"] = r.deleted_count

    # 3. Phase 4 demo investors (by exact name) + related data
    DEMO_INV_NAMES = [
        "Cayman Tech Ventures SPV Ltd", "Nassau Capital Partners IBC",
        "Marcus Harrington", "Yolanda Santos",
        "Meridian Global Holdings Ltd", "Olympus Private Capital Ltd",
    ]
    demo_inv_ids = []
    async for inv in db.investors.find({"$or": [
        {"name": {"$in": DEMO_INV_NAMES}},
        {"legal_name": {"$in": DEMO_INV_NAMES}},
    ]}):
        demo_inv_ids.append(str(inv["_id"]))
    if demo_inv_ids:
        await db.documents.delete_many({"entity_id": {"$in": demo_inv_ids}})
        await db.compliance_scorecards.delete_many({"entity_id": {"$in": demo_inv_ids}})
        r = await db.investors.delete_many({"_id": {"$in": [ObjectId(i) for i in demo_inv_ids]}})
        cleaned["demo_investors_removed"] = r.deleted_count

    # 4. Phase 4 demo deals (by exact name) + related data
    DEMO_DEAL_NAMES = [
        "CaribPay Solutions Ltd", "AgroHub Africa Ltd",
        "InsureSync Caribbean ICON", "SaaSAfrica BV", "CariLogix Ltd",
    ]
    demo_deal_ids = []
    async for deal in db.deals.find({"$or": [
        {"company_name": {"$in": DEMO_DEAL_NAMES}},
        {"name": {"$in": DEMO_DEAL_NAMES}},
    ]}):
        demo_deal_ids.append(str(deal["_id"]))
    if demo_deal_ids:
        await db.documents.delete_many({"entity_id": {"$in": demo_deal_ids}})
        r = await db.deals.delete_many({"_id": {"$in": [ObjectId(i) for i in demo_deal_ids]}})
        cleaned["demo_deals_removed"] = r.deleted_count

    # 5. Clear ALL audit logs for a pristine log history
    r = await db.audit_logs.delete_many({})
    cleaned["audit_logs_cleared"] = r.deleted_count

    # 6. Remove idempotency guard so Phase 4 seed runs fresh
    await db.fund_profile.delete_one({"fund_name": "Zephyr Caribbean Growth Fund I"})
    cleaned["fund_profile_reset"] = True

    # 7. Clear Phase 5 data
    r5a = await db.placement_agents.delete_many({})
    r5b = await db.capital_calls.delete_many({})
    r5c = await db.trailer_fee_invoices.delete_many({})
    cleaned["placement_agents_cleared"] = r5a.deleted_count
    cleaned["capital_calls_cleared"] = r5b.deleted_count
    cleaned["trailer_fee_invoices_cleared"] = r5c.deleted_count

    # 8. Re-seed Phase 4 pristine data
    await seed_demo_phase4()
    await seed_demo_phase5()
    cleaned["seed_restored"] = True

    # 9. Log the reset (in the freshly seeded audit log)
    await db.audit_logs.insert_one({
        "user_id": current_user.get("_id"),
        "user_email": current_user.get("email", ""),
        "user_role": current_user.get("role", ""),
        "user_name": current_user.get("name", ""),
        "action": "demo_reset",
        "target_id": None,
        "target_type": "system",
        "timestamp": datetime.now(timezone.utc),
        "notes": f"Demo data reset executed by {current_user.get('name', '')}. Cleaned: test_investors={cleaned.get('test_investors_removed', 0)}, test_deals={cleaned.get('test_deals_removed', 0)}, demo_investors={cleaned.get('demo_investors_removed', 0)}, demo_deals={cleaned.get('demo_deals_removed', 0)}, audit_logs={cleaned.get('audit_logs_cleared', 0)}",
    })

    return {
        "message": "Demo data reset successful. Pristine Phase 4 & 5 data restored.",
        "cleaned": cleaned,
    }


# ─── Portfolio: Summary ───────────────────────────────────────────────────────
@app.get("/api/portfolio/summary")
async def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    deals = []
    async for doc in db.deals.find():
        deals.append(normalize_deal(doc))

    # KPIs
    total_portfolio_value = sum(d.get("entry_valuation", 0) or 0 for d in deals)
    active_investments = sum(1 for d in deals if d.get("pipeline_stage") in ("ic_review", "closing"))

    total_val_for_irr = sum((d.get("entry_valuation", 0) or 0) for d in deals)
    weighted_irr_sum = sum((d.get("expected_irr", 0) or 0) * (d.get("entry_valuation", 0) or 0) for d in deals)
    weighted_avg_irr = (weighted_irr_sum / total_val_for_irr) if total_val_for_irr > 0 else 0

    total_deals = len(deals)
    exception_deals = sum(1 for d in deals if d.get("mandate_status") == "Exception")
    mandate_exception_rate = (exception_deals / total_deals * 100) if total_deals > 0 else 0

    # Sector allocation
    sector_map: dict = {}
    for d in deals:
        sector = d.get("sector") or "Unknown"
        val = d.get("entry_valuation", 0) or 0
        if sector not in sector_map:
            sector_map[sector] = {"name": sector, "value": 0, "count": 0}
        sector_map[sector]["value"] += val
        sector_map[sector]["count"] += 1

    # Geography allocation
    geo_map: dict = {}
    for d in deals:
        geo = d.get("geography") or "Unknown"
        val = d.get("entry_valuation", 0) or 0
        if geo not in geo_map:
            geo_map[geo] = {"name": geo, "value": 0, "count": 0}
        geo_map[geo]["value"] += val
        geo_map[geo]["count"] += 1

    # IRR distribution (sorted by IRR desc)
    irr_distribution = sorted([
        {
            "id": d.get("id", ""),
            "name": d.get("company_name", ""),
            "irr": d.get("expected_irr", 0) or 0,
            "valuation": d.get("entry_valuation", 0) or 0,
            "mandate_status": d.get("mandate_status", "In Mandate"),
        }
        for d in deals
    ], key=lambda x: x["irr"], reverse=True)

    # Pipeline stage value
    stage_map: dict = {"leads": 0, "due_diligence": 0, "ic_review": 0, "closing": 0}
    for d in deals:
        ps = d.get("pipeline_stage", "leads")
        if ps in stage_map:
            stage_map[ps] += d.get("entry_valuation", 0) or 0
    pipeline_stage_value = [
        {"stage": "Leads", "key": "leads", "value": stage_map["leads"]},
        {"stage": "Due Diligence", "key": "due_diligence", "value": stage_map["due_diligence"]},
        {"stage": "IC Review", "key": "ic_review", "value": stage_map["ic_review"]},
        {"stage": "Closing", "key": "closing", "value": stage_map["closing"]},
    ]

    # Holdings with inline health score
    mandate = await db.fund_mandate.find_one({})
    holdings = []
    for d in deals:
        ms = d.get("mandate_status", "In Mandate")
        irr_val = d.get("expected_irr", 0) or 0
        if mandate:
            in_irr = mandate.get("irr_min", 0) <= irr_val <= mandate.get("irr_max", 100)
        else:
            in_irr = True
        if ms in ("In Mandate", "Exception Cleared") and in_irr:
            health_score = "Good"
        elif ms == "Exception":
            health_score = "Review"
        else:
            health_score = "Poor"
        holdings.append({
            "id": d.get("id", ""),
            "company_name": d.get("company_name", ""),
            "sector": d.get("sector", ""),
            "geography": d.get("geography", ""),
            "entity_type": d.get("entity_type", "IBC"),
            "pipeline_stage": d.get("pipeline_stage", "leads"),
            "entry_valuation": d.get("entry_valuation", 0) or 0,
            "expected_irr": irr_val,
            "mandate_status": ms,
            "health_score": health_score,
        })

    # Capital Called vs Uncalled by share class
    class_capital: dict = {"A": {"called": 0.0, "uncalled": 0.0}, "B": {"called": 0.0, "uncalled": 0.0}, "C": {"called": 0.0, "uncalled": 0.0}}
    async for inv in db.investors.find({"committed_capital": {"$gt": 0}}):
        cls = inv.get("share_class", "")
        if cls in class_capital:
            class_capital[cls]["called"] += inv.get("capital_called", 0) or 0
            class_capital[cls]["uncalled"] += inv.get("capital_uncalled", 0) or (inv.get("committed_capital", 0) - (inv.get("capital_called", 0) or 0))
    capital_by_class = [{"class_label": f"Class {k}", "called": round(v["called"], 2), "uncalled": round(v["uncalled"], 2)} for k, v in class_capital.items()]

    return {
        "kpis": {
            "total_portfolio_value": total_portfolio_value,
            "active_investments": active_investments,
            "weighted_avg_irr": round(weighted_avg_irr, 2),
            "mandate_exception_rate": round(mandate_exception_rate, 1),
        },
        "charts": {
            "sector_allocation": list(sector_map.values()),
            "geography_allocation": list(geo_map.values()),
            "irr_distribution": irr_distribution,
            "pipeline_stage_value": pipeline_stage_value,
            "capital_by_class": capital_by_class,
        },
        "holdings": holdings,
    }


# ─── Phase 5 Fund-Level Bank Details ─────────────────────────────────────────
_FUND_BANK = {
    "bank_name": "Bank of The Bahamas",
    "account_name": "Zephyr Caribbean Growth Fund I",
    "account_number": "0123456789",
    "swift_code": "BAHABSNA",
    "branch": "Nassau, New Providence, The Bahamas",
}

# ─── Phase 5: Investor Fund Participation ────────────────────────────────────
@app.patch("/api/investors/{investor_id}/fund-participation")
async def update_fund_participation(investor_id: str, body: FundParticipationUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    try:
        oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")
    investor = await db.investors.find_one({"_id": oid})
    if not investor:
        raise HTTPException(404, "Investor not found")
    existing_called = investor.get("capital_called", 0) or 0
    update: dict = {
        "share_class": body.share_class,
        "committed_capital": body.committed_capital,
        "deal_associations": body.deal_associations or [],
        "placement_agent_id": body.placement_agent_id if body.placement_agent_id else None,
        "capital_uncalled": max(0.0, body.committed_capital - existing_called),
    }
    await db.investors.update_one({"_id": oid}, {"$set": update})
    await db.audit_logs.insert_one({
        "user_id": current_user.get("_id"),
        "user_email": current_user.get("email", ""),
        "user_role": current_user.get("role", ""),
        "user_name": current_user.get("name", ""),
        "action": "investor_fund_participation_updated",
        "target_id": investor_id, "target_type": "investor",
        "timestamp": datetime.now(timezone.utc),
        "notes": f"Fund participation: Class {body.share_class}, committed ${body.committed_capital:,.0f}",
    })
    return {"message": "Fund participation updated", "share_class": body.share_class, "committed_capital": body.committed_capital}


# ─── Phase 5: Placement Agents ───────────────────────────────────────────────
def _serialize_agent(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc

@app.get("/api/agents")
async def get_agents(current_user: dict = Depends(get_current_user)):
    agents = []
    async for doc in db.placement_agents.find().sort("agent_name", 1):
        doc = _serialize_agent(doc)
        agent_id = doc["id"]
        doc["linked_investors"] = await db.investors.count_documents({"placement_agent_id": agent_id})
        total_fees = 0.0
        async for inv in db.trailer_fee_invoices.find({"agent_id": agent_id, "status": {"$ne": "draft"}}):
            total_fees += inv.get("total_due", 0) or 0
        doc["total_fees_invoiced"] = total_fees
        agents.append(doc)
    return agents

@app.post("/api/agents")
async def create_agent(body: PlacementAgentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    doc = {
        "agent_name": body.agent_name, "company_name": body.company_name,
        "email": body.email, "phone": body.phone,
        "bank_name": body.bank_name, "bank_account_number": body.bank_account_number,
        "swift_code": body.swift_code, "vat_registered": body.vat_registered,
        "vat_number": body.vat_number, "created_by": current_user.get("_id"),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.placement_agents.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc

@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(agent_id)
    except Exception:
        raise HTTPException(400, "Invalid agent ID")
    doc = await db.placement_agents.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Agent not found")
    doc = _serialize_agent(doc)
    linked = []
    async for inv in db.investors.find({"placement_agent_id": agent_id}):
        linked.append({
            "id": str(inv["_id"]), "name": inv.get("legal_name") or inv.get("name", ""),
            "share_class": inv.get("share_class", "C"),
            "committed_capital": inv.get("committed_capital", 0) or 0,
            "kyc_status": inv.get("kyc_status", ""),
        })
    doc["linked_investors"] = linked
    invoices = []
    async for tf in db.trailer_fee_invoices.find({"agent_id": agent_id}).sort("created_at", -1):
        invoices.append({
            "id": str(tf["_id"]), "invoice_number": tf.get("invoice_number", ""),
            "period_year": tf.get("period_year"),
            "total_due": tf.get("total_due", 0), "status": tf.get("status", "draft"),
            "issued_date": tf.get("issued_date").isoformat() if isinstance(tf.get("issued_date"), datetime) else tf.get("issued_date"),
        })
    doc["invoices"] = invoices
    doc["total_fees_invoiced"] = sum(i["total_due"] for i in invoices if i.get("status") != "draft")
    return doc

@app.patch("/api/agents/{agent_id}")
async def update_agent(agent_id: str, body: PlacementAgentUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    try:
        oid = ObjectId(agent_id)
    except Exception:
        raise HTTPException(400, "Invalid agent ID")
    update = {k: v for k, v in body.dict().items() if v is not None}
    if not update:
        raise HTTPException(400, "No fields to update")
    await db.placement_agents.update_one({"_id": oid}, {"$set": update})
    return {"message": "Agent updated"}


# ─── Phase 5: Capital Calls ──────────────────────────────────────────────────
def _serialize_call(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    for k in ("call_date", "due_date", "created_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    li = doc.get("line_items", [])
    received = sum(1 for x in li if x.get("status") == "received")
    doc["pct_received"] = round(received / len(li) * 100, 1) if li else 0.0
    return doc

@app.get("/api/capital-calls")
async def get_capital_calls(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    calls = []
    async for doc in db.capital_calls.find().sort("call_date", -1):
        calls.append(_serialize_call(doc))
    return calls

@app.post("/api/capital-calls")
async def create_capital_call(body: CapitalCallCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    now = datetime.now(timezone.utc)
    try:
        due_dt = datetime.fromisoformat(body.due_date.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
    except Exception:
        due_dt = now + timedelta(days=30)
    line_items = []
    if body.call_type == "fund_level":
        async for inv in db.investors.find({"share_class": {"$in": body.target_classes}, "kyc_status": "approved", "committed_capital": {"$gt": 0}}):
            committed = inv.get("committed_capital", 0) or 0
            line_items.append({"investor_id": str(inv["_id"]), "investor_name": inv.get("legal_name") or inv.get("name", ""), "share_class": inv.get("share_class", "A"), "committed_capital": committed, "call_amount": round(committed * body.call_percentage / 100, 2), "status": "pending"})
    elif body.call_type == "deal_specific":
        if not body.deal_id:
            raise HTTPException(400, "deal_id required for deal_specific")
        async for inv in db.investors.find({"share_class": "C", "kyc_status": "approved", "deal_associations": body.deal_id, "committed_capital": {"$gt": 0}}):
            committed = inv.get("committed_capital", 0) or 0
            line_items.append({"investor_id": str(inv["_id"]), "investor_name": inv.get("legal_name") or inv.get("name", ""), "share_class": "C", "committed_capital": committed, "call_amount": round(committed * body.call_percentage / 100, 2), "status": "pending"})
    total_amount = sum(li["call_amount"] for li in line_items)
    doc = {"call_name": body.call_name, "call_date": now, "due_date": due_dt, "deal_id": body.deal_id, "call_type": body.call_type, "target_classes": body.target_classes, "call_percentage": body.call_percentage, "total_amount": total_amount, "status": "draft", "line_items": line_items, "created_by": current_user.get("_id"), "created_at": now}
    result = await db.capital_calls.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    for k in ("call_date", "due_date", "created_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    doc["pct_received"] = 0.0
    return doc

@app.post("/api/capital-calls/{call_id}/issue")
async def issue_capital_call(call_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    try:
        oid = ObjectId(call_id)
    except Exception:
        raise HTTPException(400, "Invalid capital call ID")
    call = await db.capital_calls.find_one({"_id": oid})
    if not call:
        raise HTTPException(404, "Capital call not found")
    if call.get("status") != "draft":
        raise HTTPException(400, "Capital call is not in draft status")
    for li in call.get("line_items", []):
        inv_id = li.get("investor_id")
        if inv_id:
            try:
                inv_oid = ObjectId(inv_id)
                inv = await db.investors.find_one({"_id": inv_oid})
                if inv:
                    existing = inv.get("capital_called", 0) or 0
                    new_called = existing + (li.get("call_amount", 0) or 0)
                    committed = inv.get("committed_capital", 0) or 0
                    await db.investors.update_one({"_id": inv_oid}, {"$set": {"capital_called": new_called, "capital_uncalled": max(0, committed - new_called)}})
            except Exception:
                pass
    await db.capital_calls.update_one({"_id": oid}, {"$set": {"status": "issued"}})
    await db.audit_logs.insert_one({"user_id": current_user.get("_id"), "user_email": current_user.get("email", ""), "user_role": current_user.get("role", ""), "user_name": current_user.get("name", ""), "action": "capital_call_issued", "target_id": call_id, "target_type": "capital_call", "timestamp": datetime.now(timezone.utc), "notes": f"Capital call issued: {call.get('call_name')} | Total: ${call.get('total_amount', 0):,.0f}"})
    return {"message": "Capital call issued", "call_id": call_id}

@app.get("/api/capital-calls/{call_id}")
async def get_capital_call(call_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    try:
        oid = ObjectId(call_id)
    except Exception:
        raise HTTPException(400, "Invalid capital call ID")
    doc = await db.capital_calls.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Capital call not found")
    doc = _serialize_call(doc)
    # Compute default interest
    now = datetime.now(timezone.utc)
    try:
        due_dt = datetime.fromisoformat(doc["due_date"].replace("Z", "+00:00"))
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
    except Exception:
        due_dt = now
    for li in doc.get("line_items", []):
        if li.get("status") == "defaulted":
            days_overdue = max(0, (now - due_dt).days)
            li["accrued_interest"] = round((li.get("call_amount", 0) or 0) * 0.08 / 365 * days_overdue, 2)
            li["days_overdue"] = days_overdue
        else:
            li["accrued_interest"] = 0
            li["days_overdue"] = 0
    return doc

@app.patch("/api/capital-calls/{call_id}/line-items/{investor_id}")
async def update_line_item(call_id: str, investor_id: str, body: LineItemStatusUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    if body.status not in ("pending", "received", "defaulted"):
        raise HTTPException(400, "Invalid status. Must be: pending, received, or defaulted")
    try:
        oid = ObjectId(call_id)
    except Exception:
        raise HTTPException(400, "Invalid capital call ID")
    call = await db.capital_calls.find_one({"_id": oid})
    if not call:
        raise HTTPException(404, "Capital call not found")
    line_items = call.get("line_items", [])
    updated = False
    for li in line_items:
        if li.get("investor_id") == investor_id:
            li["status"] = body.status
            updated = True
            break
    if not updated:
        raise HTTPException(404, "Investor not found in this capital call")
    await db.capital_calls.update_one({"_id": oid}, {"$set": {"line_items": line_items}})
    await db.audit_logs.insert_one({"user_id": current_user.get("_id"), "user_email": current_user.get("email", ""), "user_role": current_user.get("role", ""), "user_name": current_user.get("name", ""), "action": "capital_call_line_item_updated", "target_id": call_id, "target_type": "capital_call", "timestamp": datetime.now(timezone.utc), "notes": f"Line item for investor {investor_id} → {body.status}"})
    return {"message": f"Line item updated to {body.status}"}


# ─── Phase 5: Capital Call Notice PDF ────────────────────────────────────────
def _build_notice_pdf(call: dict, li: dict, fund_profile: dict, user_name: str, user_role: str) -> BytesIO:
    S = _pdf_styles()
    ts = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    buf = BytesIO()
    doc_obj = SimpleDocTemplate(buf, pagesize=A4, topMargin=33*mm, bottomMargin=22*mm, leftMargin=15*mm, rightMargin=15*mm)
    hf = _partial(_hf_callback, title_line2="CAPITAL CALL NOTICE — CONFIDENTIAL", user_name=user_name, user_role=user_role, ts=ts)
    story = []
    fund_name = fund_profile.get("fund_name", "Zephyr Caribbean Growth Fund I") if fund_profile else "Zephyr Caribbean Growth Fund I"
    license_num = fund_profile.get("license_number", "SCB-2024-PE-0042") if fund_profile else "SCB-2024-PE-0042"
    story.append(Paragraph("CAPITAL CALL NOTICE", ParagraphStyle("notitle", parent=getSampleStyleSheet()['Normal'], fontSize=20, textColor=rl_colors.HexColor('#1B3A6B'), fontName='Helvetica-Bold', spaceAfter=2, alignment=1)))
    story.append(Paragraph(fund_name, ParagraphStyle("nosub", parent=getSampleStyleSheet()['Normal'], fontSize=12, textColor=rl_colors.HexColor('#00A8C6'), fontName='Helvetica', spaceAfter=2, alignment=1)))
    story.append(Paragraph(f"SCB License: {license_num}", ParagraphStyle("nosc", parent=getSampleStyleSheet()['Normal'], fontSize=9, textColor=rl_colors.HexColor('#6B7280'), fontName='Helvetica', spaceAfter=6, alignment=1)))
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#1B3A6B'), spaceAfter=6))
    story.append(Paragraph("Fund Details", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Fund Name', fund_name],
        ['Fund Manager', fund_profile.get("fund_manager", "Zephyr Asset Management Ltd") if fund_profile else "Zephyr Asset Management Ltd"],
        ['SCB License', license_num],
        ['Call Reference', call.get("call_name", "")],
        ['Call Date', call.get("call_date", "")[:10] if call.get("call_date") else "—"],
        ['Due Date', call.get("due_date", "")[:10] if call.get("due_date") else "—"],
    ], colWidths=[55*mm, 115*mm], style=_tbl_style()))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Investor Details", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Legal Name', li.get("investor_name", "")],
        ['Share Class', f"Class {li.get('share_class', '—')}"],
        ['Committed Capital', f"USD {li.get('committed_capital', 0):,.2f}"],
    ], colWidths=[55*mm, 115*mm], style=_tbl_style()))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Capital Call Details", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Call Name', call.get("call_name", "")],
        ['Call Type', call.get("call_type", "").replace("_", " ").title()],
        ['Call Percentage', f"{call.get('call_percentage', 0)}% of Committed Capital"],
        ['Amount Due from Investor', f"USD {li.get('call_amount', 0):,.2f}"],
        ['Payment Due Date', call.get("due_date", "")[:10] if call.get("due_date") else "—"],
    ], colWidths=[70*mm, 100*mm], style=_tbl_style()))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Payment Instructions", S['h2']))
    ref = f"{li.get('investor_name', '')} — {call.get('call_name', '')}"
    story.append(Table([
        ['Field', 'Details'],
        ['Bank Name', _FUND_BANK["bank_name"]],
        ['Account Name', _FUND_BANK["account_name"]],
        ['Account Number', _FUND_BANK["account_number"]],
        ['SWIFT / BIC', _FUND_BANK["swift_code"]],
        ['Branch', _FUND_BANK["branch"]],
        ['Payment Reference', ref],
        ['Amount', f"USD {li.get('call_amount', 0):,.2f}"],
    ], colWidths=[55*mm, 115*mm], style=_tbl_style()))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Default Notice", S['h2']))
    story.append(Paragraph("Failure to fund by the due date will result in interest accruing at 8% per annum on the outstanding amount. After 30 days of non-payment, LP forfeiture provisions under the Subscription Agreement apply. For questions, contact compliance@zephyrwealth.ai.", S['body']))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=3))
    story.append(Paragraph(f"Prepared by: {user_name} ({user_role.title()})  |  Date: {ts[:11]}", S['small']))
    story.append(Paragraph("Confidential — Zephyr Asset Management Ltd | SCB Licensed Fund", S['small']))
    doc_obj.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    return buf

@app.get("/api/capital-calls/{call_id}/notice-pdf/{investor_id}")
async def get_notice_pdf(call_id: str, investor_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    try:
        oid = ObjectId(call_id)
    except Exception:
        raise HTTPException(400, "Invalid capital call ID")
    call = await db.capital_calls.find_one({"_id": oid})
    if not call:
        raise HTTPException(404, "Capital call not found")
    call_d = _serialize_call(call)
    li = next((x for x in call_d.get("line_items", []) if x.get("investor_id") == investor_id), None)
    if not li:
        raise HTTPException(404, "Investor not in this capital call")
    fund_profile = await db.fund_profile.find_one({})
    u_name = current_user.get("name", current_user.get("email", "Unknown"))
    u_role = current_user["role"]
    buf = _build_notice_pdf(call_d, li, fund_profile, u_name, u_role)
    safe_name = li.get("investor_name", investor_id).replace(" ", "_")
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="CapitalCallNotice_{safe_name}.pdf"'})

@app.get("/api/capital-calls/{call_id}/notices")
async def get_all_notices(call_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    try:
        oid = ObjectId(call_id)
    except Exception:
        raise HTTPException(400, "Invalid capital call ID")
    call = await db.capital_calls.find_one({"_id": oid})
    if not call:
        raise HTTPException(404, "Capital call not found")
    call_d = _serialize_call(call)
    line_items = call_d.get("line_items", [])
    fund_profile = await db.fund_profile.find_one({})
    u_name = current_user.get("name", current_user.get("email", "Unknown"))
    u_role = current_user["role"]
    if len(line_items) == 1:
        buf = _build_notice_pdf(call_d, line_items[0], fund_profile, u_name, u_role)
        safe = line_items[0].get("investor_name", "Investor").replace(" ", "_")
        return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="CapitalCallNotice_{safe}.pdf"'})
    zip_buf = BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for li in line_items:
            pdf_buf = _build_notice_pdf(call_d, li, fund_profile, u_name, u_role)
            safe = li.get("investor_name", li.get("investor_id", "Investor")).replace(" ", "_")
            zf.writestr(f"CapitalCallNotice_{safe}.pdf", pdf_buf.read())
    zip_buf.seek(0)
    safe_call = call_d.get("call_name", call_id).replace(" ", "_").replace("/", "-")
    return StreamingResponse(zip_buf, media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="CallNotices_{safe_call}.zip"'})

@app.get("/api/capital-calls/{call_id}/export-csv")
async def export_capital_call_csv(call_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    try:
        oid = ObjectId(call_id)
    except Exception:
        raise HTTPException(400, "Invalid capital call ID")
    call = await db.capital_calls.find_one({"_id": oid})
    if not call:
        raise HTTPException(404, "Capital call not found")
    rows = ["Investor Name,Share Class,Committed Capital,Call Amount,Status"]
    for li in call.get("line_items", []):
        rows.append(f"{li.get('investor_name','')},{li.get('share_class','')},{li.get('committed_capital',0)},{li.get('call_amount',0)},{li.get('status','')}")
    csv_str = "\n".join(rows)
    buf = BytesIO(csv_str.encode("utf-8"))
    safe = call.get("call_name", call_id).replace(" ", "_")
    return StreamingResponse(buf, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="CapitalCall_{safe}.csv"'})


# ─── Phase 5: Trailer Fee Invoices ───────────────────────────────────────────
def _serialize_tf(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    for k in ("period_start", "period_end", "issued_date", "due_date", "created_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return doc

@app.post("/api/trailer-fees/generate")
async def generate_trailer_fees(body: TrailerFeeGenerateRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    if body.agent_ids:
        try:
            agent_oids = [ObjectId(a) for a in body.agent_ids]
        except Exception:
            raise HTTPException(400, "Invalid agent ID in list")
        agents_cur = db.placement_agents.find({"_id": {"$in": agent_oids}})
    else:
        agents_cur = db.placement_agents.find()
    period_start = datetime(body.year, 1, 1, tzinfo=timezone.utc)
    period_end = datetime(body.year, 12, 31, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    invoices = []
    async for agent in agents_cur:
        agent_id = str(agent["_id"])
        line_items = []
        subtotal = 0.0
        async for inv in db.investors.find({"placement_agent_id": agent_id, "share_class": "C"}):
            committed = inv.get("committed_capital", 0) or 0
            if committed <= 0:
                continue
            fee_amount = round(committed * 0.0075, 2)
            deal_names = []
            for did in (inv.get("deal_associations") or []):
                try:
                    deal = await db.deals.find_one({"_id": ObjectId(did)})
                    if deal:
                        deal_names.append(deal.get("company_name") or deal.get("name", ""))
                except Exception:
                    pass
            line_items.append({"investor_id": str(inv["_id"]), "investor_name": inv.get("legal_name") or inv.get("name", ""), "deal_name": ", ".join(deal_names) if deal_names else "General Fund", "committed_capital": committed, "fee_rate": 0.0075, "fee_amount": fee_amount})
            subtotal += fee_amount
        if not line_items:
            continue
        vat_applicable = bool(agent.get("vat_registered", False))
        vat_amount = round(subtotal * 0.10, 2) if vat_applicable else 0.0
        total_due = round(subtotal + vat_amount, 2)
        existing = await db.trailer_fee_invoices.count_documents({"agent_id": agent_id, "period_year": body.year})
        seq = existing + 1
        inv_doc = {"agent_id": agent_id, "agent_name": agent.get("agent_name", ""), "invoice_number": f"TF-{body.year}-{str(seq).zfill(3)}", "period_year": body.year, "period_start": period_start, "period_end": period_end, "line_items": line_items, "subtotal": subtotal, "vat_applicable": vat_applicable, "vat_amount": vat_amount, "total_due": total_due, "status": "draft", "issued_date": None, "due_date": now + timedelta(days=30), "created_by": current_user.get("_id"), "created_at": now}
        result = await db.trailer_fee_invoices.insert_one(inv_doc)
        inv_doc = _serialize_tf(inv_doc)
        inv_doc["id"] = str(result.inserted_id)
        invoices.append(inv_doc)
    return {"invoices": invoices, "count": len(invoices)}

@app.get("/api/trailer-fees")
async def get_trailer_fees(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    result = []
    async for doc in db.trailer_fee_invoices.find().sort("created_at", -1):
        result.append(_serialize_tf(doc))
    return result

@app.get("/api/trailer-fees/{tf_id}")
async def get_trailer_fee(tf_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    try:
        oid = ObjectId(tf_id)
    except Exception:
        raise HTTPException(400, "Invalid invoice ID")
    doc = await db.trailer_fee_invoices.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Trailer fee invoice not found")
    return _serialize_tf(doc)

@app.post("/api/trailer-fees/{tf_id}/issue")
async def issue_trailer_fee(tf_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    try:
        oid = ObjectId(tf_id)
    except Exception:
        raise HTTPException(400, "Invalid invoice ID")
    doc = await db.trailer_fee_invoices.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Invoice not found")
    if doc.get("status") != "draft":
        raise HTTPException(400, "Invoice is not in draft status")
    now = datetime.now(timezone.utc)
    await db.trailer_fee_invoices.update_one({"_id": oid}, {"$set": {"status": "issued", "issued_date": now, "due_date": now + timedelta(days=30)}})
    return {"message": "Invoice issued"}

@app.post("/api/trailer-fees/{tf_id}/mark-paid")
async def mark_trailer_fee_paid(tf_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(403, "Compliance role required")
    try:
        oid = ObjectId(tf_id)
    except Exception:
        raise HTTPException(400, "Invalid invoice ID")
    doc = await db.trailer_fee_invoices.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Invoice not found")
    await db.trailer_fee_invoices.update_one({"_id": oid}, {"$set": {"status": "paid"}})
    return {"message": "Invoice marked as paid"}

@app.get("/api/trailer-fees/{tf_id}/pdf")
async def get_trailer_fee_pdf(tf_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    try:
        oid = ObjectId(tf_id)
    except Exception:
        raise HTTPException(400, "Invalid invoice ID")
    doc = await db.trailer_fee_invoices.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Invoice not found")
    S = _pdf_styles()
    ts = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    u_name = current_user.get("name", current_user.get("email", "Unknown"))
    u_role = current_user["role"]
    buf = BytesIO()
    pdf_doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=33*mm, bottomMargin=22*mm, leftMargin=15*mm, rightMargin=15*mm)
    hf = _partial(_hf_callback, title_line2="TRAILER FEE INVOICE — CONFIDENTIAL", user_name=u_name, user_role=u_role, ts=ts)
    story = []
    inv_num = doc.get("invoice_number", f"TF-{doc.get('period_year', '')}-001")
    agent_name = doc.get("agent_name", "")
    story.append(Paragraph("TRAILER FEE INVOICE", ParagraphStyle("tfi_title", parent=getSampleStyleSheet()['Normal'], fontSize=20, textColor=rl_colors.HexColor('#1B3A6B'), fontName='Helvetica-Bold', spaceAfter=2, alignment=1)))
    story.append(Paragraph("Zephyr Asset Management Ltd | ZephyrWealth.ai", ParagraphStyle("tfi_sub", parent=getSampleStyleSheet()['Normal'], fontSize=10, textColor=rl_colors.HexColor('#6B7280'), fontName='Helvetica', spaceAfter=6, alignment=1)))
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#1B3A6B'), spaceAfter=6))
    period_y = doc.get("period_year", "")
    issued_dt = doc.get("issued_date")
    issued_str = issued_dt.strftime("%d %b %Y") if isinstance(issued_dt, datetime) else (issued_dt[:10] if issued_dt else ts[:11])
    due_dt = doc.get("due_date")
    due_str = due_dt.strftime("%d %b %Y") if isinstance(due_dt, datetime) else (due_dt[:10] if due_dt else "Net 30")
    story.append(Paragraph("Invoice Details", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Invoice Number', inv_num],
        ['Period', str(period_y)],
        ['Date Issued', issued_str],
        ['Due Date', due_str],
        ['Status', doc.get("status", "draft").upper()],
    ], colWidths=[55*mm, 115*mm], style=_tbl_style()))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Bill To", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Agent Name', agent_name],
        ['Company', doc.get("company_name", "—") if doc.get("company_name") else "—"],
        ['Email', "—"],
    ], colWidths=[55*mm, 115*mm], style=_tbl_style()))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Fee Schedule", S['h2']))
    li_data = [['Investor Name', 'Deal Name', 'Committed Capital', 'Rate', 'Fee Amount']]
    for li in doc.get("line_items", []):
        li_data.append([li.get("investor_name", ""), li.get("deal_name", "General"), f"USD {li.get('committed_capital', 0):,.2f}", f"{li.get('fee_rate', 0.0075)*100:.2f}%", f"USD {li.get('fee_amount', 0):,.2f}"])
    fee_tbl = Table(li_data, colWidths=[45*mm, 40*mm, 35*mm, 15*mm, 35*mm])
    fee_tbl.setStyle(_tbl_style())
    story.append(fee_tbl)
    story.append(Spacer(1, 5*mm))
    summary_data = [['Item', 'Amount'], ['Subtotal', f"USD {doc.get('subtotal', 0):,.2f}"]]
    if doc.get("vat_applicable"):
        summary_data.append(['VAT (10%)', f"USD {doc.get('vat_amount', 0):,.2f}"])
    summary_data.append(['TOTAL DUE', f"USD {doc.get('total_due', 0):,.2f}"])
    s_tbl = Table(summary_data, colWidths=[100*mm, 70*mm])
    s_tbl.setStyle(_tbl_style())
    story.append(s_tbl)
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Payment Instructions", S['h2']))
    story.append(Table([
        ['Field', 'Details'],
        ['Bank Name', _FUND_BANK["bank_name"]],
        ['Account Name', _FUND_BANK["account_name"]],
        ['Account Number', _FUND_BANK["account_number"]],
        ['SWIFT / BIC', _FUND_BANK["swift_code"]],
        ['Reference', inv_num],
    ], colWidths=[55*mm, 115*mm], style=_tbl_style()))
    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=3))
    story.append(Paragraph(f"Trailer fee per Placement Agent Agreement | Zephyr Asset Management Ltd | Period: {period_y}", S['small']))
    story.append(Paragraph(f"Generated by: {u_name} ({u_role.title()}) | {ts}", S['small']))
    pdf_doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="TrailerFeeInvoice_{inv_num}.pdf"'})


# ─── Phase 5 Demo Seed ────────────────────────────────────────────────────────
async def seed_demo_phase5():
    """Phase 5 idempotent demo seed. Guard: placement_agents count."""
    if await db.placement_agents.count_documents({}) > 0:
        return
    now = datetime.now(timezone.utc)
    def dag(n): return now - timedelta(days=n)

    # ── Placement Agents ──────────────────────────────────────────────────────
    ag1 = {"agent_name": "Island Capital Advisors Ltd", "company_name": "Island Capital Advisors Ltd", "email": "fees@islandcapital.bs", "phone": "+1 242-555-0201", "bank_name": "RBC Royal Bank (Bahamas)", "bank_account_number": "1234567890", "swift_code": "ROYCBSNA", "vat_registered": True, "vat_number": "VAT-BS-20240042", "created_at": dag(90)}
    ag2 = {"agent_name": "Caribbean Wealth Partners", "company_name": "Caribbean Wealth Partners LLC", "email": "admin@caribwealthpartners.com", "phone": "+1 345-555-0188", "bank_name": "Cayman National Bank", "bank_account_number": "9876543210", "swift_code": "CANACAYK", "vat_registered": False, "vat_number": None, "created_at": dag(80)}
    ag1_res = await db.placement_agents.insert_one(ag1)
    ag2_res = await db.placement_agents.insert_one(ag2)
    ag1_id = str(ag1_res.inserted_id)
    ag2_id = str(ag2_res.inserted_id)

    # ── Update Phase 4 investors with share class + committed capital ──────────
    # Lookup by legal_name
    inv_updates = [
        ("Cayman Tech Ventures SPV Ltd", {"share_class": "A", "committed_capital": 750000.0, "capital_called": 0.0, "capital_uncalled": 750000.0}),
        ("Nassau Capital Partners IBC", {"share_class": "A", "committed_capital": 500000.0, "capital_called": 0.0, "capital_uncalled": 500000.0}),
        ("Marcus Harrington", {"share_class": "B", "committed_capital": 150000.0, "capital_called": 0.0, "capital_uncalled": 150000.0}),
        ("Yolanda Santos", {"share_class": "B", "committed_capital": 100000.0, "capital_called": 0.0, "capital_uncalled": 100000.0}),
        ("Meridian Global Holdings Ltd", {"share_class": "C", "committed_capital": 200000.0, "capital_called": 0.0, "capital_uncalled": 200000.0, "placement_agent_id": ag1_id, "deal_associations": []}),
        ("Olympus Private Capital Ltd", {"share_class": "C", "committed_capital": 0.0, "capital_called": 0.0, "capital_uncalled": 0.0, "placement_agent_id": ag2_id, "deal_associations": []}),
    ]

    # Also use secondary names for Phase 4 demo investors that might exist
    alt_names = {
        "Cayman Tech Ventures SPV Ltd": ["Cayman Tech Ventures SPV Ltd"],
        "Nassau Capital Partners IBC": ["Nassau Capital Partners IBC", "Nassau Capital Partners"],
        "Marcus Harrington": ["Marcus Harrington"],
        "Yolanda Santos": ["Yolanda Santos"],
        "Meridian Global Holdings Ltd": ["Meridian Global Holdings Ltd", "Meridian Global Holdings"],
        "Olympus Private Capital Ltd": ["Olympus Private Capital Ltd", "Olympus Private Capital"],
    }

    inv_ids: dict = {}
    for primary, fields in inv_updates:
        names_to_try = alt_names.get(primary, [primary])
        found = None
        for name in names_to_try:
            found = await db.investors.find_one({"$or": [{"legal_name": name}, {"name": name}]})
            if found:
                break
        if found:
            await db.investors.update_one({"_id": found["_id"]}, {"$set": fields})
            inv_ids[primary] = str(found["_id"])

    # ── Find CaribPay deal for Class C deal_associations ─────────────────────
    caribpay_deal = await db.deals.find_one({"$or": [{"company_name": {"$regex": "CaribPay", "$options": "i"}}, {"name": {"$regex": "CaribPay", "$options": "i"}}]})
    if caribpay_deal and "Meridian Global Holdings Ltd" in inv_ids:
        deal_id = str(caribpay_deal["_id"])
        meridian_id = ObjectId(inv_ids["Meridian Global Holdings Ltd"])
        await db.investors.update_one({"_id": meridian_id}, {"$set": {"deal_associations": [deal_id]}})

    # ── Capital Call 1: Q1 2026 Initial Drawdown ──────────────────────────────
    # Class A + B, 20%, all received, due 60 days ago
    cc1_due = dag(60)
    cc1_li = []
    for name, cls in [("Cayman Tech Ventures SPV Ltd", "A"), ("Nassau Capital Partners IBC", "A"), ("Marcus Harrington", "B"), ("Yolanda Santos", "B")]:
        if name in inv_ids:
            inv = await db.investors.find_one({"_id": ObjectId(inv_ids[name])})
            committed = inv.get("committed_capital", 0) or 0
            cc1_li.append({"investor_id": inv_ids[name], "investor_name": name, "share_class": cls, "committed_capital": committed, "call_amount": round(committed * 0.20, 2), "status": "received"})
    cc1_total = sum(li["call_amount"] for li in cc1_li)
    cc1_doc = {"call_name": "Q1 2026 — Initial Drawdown", "call_date": dag(75), "due_date": cc1_due, "deal_id": None, "call_type": "fund_level", "target_classes": ["A", "B"], "call_percentage": 20.0, "total_amount": cc1_total, "status": "issued", "line_items": cc1_li, "created_by": "system", "created_at": dag(80)}
    cc1_res = await db.capital_calls.insert_one(cc1_doc)

    # Update capital_called on investors for Q1 (all received)
    for li in cc1_li:
        inv_oid = ObjectId(li["investor_id"])
        inv = await db.investors.find_one({"_id": inv_oid})
        if inv:
            new_called = (inv.get("capital_called", 0) or 0) + li["call_amount"]
            committed = inv.get("committed_capital", 0) or 0
            await db.investors.update_one({"_id": inv_oid}, {"$set": {"capital_called": new_called, "capital_uncalled": max(0, committed - new_called)}})

    # ── Capital Call 2: Q2 2026 Harbour House ────────────────────────────────
    # Class A + B, 25%, due 10 days from now, Yolanda pending, rest received
    cc2_due = now + timedelta(days=10)
    cc2_li = []
    for name, cls in [("Cayman Tech Ventures SPV Ltd", "A"), ("Nassau Capital Partners IBC", "A"), ("Marcus Harrington", "B"), ("Yolanda Santos", "B")]:
        if name in inv_ids:
            inv = await db.investors.find_one({"_id": ObjectId(inv_ids[name])})
            committed = inv.get("committed_capital", 0) or 0
            status = "pending" if name == "Yolanda Santos" else "received"
            cc2_li.append({"investor_id": inv_ids[name], "investor_name": name, "share_class": cls, "committed_capital": committed, "call_amount": round(committed * 0.25, 2), "status": status})
    cc2_total = sum(li["call_amount"] for li in cc2_li)
    cc2_doc = {"call_name": "Q2 2026 — Harbour House Acquisition", "call_date": dag(5), "due_date": cc2_due, "deal_id": None, "call_type": "fund_level", "target_classes": ["A", "B"], "call_percentage": 25.0, "total_amount": cc2_total, "status": "issued", "line_items": cc2_li, "created_by": "system", "created_at": dag(7)}
    await db.capital_calls.insert_one(cc2_doc)

    # Update capital_called on investors for Q2 (update all, pending still gets capital_called updated on issue)
    for li in cc2_li:
        inv_oid = ObjectId(li["investor_id"])
        inv = await db.investors.find_one({"_id": inv_oid})
        if inv:
            new_called = (inv.get("capital_called", 0) or 0) + li["call_amount"]
            committed = inv.get("committed_capital", 0) or 0
            await db.investors.update_one({"_id": inv_oid}, {"$set": {"capital_called": new_called, "capital_uncalled": max(0, committed - new_called)}})

    # ── Trailer Fee Invoice: Island Capital, 2025, Issued ────────────────────
    meridian_inv = await db.investors.find_one({"_id": ObjectId(inv_ids["Meridian Global Holdings Ltd"])}) if "Meridian Global Holdings Ltd" in inv_ids else None
    if meridian_inv:
        committed_m = meridian_inv.get("committed_capital", 200000.0) or 200000.0
        fee_amount = round(committed_m * 0.0075, 2)
        tf_doc = {
            "agent_id": ag1_id, "agent_name": "Island Capital Advisors Ltd",
            "invoice_number": "TF-2025-001", "period_year": 2025,
            "period_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "period_end": datetime(2025, 12, 31, tzinfo=timezone.utc),
            "line_items": [{"investor_id": inv_ids["Meridian Global Holdings Ltd"], "investor_name": "Meridian Global Holdings Ltd", "deal_name": "General Fund", "committed_capital": committed_m, "fee_rate": 0.0075, "fee_amount": fee_amount}],
            "subtotal": fee_amount, "vat_applicable": True,
            "vat_amount": round(fee_amount * 0.10, 2),
            "total_due": round(fee_amount * 1.10, 2),
            "status": "issued", "issued_date": dag(30),
            "due_date": dag(30) + timedelta(days=30),
            "created_by": "system", "created_at": dag(35),
        }
        await db.trailer_fee_invoices.insert_one(tf_doc)
