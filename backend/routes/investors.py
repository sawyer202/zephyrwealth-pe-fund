from datetime import datetime, timezone
from pathlib import Path
import uuid
import json
from functools import partial as _partial
from io import BytesIO

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from bson import ObjectId
from emergentintegrations.llm.chat import LlmChat, UserMessage

from database import db, DOCUMENTS_DIR
from utils import get_current_user, EMERGENT_LLM_KEY, SCORECARD_SYSTEM_PROMPT
from models import InvestorCreateRequest, DecisionRequest, FundParticipationUpdate
from pdf_utils import _pdf_styles, _tbl_style, _PDF_HC, _hf_callback

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm

router = APIRouter(tags=["investors"])


@router.get("/api/investors")
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


@router.post("/api/investors")
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


@router.get("/api/investors/{investor_id}")
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


@router.post("/api/investors/{investor_id}/documents")
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


@router.get("/api/investors/{investor_id}/documents")
async def list_investor_documents(investor_id: str, current_user: dict = Depends(get_current_user)):
    docs = []
    async for doc in db.documents.find({"entity_id": investor_id}).sort("uploaded_at", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("uploaded_at"), datetime):
            doc["uploaded_at"] = doc["uploaded_at"].isoformat()
        docs.append(doc)
    return docs


@router.get("/api/investors/{investor_id}/documents/{document_id}/download")
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


@router.post("/api/investors/{investor_id}/scorecard")
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


@router.get("/api/investors/{investor_id}/scorecard")
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


@router.post("/api/investors/{investor_id}/decision")
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


@router.get("/api/investors/{investor_id}/export-pdf")
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
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=33 * mm, bottomMargin=22 * mm, leftMargin=15 * mm, rightMargin=15 * mm)
    hf = _partial(_hf_callback, title_line2="KYC Compliance Pack", user_name=u_name, user_role=u_role, ts=ts)

    story = []
    inv_name = investor.get("legal_name") or investor.get("name", "Unknown")
    story.append(Paragraph(inv_name, S['h1']))
    story.append(Paragraph("KYC Compliance Pack — Confidential", S['small']))
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#1B3A6B'), spaceAfter=6))
    story.append(Spacer(1, 4 * mm))

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
    ], colWidths=[55 * mm, 115 * mm])
    sc_tbl.setStyle(_tbl_style())
    story.append(sc_tbl)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph(f"KYC Document Checklist ({len(docs)} document{'s' if len(docs) != 1 else ''} on file)", S['h2']))
    DOC_LABELS = {"passport": "Passport / National ID", "proof_of_address": "Proof of Address", "source_of_wealth_doc": "Source of Wealth Declaration", "corporate_documents": "Corporate / Incorporation Documents", "cap_table": "Cap Table", "financials": "Financial Statements"}
    if docs:
        d_rows = [['Document Type', 'File Name', 'Upload Date']]
        for d in docs:
            d_rows.append([DOC_LABELS.get(d.get('document_type', ''), d.get('document_type', '—')), d.get('file_name', '—'), datetime.fromisoformat(str(d.get('uploaded_at', ''))).strftime('%d %b %Y') if d.get('uploaded_at') else '—'])
        d_tbl = Table(d_rows, colWidths=[60 * mm, 70 * mm, 40 * mm])
        d_tbl.setStyle(_tbl_style())
        story.append(d_tbl)
    else:
        story.append(Paragraph("No documents uploaded.", S['body']))
    story.append(Spacer(1, 6 * mm))

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
        sc_tbl2 = Table(sc_rows, colWidths=[70 * mm, 100 * mm])
        ss2 = _tbl_style()
        for ri, row in enumerate(sc_rows[1:], 1):
            col_hex = _PDF_HC.get(row[1])
            if col_hex:
                ss2.add('TEXTCOLOR', (1, ri), (1, ri), rl_colors.HexColor(col_hex))
                ss2.add('FONTNAME', (1, ri), (1, ri), 'Helvetica-Bold')
        sc_tbl2.setStyle(ss2)
        story.append(sc_tbl2)
        story.append(Spacer(1, 3 * mm))

        rec = sc.get('recommendation', '—')
        rec_col = rl_colors.HexColor(_PDF_HC.get(rec, '#374151'))
        rec_tbl = Table([[f"Recommendation: {rec}  |  Score: {score}/100  |  {sc.get('overall_rating', '')}  |  EDD: {'YES' if sc.get('edd_required') else 'NO'}"]], colWidths=[170 * mm])
        rec_tbl.setStyle(TableStyle([('BACKGROUND', (0, 0), (0, 0), rl_colors.HexColor('#252523')), ('TEXTCOLOR', (0, 0), (0, 0), rec_col), ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (0, 0), 9), ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7), ('LEFTPADDING', (0, 0), (-1, -1), 8)]))
        story.append(rec_tbl)
        story.append(Spacer(1, 3 * mm))
        if sc.get('summary'):
            story.append(Paragraph("Analysis Summary", S['h3']))
            story.append(Paragraph(sc['summary'], S['body']))
    else:
        story.append(Paragraph("No AI Compliance Scorecard has been generated for this investor.", S['body']))
    story.append(Spacer(1, 6 * mm))

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
    dec_tbl = Table(dec_rows, colWidths=[40 * mm, 90 * mm, 40 * mm])
    dec_tbl.setStyle(_tbl_style())
    story.append(dec_tbl)

    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=3))
    story.append(Paragraph(f"Report generated: {ts}  |  Prepared by: {u_name} ({u_role})", S['small']))

    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    safe = inv_name.replace(' ', '_')
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="KYC_Pack_{safe}.pdf"'})


@router.patch("/api/investors/{investor_id}/fund-participation")
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
