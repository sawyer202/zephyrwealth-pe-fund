import calendar
from datetime import datetime, timezone, timedelta
from functools import partial as _partial
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from bson import ObjectId

from database import db
from utils import get_current_user
from pdf_utils import _pdf_styles, _tbl_style, _PDF_HC, _hf_callback

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm

router = APIRouter(tags=["reports"])


@router.get("/api/audit-logs")
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


@router.get("/api/reports/tav-pdf")
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
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=33 * mm, bottomMargin=22 * mm, leftMargin=15 * mm, rightMargin=15 * mm)
    hf = _partial(_hf_callback, title_line2=f"TAV Report — {quarter_label}", user_name=u_name, user_role=u_role, ts=ts)

    story = []

    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph(fund_profile.get("fund_name", "Zephyr Caribbean Growth Fund I"), S['cover_title']))
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="80%", thickness=2, color=rl_colors.HexColor('#00A8C6'), spaceAfter=8, hAlign='CENTER'))
    story.append(Paragraph(f"Total Asset Value Report — {quarter_label}", S['cover_sub']))
    story.append(Spacer(1, 8 * mm))
    cover_data = [
        ['Reporting Period', f"{period_from}  to  {period_to}"],
        ['Generation Date', ts],
        ['Prepared By', f"{u_name} ({u_role})"],
        ['Fund License', fund_profile.get("license_number", "SCB-2024-PE-0042")],
        ['Fund Manager', fund_profile.get("fund_manager", "Zephyr Asset Management Ltd")],
    ]
    cv_tbl = Table(cover_data, colWidths=[55 * mm, 105 * mm])
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
    story.append(Spacer(1, 16 * mm))
    story.append(Paragraph("CONFIDENTIAL — FOR REGULATORY SUBMISSION ONLY", ParagraphStyle('conf', parent=getSampleStyleSheet()['Normal'], alignment=1, textColor=rl_colors.HexColor('#EF4444'), fontName='Helvetica-Bold', fontSize=9)))
    story.append(PageBreak())

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
    s1_tbl = Table(s1_data, colWidths=[55 * mm, 115 * mm])
    s1_tbl.setStyle(_tbl_style())
    story.append(s1_tbl)
    story.append(Spacer(1, 8 * mm))

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
        p2_tbl = Table(p2_rows, colWidths=[40 * mm, 28 * mm, 25 * mm, 16 * mm, 28 * mm, 16 * mm, 17 * mm])
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
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Section 3 — Total Asset Value", S['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=4))
    tav_highlight = Table([[f"USD {total_tav:,.0f}", "Total Asset Value"]], colWidths=[85 * mm, 85 * mm])
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
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Breakdown by Sector", S['h3']))
    sec_rows = [['Sector', 'Total Valuation (USD)', '% of TAV']]
    for sec, val in sorted(sector_breakdown.items(), key=lambda x: -x[1]):
        pct = (val / total_tav * 100) if total_tav else 0
        sec_rows.append([sec, f"${val:,.0f}", f"{pct:.1f}%"])
    sec_tbl = Table(sec_rows, colWidths=[70 * mm, 60 * mm, 40 * mm])
    sec_tbl.setStyle(_tbl_style())
    story.append(sec_tbl)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Breakdown by Entity Type (IBC vs ICON)", S['h3']))
    ent_rows = [['Entity Type', 'Total Valuation (USD)', '% of TAV']]
    for et, val in sorted(entity_breakdown.items(), key=lambda x: -x[1]):
        pct = (val / total_tav * 100) if total_tav else 0
        ent_rows.append([et, f"${val:,.0f}", f"{pct:.1f}%"])
    ent_tbl = Table(ent_rows, colWidths=[70 * mm, 60 * mm, 40 * mm])
    ent_tbl.setStyle(_tbl_style())
    story.append(ent_tbl)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Section 4 — Investor Base Summary", S['h2']))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=4))
    s4_data = [
        ['Metric', 'Count'],
        ['Total Investors', str(total_inv)],
        ['Approved', str(approved_inv)],
        ['Individual Investors', str(ind_inv)],
        ['Corporate / Institutional', str(corp_inv)],
    ]
    s4_tbl = Table(s4_data, colWidths=[100 * mm, 70 * mm])
    s4_tbl.setStyle(_tbl_style())
    story.append(s4_tbl)
    story.append(Spacer(1, 8 * mm))

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
    s5_tbl = Table(s5_data, colWidths=[100 * mm, 70 * mm])
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
