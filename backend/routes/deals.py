from datetime import datetime, timezone
from pathlib import Path
from functools import partial as _partial
from io import BytesIO

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse, Response
from bson import ObjectId

from database import db, DOCUMENTS_DIR
from utils import (
    get_current_user, normalize_deal, check_deal_mandate,
    generate_subscription_agreement, generate_participation_agreement,
    OLD_DEAL_STAGE_MAP, STAGE_LABELS,
)
from models import DealCreateRequest, DealStageUpdate
from pdf_utils import _pdf_styles, _tbl_style, _PDF_HC, _hf_callback

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm

router = APIRouter(tags=["deals"])


@router.get("/api/deals")
async def get_deals(current_user: dict = Depends(get_current_user)):
    deals = []
    async for doc in db.deals.find().sort("submitted_date", -1):
        deals.append(normalize_deal(doc))
    return deals


@router.post("/api/deals")
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


@router.get("/api/deals/{deal_id}")
async def get_deal(deal_id: str, current_user: dict = Depends(get_current_user)):
    try:
        oid = ObjectId(deal_id)
    except Exception:
        raise HTTPException(400, "Invalid deal ID")
    doc = await db.deals.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Deal not found")
    return normalize_deal(doc)


@router.put("/api/deals/{deal_id}/stage")
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


@router.post("/api/deals/{deal_id}/documents")
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


@router.get("/api/deals/{deal_id}/documents")
async def list_deal_documents(deal_id: str, current_user: dict = Depends(get_current_user)):
    docs = []
    async for doc in db.documents.find({"entity_id": deal_id}).sort("uploaded_at", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("uploaded_at"), datetime):
            doc["uploaded_at"] = doc["uploaded_at"].isoformat()
        docs.append(doc)
    return docs


@router.get("/api/deals/{deal_id}/documents/{document_id}/download")
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


@router.get("/api/deals/{deal_id}/health-score")
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


@router.post("/api/deals/{deal_id}/execute")
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
    return Response(content=content.encode("utf-8"), media_type="application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/api/deals/{deal_id}/export-pdf")
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
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=33 * mm, bottomMargin=22 * mm, leftMargin=15 * mm, rightMargin=15 * mm)
    hf = _partial(_hf_callback, title_line2="Investment Committee Pack", user_name=u_name, user_role=u_role, ts=ts)

    story = []
    story.append(Paragraph(deal.get("company_name", ""), S['h1']))
    story.append(Paragraph("Investment Committee Pack — Confidential", S['small']))
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#1B3A6B'), spaceAfter=6))
    story.append(Spacer(1, 4 * mm))

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
    ], colWidths=[55 * mm, 115 * mm])
    deal_tbl.setStyle(_tbl_style())
    story.append(deal_tbl)
    story.append(Spacer(1, 6 * mm))

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
        m_tbl = Table(m_data, colWidths=[40 * mm, 60 * mm, 40 * mm, 30 * mm])
        ms = _tbl_style()
        for ri, row in enumerate(m_data[1:], 1):
            c = rl_colors.HexColor('#10B981') if row[-1] == 'PASS' else rl_colors.HexColor('#EF4444')
            ms.add('TEXTCOLOR', (3, ri), (3, ri), c)
            ms.add('FONTNAME', (3, ri), (3, ri), 'Helvetica-Bold')
        m_tbl.setStyle(ms)
        story.append(m_tbl)
    mc = rl_colors.HexColor('#10B981') if mandate_status == 'In Mandate' else rl_colors.HexColor('#EF4444')
    ms_lbl = f"Overall Mandate Status: {mandate_status}"
    story.append(Spacer(1, 3 * mm))
    ov_tbl = Table([[ms_lbl]], colWidths=[170 * mm])
    ov_tbl.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), rl_colors.HexColor('#F8F9FA')), ('TEXTCOLOR', (0, 0), (0, 0), mc), ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (0, 0), 10), ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#E5E7EB')), ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
    story.append(ov_tbl)
    story.append(Spacer(1, 6 * mm))

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
    h_tbl = Table(h_data, colWidths=[70 * mm, 100 * mm])
    hs = _tbl_style()
    for ri, row in enumerate(h_data[1:], 1):
        col_hex = _PDF_HC.get(row[1])
        if col_hex:
            hs.add('TEXTCOLOR', (1, ri), (1, ri), rl_colors.HexColor(col_hex))
            hs.add('FONTNAME', (1, ri), (1, ri), 'Helvetica-Bold')
    h_tbl.setStyle(hs)
    story.append(h_tbl)
    story.append(Spacer(1, 6 * mm))

    if deal.get("mandate_override_note"):
        story.append(Paragraph("Risk Officer Override Note", S['h3']))
        story.append(Paragraph(deal["mandate_override_note"], S['body']))
        story.append(Spacer(1, 4 * mm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=3))
    story.append(Paragraph("Rule-based assessment — human review required — ZephyrWealth Compliance Framework", S['small']))
    story.append(Paragraph(f"Report generated: {ts}  |  Prepared by: {u_name} ({u_role})", S['small']))

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    safe = deal.get('company_name', 'Deal').replace(' ', '_')
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="IC_Pack_{safe}.pdf"'})
