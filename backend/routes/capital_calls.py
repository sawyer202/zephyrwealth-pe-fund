from datetime import datetime, timezone, timedelta
from io import BytesIO
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId

from database import db
from utils import get_current_user
from models import CapitalCallCreate, LineItemStatusUpdate
from pdf_utils import _build_notice_pdf

router = APIRouter(tags=["capital-calls"])


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


@router.get("/api/capital-calls")
async def get_capital_calls(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    calls = []
    async for doc in db.capital_calls.find().sort("call_date", -1):
        calls.append(_serialize_call(doc))
    return calls


@router.post("/api/capital-calls")
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


@router.post("/api/capital-calls/{call_id}/issue")
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


@router.get("/api/capital-calls/{call_id}")
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


@router.patch("/api/capital-calls/{call_id}/line-items/{investor_id}")
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


@router.get("/api/capital-calls/{call_id}/notice-pdf/{investor_id}")
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


@router.get("/api/capital-calls/{call_id}/notices")
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


@router.get("/api/capital-calls/{call_id}/export-csv")
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
