"""
Phase 6 — Investor Portal Data Endpoints
All endpoints require valid investor_token cookie via get_current_investor.
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from bson import ObjectId

from database import db
from routes.portal_auth import get_current_investor
from pdf_utils import _build_notice_pdf
from routes.capital_calls import _serialize_call

router = APIRouter(tags=["portal"])

# Payment instruction fallbacks (matches _FUND_BANK in pdf_utils.py)
_FALLBACK_BANK = {
    "bank_name": "Bank of The Bahamas",
    "bank_account_number": "4521-9900-0087",
    "swift_code": "BAHABSNA",
}


def _fmt(d):
    if isinstance(d, datetime):
        return d.isoformat()
    return d


def _parse_dt(d):
    if isinstance(d, datetime):
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
    if isinstance(d, str):
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
            return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except Exception:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


# ─── Dashboard ────────────────────────────────────────────────────────────────
@router.get("/api/portal/dashboard")
async def portal_dashboard(current_investor: dict = Depends(get_current_investor)):
    investor_id = current_investor["investor_id"]
    try:
        inv_oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")

    investor = await db.investors.find_one({"_id": inv_oid})
    if not investor:
        raise HTTPException(404, "Investor record not found")

    committed = investor.get("committed_capital", 0) or 0
    called = investor.get("capital_called", 0) or 0
    uncalled = max(0.0, committed - called)

    now = datetime.now(timezone.utc)
    pending_call = None
    activity = []

    async for cc in db.capital_calls.find():
        for li in cc.get("line_items", []):
            if li.get("investor_id") != investor_id:
                continue
            due_dt = _parse_dt(cc.get("due_date"))
            days_remaining = (due_dt - now).days if due_dt != datetime.min.replace(tzinfo=timezone.utc) else None

            if li.get("status") == "pending" and pending_call is None:
                pending_call = {
                    "call_id": str(cc["_id"]),
                    "call_name": cc.get("call_name", ""),
                    "amount_due": li.get("call_amount", 0),
                    "due_date": _fmt(cc.get("due_date")),
                    "days_remaining": days_remaining,
                }

            call_date = cc.get("call_date") or cc.get("created_at")
            activity.append({
                "type": "capital_call",
                "event": f"Capital Call: {cc.get('call_name', '')}",
                "sub": f"${li.get('call_amount', 0):,.0f} — {li.get('status', '').title()}",
                "date": _fmt(call_date),
                "amount": li.get("call_amount", 0),
                "status": li.get("status", ""),
            })

    async for doc in db.documents.find({"entity_id": investor_id}).sort("uploaded_at", -1).limit(5):
        activity.append({
            "type": "document",
            "event": f"Document: {doc.get('file_name', '')}",
            "sub": doc.get("document_type", "").replace("_", " ").title(),
            "date": _fmt(doc.get("uploaded_at")),
            "amount": None,
            "status": "uploaded",
        })

    activity.sort(key=lambda x: _parse_dt(x.get("date")), reverse=True)
    activity = activity[:5]

    return {
        "investor_name": investor.get("legal_name") or investor.get("name", ""),
        "kpi": {
            "committed_capital": committed,
            "capital_called": called,
            "capital_uncalled": uncalled,
            "total_distributions": 0.0,
        },
        "next_capital_call": pending_call,
        "recent_activity": activity,
    }


# ─── Investment Detail ────────────────────────────────────────────────────────
@router.get("/api/portal/investment")
async def portal_investment(current_investor: dict = Depends(get_current_investor)):
    investor_id = current_investor["investor_id"]
    try:
        inv_oid = ObjectId(investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")

    investor = await db.investors.find_one({"_id": inv_oid})
    if not investor:
        raise HTTPException(404, "Investor record not found")

    committed = investor.get("committed_capital", 0) or 0
    called = investor.get("capital_called", 0) or 0
    uncalled = max(0.0, committed - called)
    call_rate = round(called / committed * 100, 1) if committed > 0 else 0.0

    share_class = investor.get("share_class", "A")
    sc_desc = {
        "A": "Class A — Institutional LP. Priority in the distribution waterfall. Pro-rata capital calls based on committed capital. 1.5% management fee p.a. Carried interest above an 8% hurdle rate.",
        "B": "Class B — HNW Individual. Standard distribution waterfall. Pro-rata capital calls. 2.0% management fee p.a. 20% carried interest above the 8% hurdle rate.",
        "C": "Class C — Placement Agent Co-Invest. Introduced via a licensed placement agent. Deal-specific capital calls and co-investment rights. Fee arrangements governed by the relevant placement agreement.",
    }

    capital_call_history = []
    async for cc in db.capital_calls.find().sort("call_date", -1):
        for li in cc.get("line_items", []):
            if li.get("investor_id") == investor_id:
                capital_call_history.append({
                    "call_id": str(cc["_id"]),
                    "call_name": cc.get("call_name", ""),
                    "issue_date": _fmt(cc.get("call_date") or cc.get("created_at")),
                    "due_date": _fmt(cc.get("due_date")),
                    "call_amount": li.get("call_amount", 0),
                    "status": li.get("status", "pending"),
                })

    return {
        "profile": {
            "legal_name": investor.get("legal_name") or investor.get("name", ""),
            "entity_type": investor.get("entity_type", ""),
            "share_class": share_class,
            "nationality": investor.get("nationality", ""),
            "kyc_status": investor.get("kyc_status", ""),
            "risk_rating": investor.get("risk_rating", ""),
        },
        "fund_participation": {
            "committed_capital": committed,
            "capital_called": called,
            "capital_uncalled": uncalled,
            "call_rate": call_rate,
            "share_class_description": sc_desc.get(share_class, sc_desc["A"]),
        },
        "distribution_history": [],
        "capital_call_history": capital_call_history,
    }


# ─── Capital Calls ────────────────────────────────────────────────────────────
@router.get("/api/portal/capital-calls")
async def portal_capital_calls(current_investor: dict = Depends(get_current_investor)):
    investor_id = current_investor["investor_id"]
    now = datetime.now(timezone.utc)

    fund_profile = await db.fund_profile.find_one({})
    fp = fund_profile or {}

    investor = await db.investors.find_one({"_id": ObjectId(investor_id)})
    inv_name = (investor.get("legal_name") or investor.get("name", "")) if investor else ""

    calls = []
    async for cc in db.capital_calls.find().sort("call_date", -1):
        for li in cc.get("line_items", []):
            if li.get("investor_id") != investor_id:
                continue
            due_dt = _parse_dt(cc.get("due_date"))
            days_remaining = (due_dt - now).days if due_dt != datetime.min.replace(tzinfo=timezone.utc) else None
            call_name = cc.get("call_name", "")
            calls.append({
                "call_id": str(cc["_id"]),
                "call_name": call_name,
                "issue_date": _fmt(cc.get("call_date") or cc.get("created_at")),
                "due_date": _fmt(cc.get("due_date")),
                "amount_due": li.get("call_amount", 0),
                "status": li.get("status", "pending"),
                "days_remaining": days_remaining,
                "call_percentage": cc.get("call_percentage", 0),
                "share_class": li.get("share_class", ""),
                "payment_instructions": {
                    "fund_name": fp.get("fund_name", "Zephyr Caribbean Growth Fund I"),
                    "bank_name": fp.get("bank_name", _FALLBACK_BANK["bank_name"]),
                    "account_number": fp.get("bank_account_number", _FALLBACK_BANK["bank_account_number"]),
                    "swift": fp.get("swift_code", _FALLBACK_BANK["swift_code"]),
                    "reference": f"{inv_name} — {call_name}",
                },
            })

    return calls


@router.get("/api/portal/capital-calls/{call_id}/notice-pdf")
async def portal_call_notice_pdf(
    call_id: str,
    current_investor: dict = Depends(get_current_investor),
):
    investor_id = current_investor["investor_id"]
    try:
        oid = ObjectId(call_id)
    except Exception:
        raise HTTPException(400, "Invalid call ID")

    cc = await db.capital_calls.find_one({"_id": oid})
    if not cc:
        raise HTTPException(404, "Capital call not found")

    call_d = _serialize_call(cc)
    li = next((x for x in call_d.get("line_items", []) if x.get("investor_id") == investor_id), None)
    if not li:
        raise HTTPException(403, "You are not a participant in this capital call")

    fund_profile = await db.fund_profile.find_one({})
    buf = _build_notice_pdf(call_d, li, fund_profile, current_investor.get("name", "Investor"), "Investor Portal")
    safe_name = li.get("investor_name", investor_id).replace(" ", "_")
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="CapitalCallNotice_{safe_name}.pdf"'},
    )


# ─── Documents ────────────────────────────────────────────────────────────────
@router.get("/api/portal/documents")
async def portal_documents(current_investor: dict = Depends(get_current_investor)):
    investor_id = current_investor["investor_id"]
    docs = []
    async for doc in db.documents.find({"entity_id": investor_id}).sort("uploaded_at", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("uploaded_at"), datetime):
            doc["uploaded_at"] = doc["uploaded_at"].isoformat()
        docs.append(doc)
    return docs


@router.get("/api/portal/documents/{doc_id}/download")
async def portal_document_download(
    doc_id: str,
    current_investor: dict = Depends(get_current_investor),
):
    investor_id = current_investor["investor_id"]
    try:
        oid = ObjectId(doc_id)
    except Exception:
        raise HTTPException(400, "Invalid document ID")

    doc = await db.documents.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Document not found")

    # SECURITY: verify the document belongs to this investor
    if doc.get("entity_id") != investor_id:
        raise HTTPException(403, "Access denied: document does not belong to your account")

    file_path = Path(doc["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "File not found on server")

    return FileResponse(
        path=str(file_path),
        filename=doc["file_name"],
        media_type="application/octet-stream",
    )


# ─── Profile ──────────────────────────────────────────────────────────────────
@router.get("/api/portal/profile")
async def portal_profile(current_investor: dict = Depends(get_current_investor)):
    investor_id = current_investor["investor_id"]
    investor = await db.investors.find_one({"_id": ObjectId(investor_id)})
    if not investor:
        raise HTTPException(404, "Investor record not found")
    return {
        "email": current_investor["email"],
        "name": current_investor["name"],
        "legal_name": investor.get("legal_name") or investor.get("name", ""),
        "entity_type": investor.get("entity_type", ""),
        "share_class": investor.get("share_class", ""),
        "nationality": investor.get("nationality", ""),
        "kyc_status": investor.get("kyc_status", ""),
    }
