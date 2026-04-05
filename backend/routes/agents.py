from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from database import db
from utils import get_current_user
from models import PlacementAgentCreate, PlacementAgentUpdate

router = APIRouter(tags=["agents"])


def _serialize_agent(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


@router.get("/api/agents")
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


@router.post("/api/agents")
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


@router.get("/api/agents/{agent_id}")
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


@router.patch("/api/agents/{agent_id}")
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
