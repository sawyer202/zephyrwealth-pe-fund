"""
Fund-level documents — visible to back-office and to all investor portal users.
Documents live in the `documents` collection with entity_type="fund".

Some documents (Prospectus, LPA, Subscription Agreement) are NDA-gated for
investor-portal downloads. The investor must POST an acknowledgement before
the download endpoint will stream the file. Back-office users are exempt
(they are the document custodians).
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from bson import ObjectId

from database import db
from utils import get_current_user
from routes.portal_auth import get_current_investor

router = APIRouter(tags=["fund-documents"])


def _serialize(doc):
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    if isinstance(doc.get("uploaded_at"), datetime):
        doc["uploaded_at"] = doc["uploaded_at"].isoformat()
    return doc


# ── BACK-OFFICE ──────────────────────────────────────────────────────────────
@router.get("/api/fund-documents")
async def list_fund_documents(
    current_user: dict = Depends(get_current_user),
):
    """List all fund-level documents (back-office)."""
    out = []
    async for d in db.documents.find({"entity_type": "fund"}).sort(
        "uploaded_at", -1
    ):
        out.append(_serialize(d))
    return out


@router.get("/api/fund-documents/{doc_id}/download")
async def download_fund_document(
    doc_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        oid = ObjectId(doc_id)
    except Exception:
        raise HTTPException(400, "Invalid document ID")

    d = await db.documents.find_one({"_id": oid, "entity_type": "fund"})
    if not d:
        raise HTTPException(404, "Fund document not found")

    file_path = Path(d["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "File missing on server")

    return FileResponse(
        path=str(file_path),
        filename=d["file_name"],
        media_type="application/pdf",
    )


# ── INVESTOR PORTAL ──────────────────────────────────────────────────────────
@router.get("/api/portal/fund-documents")
async def portal_list_fund_documents(
    current_investor: dict = Depends(get_current_investor),
):
    """List fund-level documents available to portal investors."""
    out = []
    async for d in db.documents.find({"entity_type": "fund"}).sort(
        "uploaded_at", -1
    ):
        out.append(_serialize(d))
    return out


@router.get("/api/portal/fund-documents/{doc_id}/download")
async def portal_download_fund_document(
    doc_id: str,
    current_investor: dict = Depends(get_current_investor),
):
    try:
        oid = ObjectId(doc_id)
    except Exception:
        raise HTTPException(400, "Invalid document ID")

    d = await db.documents.find_one({"_id": oid, "entity_type": "fund"})
    if not d:
        raise HTTPException(404, "Fund document not found")

    # NDA gate: investor must acknowledge before downloading sensitive docs
    if d.get("nda_required"):
        ack = await db.nda_acknowledgements.find_one({
            "investor_id": current_investor["investor_id"],
            "document_id": str(d["_id"]),
        })
        if not ack:
            raise HTTPException(
                status_code=403,
                detail="NDA acknowledgement required for this document",
            )

    file_path = Path(d["file_path"])
    if not file_path.exists():
        raise HTTPException(404, "File missing on server")

    return FileResponse(
        path=str(file_path),
        filename=d["file_name"],
        media_type="application/pdf",
    )


@router.post("/api/portal/fund-documents/{doc_id}/acknowledge-nda")
async def portal_acknowledge_nda(
    doc_id: str,
    current_investor: dict = Depends(get_current_investor),
):
    """Investor acknowledges the NDA / Professional-Investor representation
    before downloading a sensitive offering document. Idempotent."""
    try:
        oid = ObjectId(doc_id)
    except Exception:
        raise HTTPException(400, "Invalid document ID")

    d = await db.documents.find_one({"_id": oid, "entity_type": "fund"})
    if not d:
        raise HTTPException(404, "Fund document not found")
    if not d.get("nda_required"):
        return {"acknowledged": True, "note": "Document does not require NDA"}

    inv_id = current_investor["investor_id"]
    now = datetime.now(timezone.utc)

    existing = await db.nda_acknowledgements.find_one({
        "investor_id": inv_id,
        "document_id": str(d["_id"]),
    })
    if existing:
        return {
            "acknowledged": True,
            "acknowledged_at": existing["acknowledged_at"].isoformat()
            if isinstance(existing.get("acknowledged_at"), datetime)
            else existing.get("acknowledged_at"),
        }

    await db.nda_acknowledgements.insert_one({
        "investor_id": inv_id,
        "investor_email": current_investor.get("email", ""),
        "investor_name": current_investor.get("name", ""),
        "document_id": str(d["_id"]),
        "document_title": d.get("title") or d.get("file_name"),
        "document_category": d.get("category", ""),
        "acknowledged_at": now,
    })
    return {"acknowledged": True, "acknowledged_at": now.isoformat()}
