from datetime import datetime, timezone, timedelta
from io import BytesIO
from functools import partial as _partial

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from bson import ObjectId

from database import db
from utils import get_current_user
from models import TrailerFeeGenerateRequest
from pdf_utils import _pdf_styles, _tbl_style, _hf_callback, _FUND_BANK

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm

router = APIRouter(tags=["trailer-fees"])


def _serialize_tf(doc: dict) -> dict:
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    for k in ("period_start", "period_end", "issued_date", "due_date", "created_at"):
        if isinstance(doc.get(k), datetime):
            doc[k] = doc[k].isoformat()
    return doc


@router.post("/api/trailer-fees/generate")
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


@router.get("/api/trailer-fees")
async def get_trailer_fees(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "risk"):
        raise HTTPException(403, "Compliance or Risk role required")
    result = []
    async for doc in db.trailer_fee_invoices.find().sort("created_at", -1):
        result.append(_serialize_tf(doc))
    return result


@router.get("/api/trailer-fees/{tf_id}")
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


@router.post("/api/trailer-fees/{tf_id}/issue")
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


@router.post("/api/trailer-fees/{tf_id}/mark-paid")
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


@router.get("/api/trailer-fees/{tf_id}/pdf")
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
    pdf_doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=33 * mm, bottomMargin=22 * mm, leftMargin=15 * mm, rightMargin=15 * mm)
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
    ], colWidths=[55 * mm, 115 * mm], style=_tbl_style()))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Bill To", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Agent Name', agent_name],
        ['Company', doc.get("company_name", "—") if doc.get("company_name") else "—"],
        ['Email', "—"],
    ], colWidths=[55 * mm, 115 * mm], style=_tbl_style()))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Fee Schedule", S['h2']))
    li_data = [['Investor Name', 'Deal Name', 'Committed Capital', 'Rate', 'Fee Amount']]
    for li in doc.get("line_items", []):
        li_data.append([li.get("investor_name", ""), li.get("deal_name", "General"), f"USD {li.get('committed_capital', 0):,.2f}", f"{li.get('fee_rate', 0.0075)*100:.2f}%", f"USD {li.get('fee_amount', 0):,.2f}"])
    fee_tbl = Table(li_data, colWidths=[45 * mm, 40 * mm, 35 * mm, 15 * mm, 35 * mm])
    fee_tbl.setStyle(_tbl_style())
    story.append(fee_tbl)
    story.append(Spacer(1, 5 * mm))
    summary_data = [['Item', 'Amount'], ['Subtotal', f"USD {doc.get('subtotal', 0):,.2f}"]]
    if doc.get("vat_applicable"):
        summary_data.append(['VAT (10%)', f"USD {doc.get('vat_amount', 0):,.2f}"])
    summary_data.append(['TOTAL DUE', f"USD {doc.get('total_due', 0):,.2f}"])
    s_tbl = Table(summary_data, colWidths=[100 * mm, 70 * mm])
    s_tbl.setStyle(_tbl_style())
    story.append(s_tbl)
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Payment Instructions", S['h2']))
    story.append(Table([
        ['Field', 'Details'],
        ['Bank Name', _FUND_BANK["bank_name"]],
        ['Account Name', _FUND_BANK["account_name"]],
        ['Account Number', _FUND_BANK["account_number"]],
        ['SWIFT / BIC', _FUND_BANK["swift_code"]],
        ['Reference', inv_num],
    ], colWidths=[55 * mm, 115 * mm], style=_tbl_style()))
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=3))
    story.append(Paragraph(f"Trailer fee per Placement Agent Agreement | Zephyr Asset Management Ltd | Period: {period_y}", S['small']))
    story.append(Paragraph(f"Generated by: {u_name} ({u_role.title()}) | {ts}", S['small']))
    pdf_doc.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="TrailerFeeInvoice_{inv_num}.pdf"'})
