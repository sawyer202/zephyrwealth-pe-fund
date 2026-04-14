"""
Distributions — CRUD routes
Phase 6: Includes email notification when a line item is marked as paid.
"""
import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from pydantic import BaseModel
from typing import List, Optional

from database import db
from utils import get_current_user
from email_service import notify_distribution_paid

router = APIRouter(tags=["distributions"])


# ─── Models ────────────────────────────────────────────────────────────────────
class DistributionLineItemModel(BaseModel):
    investor_id: str
    investor_name: str
    share_class: Optional[str] = "A"
    gross_amount: float
    net_amount: float
    status: str = "scheduled"  # scheduled | paid


class DistributionCreate(BaseModel):
    distribution_name: str
    deal_id: Optional[str] = None
    deal_name: Optional[str] = None
    type: str = "income"  # income | capital_return
    gross_amount: float
    payment_date: Optional[str] = None
    line_items: List[DistributionLineItemModel] = []


class LineItemPatch(BaseModel):
    status: str  # "scheduled" | "paid"


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


# ─── CRUD ──────────────────────────────────────────────────────────────────────
@router.get("/api/distributions")
async def list_distributions(current_user: dict = Depends(get_current_user)):
    docs = []
    async for d in db.distributions.find().sort("created_at", -1):
        docs.append(_serialize(d))
    return docs


@router.post("/api/distributions", status_code=201)
async def create_distribution(payload: DistributionCreate, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ("compliance", "manager"):
        raise HTTPException(403, "Insufficient permissions")
    now = datetime.now(timezone.utc)
    doc = {
        **payload.dict(),
        "line_items": [li.dict() for li in payload.line_items],
        "created_by": current_user.get("email", ""),
        "created_at": now,
    }
    result = await db.distributions.insert_one(doc)
    dist_id = str(result.inserted_id)
    await db.audit_logs.insert_one({
        "user_email": current_user.get("email", ""),
        "user_role": current_user.get("role", ""),
        "user_name": current_user.get("name", ""),
        "action": "distribution_issued",
        "target_id": dist_id,
        "target_type": "distribution",
        "timestamp": now,
        "notes": f"Distribution created: {payload.distribution_name} | ${payload.gross_amount:,.0f}",
    })
    return {"id": dist_id, "message": "Distribution created"}


@router.get("/api/distributions/{dist_id}")
async def get_distribution(dist_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(dist_id)
    except Exception:
        raise HTTPException(400, "Invalid distribution ID")
    doc = await db.distributions.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Distribution not found")
    return _serialize(doc)


@router.patch("/api/distributions/{dist_id}/line-items/{investor_id}")
async def update_line_item_status(
    dist_id: str,
    investor_id: str,
    payload: LineItemPatch,
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") not in ("compliance", "manager"):
        raise HTTPException(403, "Insufficient permissions")
    if payload.status not in ("scheduled", "paid"):
        raise HTTPException(400, "status must be 'scheduled' or 'paid'")

    try:
        oid = ObjectId(dist_id)
    except Exception:
        raise HTTPException(400, "Invalid distribution ID")

    distribution = await db.distributions.find_one({"_id": oid})
    if not distribution:
        raise HTTPException(404, "Distribution not found")

    # Find and update the matching line item
    line_items = distribution.get("line_items", [])
    matched_li = None
    for li in line_items:
        if li.get("investor_id") == investor_id:
            li["status"] = payload.status
            matched_li = li
            break

    if matched_li is None:
        raise HTTPException(404, f"No line item found for investor {investor_id}")

    await db.distributions.update_one(
        {"_id": oid},
        {"$set": {"line_items": line_items}},
    )

    now = datetime.now(timezone.utc)
    await db.audit_logs.insert_one({
        "user_email": current_user.get("email", ""),
        "user_role": current_user.get("role", ""),
        "user_name": current_user.get("name", ""),
        "action": "distribution_paid",
        "target_id": dist_id,
        "target_type": "distribution",
        "timestamp": now,
        "notes": f"Line item marked {payload.status} | {distribution.get('distribution_name')} | investor: {investor_id}",
    })

    # Fire email notification when marked as paid — non-blocking
    if payload.status == "paid":
        asyncio.create_task(notify_distribution_paid(db, distribution, investor_id, matched_li))

    return {"message": f"Line item status updated to {payload.status}", "investor_id": investor_id}
