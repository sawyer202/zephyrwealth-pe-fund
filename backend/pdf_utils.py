from functools import partial as _partial
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors as rl_colors
from reportlab.lib.units import mm


# ─── Header / Footer Callback ────────────────────────────────────────────────

def _hf_callback(canvas, doc, *, title_line2, user_name, user_role, ts):
    """Draw branded header and footer on every page."""
    page_w, page_h = A4
    canvas.saveState()
    canvas.setFillColor(rl_colors.HexColor('#1B3A6B'))
    canvas.rect(0, page_h - 28 * mm, page_w, 28 * mm, fill=True, stroke=False)
    canvas.setFillColor(rl_colors.white)
    canvas.setFont('Helvetica-Bold', 13)
    canvas.drawString(15 * mm, page_h - 11 * mm, 'ZephyrWealth.ai')
    canvas.setFillColor(rl_colors.HexColor('#00A8C6'))
    canvas.setFont('Helvetica', 8)
    canvas.drawString(15 * mm, page_h - 19 * mm, 'Private Equity Back-Office Platform')
    canvas.setFillColor(rl_colors.HexColor('#C9A84C'))
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawRightString(page_w - 15 * mm, page_h - 11 * mm, title_line2)
    canvas.setFillColor(rl_colors.HexColor('#9CA3AF'))
    canvas.setFont('Helvetica', 7)
    canvas.drawRightString(page_w - 15 * mm, page_h - 19 * mm, f'Generated: {ts}')
    canvas.setFillColor(rl_colors.HexColor('#F8F9FA'))
    canvas.rect(0, 0, page_w, 15 * mm, fill=True, stroke=False)
    canvas.setStrokeColor(rl_colors.HexColor('#E5E7EB'))
    canvas.line(0, 15 * mm, page_w, 15 * mm)
    canvas.setFillColor(rl_colors.HexColor('#6B7280'))
    canvas.setFont('Helvetica', 7)
    canvas.drawString(15 * mm, 6 * mm, f'Prepared by ZephyrWealth.ai  |  Confidential — For Regulatory Submission Only  |  {user_name} ({user_role})')
    canvas.drawRightString(page_w - 15 * mm, 6 * mm, f'Page {doc.page}')
    canvas.restoreState()


# ─── Style Factories ─────────────────────────────────────────────────────────

def _pdf_styles():
    ss = getSampleStyleSheet()
    return {
        'h1': ParagraphStyle('zwh1', parent=ss['Normal'], fontSize=18, textColor=rl_colors.HexColor('#1B3A6B'), fontName='Helvetica-Bold', spaceAfter=4),
        'h2': ParagraphStyle('zwh2', parent=ss['Normal'], fontSize=12, textColor=rl_colors.HexColor('#1B3A6B'), fontName='Helvetica-Bold', spaceAfter=3, spaceBefore=8),
        'h3': ParagraphStyle('zwh3', parent=ss['Normal'], fontSize=10, textColor=rl_colors.HexColor('#374151'), fontName='Helvetica-Bold', spaceAfter=2, spaceBefore=4),
        'body': ParagraphStyle('zwbody', parent=ss['Normal'], fontSize=9, textColor=rl_colors.HexColor('#374151'), fontName='Helvetica', spaceAfter=2),
        'small': ParagraphStyle('zwsmall', parent=ss['Normal'], fontSize=7.5, textColor=rl_colors.HexColor('#6B7280'), fontName='Helvetica', spaceAfter=1),
        'center': ParagraphStyle('zwcenter', parent=ss['Normal'], fontSize=9, alignment=1, textColor=rl_colors.HexColor('#374151'), fontName='Helvetica'),
        'cover_title': ParagraphStyle('zwcvt', parent=ss['Normal'], fontSize=26, textColor=rl_colors.HexColor('#1B3A6B'), alignment=1, fontName='Helvetica-Bold', spaceAfter=6),
        'cover_sub': ParagraphStyle('zwcvs', parent=ss['Normal'], fontSize=13, textColor=rl_colors.HexColor('#00A8C6'), alignment=1, fontName='Helvetica', spaceAfter=4),
        'cover_body': ParagraphStyle('zwcvb', parent=ss['Normal'], fontSize=10, textColor=rl_colors.HexColor('#6B7280'), alignment=1, fontName='Helvetica', spaceAfter=3),
    }


def _tbl_style():
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1B3A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), rl_colors.HexColor('#374151')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor('#F8F9FA')]),
        ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#E5E7EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])


# ─── Color Map ───────────────────────────────────────────────────────────────

_PDF_HC = {
    'Low': '#10B981', 'High': '#EF4444', 'Medium': '#F59E0B',
    'Aligned': '#10B981', 'Misaligned': '#EF4444',
    'Complete': '#10B981', 'Partial': '#F59E0B', 'Missing': '#EF4444',
    'In Mandate': '#10B981', 'Exception': '#EF4444', 'Exception Cleared': '#F59E0B',
    'Recommend Approve': '#10B981', 'Review': '#F59E0B', 'Block': '#EF4444',
    'Approve': '#10B981', 'Reject': '#EF4444', 'Review_rec': '#F59E0B',
}

# ─── Fund Bank Details ───────────────────────────────────────────────────────

