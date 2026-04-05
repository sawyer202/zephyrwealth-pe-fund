import os
import jwt
import bcrypt
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import HTTPException, Request
from bson import ObjectId

from database import db

# ─── JWT Constants ────────────────────────────────────────────────────────────
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

# ─── Deal Stage Maps ──────────────────────────────────────────────────────────
OLD_DEAL_STAGE_MAP = {
    "term_sheet": "ic_review",
    "due_diligence": "due_diligence",
    "prospecting": "leads",
    "closed": "closing",
}
STAGE_LABELS = {
    "leads": "Leads",
    "due_diligence": "Due Diligence",
    "ic_review": "IC Review",
    "closing": "Closing",
}

# ─── AI Scorecard Prompt ──────────────────────────────────────────────────────
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


# ─── Password Helpers ─────────────────────────────────────────────────────────
def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ─── JWT Helpers ──────────────────────────────────────────────────────────────
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


# ─── Agreement Generators ─────────────────────────────────────────────────────
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