_FUND_BANK = {
    "bank_name": "Bank of The Bahamas",
    "account_name": "Zephyr Caribbean Growth Fund I",
    "account_number": "0123456789",
    "swift_code": "BAHABSNA",
    "branch": "Nassau, New Providence, The Bahamas",
}


# ─── Capital Call Notice PDF Builder ─────────────────────────────────────────

def _build_notice_pdf(call: dict, li: dict, fund_profile: dict, user_name: str, user_role: str) -> BytesIO:
    S = _pdf_styles()
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    buf = BytesIO()
    doc_obj = SimpleDocTemplate(buf, pagesize=A4, topMargin=33 * mm, bottomMargin=22 * mm, leftMargin=15 * mm, rightMargin=15 * mm)
    hf = _partial(_hf_callback, title_line2="CAPITAL CALL NOTICE — CONFIDENTIAL", user_name=user_name, user_role=user_role, ts=ts)
    story = []
    fund_name = fund_profile.get("fund_name", "Zephyr Caribbean Growth Fund I") if fund_profile else "Zephyr Caribbean Growth Fund I"
    license_num = fund_profile.get("license_number", "SCB-2024-PE-0042") if fund_profile else "SCB-2024-PE-0042"
    story.append(Paragraph("CAPITAL CALL NOTICE", ParagraphStyle("notitle", parent=getSampleStyleSheet()['Normal'], fontSize=20, textColor=rl_colors.HexColor('#1B3A6B'), fontName='Helvetica-Bold', spaceAfter=2, alignment=1)))
    story.append(Paragraph(fund_name, ParagraphStyle("nosub", parent=getSampleStyleSheet()['Normal'], fontSize=12, textColor=rl_colors.HexColor('#00A8C6'), fontName='Helvetica', spaceAfter=2, alignment=1)))
    story.append(Paragraph(f"SCB License: {license_num}", ParagraphStyle("nosc", parent=getSampleStyleSheet()['Normal'], fontSize=9, textColor=rl_colors.HexColor('#6B7280'), fontName='Helvetica', spaceAfter=6, alignment=1)))
    story.append(HRFlowable(width="100%", thickness=1, color=rl_colors.HexColor('#1B3A6B'), spaceAfter=6))
    story.append(Paragraph("Fund Details", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Fund Name', fund_name],
        ['Fund Manager', fund_profile.get("fund_manager", "Zephyr Asset Management Ltd") if fund_profile else "Zephyr Asset Management Ltd"],
        ['SCB License', license_num],
        ['Call Reference', call.get("call_name", "")],
        ['Call Date', call.get("call_date", "")[:10] if call.get("call_date") else "—"],
        ['Due Date', call.get("due_date", "")[:10] if call.get("due_date") else "—"],
    ], colWidths=[55 * mm, 115 * mm], style=_tbl_style()))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Investor Details", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Legal Name', li.get("investor_name", "")],
        ['Share Class', f"Class {li.get('share_class', '—')}"],
        ['Committed Capital', f"USD {li.get('committed_capital', 0):,.2f}"],
    ], colWidths=[55 * mm, 115 * mm], style=_tbl_style()))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Capital Call Details", S['h2']))
    story.append(Table([
        ['Field', 'Value'],
        ['Call Name', call.get("call_name", "")],
        ['Call Type', call.get("call_type", "").replace("_", " ").title()],
        ['Call Percentage', f"{call.get('call_percentage', 0)}% of Committed Capital"],
        ['Amount Due from Investor', f"USD {li.get('call_amount', 0):,.2f}"],
        ['Payment Due Date', call.get("due_date", "")[:10] if call.get("due_date") else "—"],
    ], colWidths=[70 * mm, 100 * mm], style=_tbl_style()))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Payment Instructions", S['h2']))
    ref = f"{li.get('investor_name', '')} — {call.get('call_name', '')}"
    story.append(Table([
        ['Field', 'Details'],
        ['Bank Name', _FUND_BANK["bank_name"]],
        ['Account Name', _FUND_BANK["account_name"]],
        ['Account Number', _FUND_BANK["account_number"]],
        ['SWIFT / BIC', _FUND_BANK["swift_code"]],
        ['Branch', _FUND_BANK["branch"]],
        ['Payment Reference', ref],
        ['Amount', f"USD {li.get('call_amount', 0):,.2f}"],
    ], colWidths=[55 * mm, 115 * mm], style=_tbl_style()))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("Default Notice", S['h2']))
    story.append(Paragraph("Failure to fund by the due date will result in interest accruing at 8% per annum on the outstanding amount. After 30 days of non-payment, LP forfeiture provisions under the Subscription Agreement apply. For questions, contact compliance@zephyrwealth.ai.", S['body']))
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=rl_colors.HexColor('#E5E7EB'), spaceAfter=3))
    story.append(Paragraph(f"Prepared by: {user_name} ({user_role.title()})  |  Date: {ts[:11]}", S['small']))
    story.append(Paragraph("Confidential — Zephyr Asset Management Ltd | SCB Licensed Fund", S['small']))
    doc_obj.build(story, onFirstPage=hf, onLaterPages=hf)
    buf.seek(0)
    return buf
