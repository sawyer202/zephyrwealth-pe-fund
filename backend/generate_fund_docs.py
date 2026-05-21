"""
Generate fund documents for Zephyr Caribbean Growth Fund I.

This script generates:
  • 9 Fund-level title-page placeholder PDFs (visible in back-office Reports
    + Investor Portal Documents tab for every investor).
  • 1 Investor-specific Capital Call Report PDF for investor1@caymantech.com
    (visible only inside that investor's portal Documents tab).

All numbers shown on the PDFs are pulled live from the database at run time
so they stay consistent with the dashboard KPIs.

Run: python3 /app/backend/generate_fund_docs.py
"""
import os
import sys
import asyncio
from datetime import datetime, timezone

sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# ── Brand colours ────────────────────────────────────────────────────────────
DARK = colors.HexColor("#111110")
AQUA = colors.HexColor("#00A8C6")
NAVY = colors.HexColor("#1B3A6B")
WHITE = colors.white
BORDER = colors.HexColor("#E8E6E0")
MUTED = colors.HexColor("#888880")
TEXT = colors.HexColor("#0F0F0E")
LIGHT = colors.HexColor("#F3F4F6")

UPLOAD_DIR = "/app/backend/uploads/fund_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

W, H = A4


def fmt_usd(v):
    try:
        return f"${float(v or 0):,.0f}"
    except Exception:
        return "$0"


def page_header(doc_title, fund_name, license_no):
    def on_page(canv, doc):
        canv.saveState()
        # Dark header bar
        canv.setFillColor(DARK)
        canv.rect(0, H - 2.0 * cm, W, 2.0 * cm, fill=1, stroke=0)
        canv.setFillColor(WHITE)
        canv.setFont("Helvetica-Bold", 13)
        canv.drawString(1.8 * cm, H - 1.30 * cm, "Zephyr")
        canv.setFillColor(AQUA)
        canv.drawString(3.55 * cm, H - 1.30 * cm, "Wealth")
        canv.setFillColor(colors.HexColor("#E8E8E4"))
        canv.setFont("Helvetica", 8)
        canv.drawRightString(W - 1.8 * cm, H - 1.30 * cm, doc_title)
        # Footer
        canv.setFillColor(MUTED)
        canv.setFont("Helvetica", 7)
        footer = f"{fund_name}  |  SCB License {license_no}  |  CONFIDENTIAL"
        canv.drawCentredString(W / 2, 1.1 * cm, footer)
        canv.setStrokeColor(BORDER)
        canv.setLineWidth(0.4)
        canv.line(1.8 * cm, 1.55 * cm, W - 1.8 * cm, 1.55 * cm)
        canv.restoreState()
    return on_page


def build_placeholder_pdf(path, title, subtitle, doc_type_label, version,
                         fund_ctx, kpis, regulatory_note=None):
    """Generate a clean single-page title-card style fund document PDF.

    fund_ctx: dict with fund metadata (fund_name, license, manager, etc.)
    kpis: list of (label, value) tuples matching dashboard numbers.
    """
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=3.0 * cm, bottomMargin=2.0 * cm,
    )

    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold",
                                fontSize=22, textColor=TEXT, leading=26,
                                spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica",
                                   fontSize=11, textColor=MUTED, leading=15,
                                   spaceAfter=4),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold",
                                fontSize=9, textColor=AQUA, leading=12,
                                spaceAfter=2),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9,
                               textColor=TEXT, leading=14, spaceAfter=6),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.5,
                                textColor=MUTED, leading=11, spaceAfter=4),
        "tag": ParagraphStyle("tag", fontName="Helvetica-Bold", fontSize=8,
                              textColor=WHITE, leading=10),
    }

    elems = []
    elems.append(Spacer(1, 1.5 * cm))

    # Document type tag
    tag = Table(
        [[Paragraph(doc_type_label.upper(), styles["tag"])]],
        colWidths=[6 * cm],
    )
    tag.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(tag)
    elems.append(Spacer(1, 0.8 * cm))

    elems.append(Paragraph(title, styles["title"]))
    elems.append(Paragraph(subtitle, styles["subtitle"]))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=BORDER,
                            spaceAfter=14, spaceBefore=6))

    # Fund metadata block
    meta_rows = [
        ["Fund Name", fund_ctx["fund_name"]],
        ["Document Type", doc_type_label],
        ["Document Version", version],
        ["Date Issued", datetime.now(timezone.utc).strftime("%d %B %Y")],
        ["Regulator", "Securities Commission of The Bahamas (SCB)"],
        ["Investment Funds Act", "2019"],
        ["License Number", fund_ctx["license_number"]],
        ["Fund Manager", fund_ctx["fund_manager"]],
        ["Bank", fund_ctx["bank_name"]],
    ]
    meta_tbl = Table(meta_rows, colWidths=[5.0 * cm, 10.5 * cm])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    elems.append(meta_tbl)
    elems.append(Spacer(1, 0.7 * cm))

    # Live KPI block
    elems.append(Paragraph("Fund Key Figures (live values)", styles["label"]))
    kpi_rows = [["Metric", "Value"]]
    for k, v in kpis:
        kpi_rows.append([k, v])
    kpi_tbl = Table(kpi_rows, colWidths=[8.5 * cm, 7.0 * cm])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    elems.append(kpi_tbl)
    elems.append(Spacer(1, 0.7 * cm))

    # Placeholder body
    elems.append(Paragraph(
        f"This document is a placeholder for the {doc_type_label} of "
        f"{fund_ctx['fund_name']}. The full document is on file with the Fund "
        f"Manager and the Securities Commission of The Bahamas, and may be "
        f"requested by accredited investors and authorised parties through "
        f"the Investor Portal data room or by contacting the Compliance Office "
        f"at compliance@zephyrwealth.ai.",
        styles["body"],
    ))

    if regulatory_note:
        elems.append(Spacer(1, 0.3 * cm))
        elems.append(Paragraph(regulatory_note, styles["small"]))

    elems.append(Spacer(1, 0.5 * cm))
    elems.append(HRFlowable(width="100%", thickness=0.4, color=BORDER))
    elems.append(Spacer(1, 0.2 * cm))
    elems.append(Paragraph(
        "CONFIDENTIAL — This document is provided for information purposes "
        "only and does not constitute an offer to sell or a solicitation to "
        "buy any securities. Investments involve risk including possible loss "
        "of principal. Past performance is not indicative of future results.",
        styles["small"],
    ))

    doc.build(
        elems,
        onFirstPage=page_header(doc_type_label, fund_ctx["fund_name"],
                                fund_ctx["license_number"]),
        onLaterPages=page_header(doc_type_label, fund_ctx["fund_name"],
                                 fund_ctx["license_number"]),
    )
    print(f"  ✓ {os.path.basename(path)}  ({os.path.getsize(path):,} bytes)")


def build_capital_call_report(path, investor, fund_ctx, calls_for_investor):
    """Investor-specific Capital Call Report PDF."""
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
        topMargin=3.0 * cm, bottomMargin=2.0 * cm,
    )

    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold",
                                fontSize=22, textColor=TEXT, leading=26,
                                spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontName="Helvetica",
                                   fontSize=11, textColor=MUTED, leading=15,
                                   spaceAfter=4),
        "label": ParagraphStyle("label", fontName="Helvetica-Bold",
                                fontSize=9, textColor=AQUA, leading=12,
                                spaceAfter=2),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9,
                               textColor=TEXT, leading=14, spaceAfter=6),
        "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.5,
                                textColor=MUTED, leading=11, spaceAfter=4),
        "tag": ParagraphStyle("tag", fontName="Helvetica-Bold", fontSize=8,
                              textColor=WHITE, leading=10),
    }

    elems = []
    elems.append(Spacer(1, 1.5 * cm))

    tag = Table(
        [[Paragraph("INVESTOR CAPITAL CALL REPORT", styles["tag"])]],
        colWidths=[6.5 * cm],
    )
    tag.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AQUA),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elems.append(tag)
    elems.append(Spacer(1, 0.8 * cm))

    elems.append(Paragraph("Capital Call Report", styles["title"]))
    elems.append(Paragraph(
        f"{investor['name']}  ·  Generated "
        f"{datetime.now(timezone.utc).strftime('%d %B %Y')}",
        styles["subtitle"],
    ))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=BORDER,
                            spaceAfter=14, spaceBefore=6))

    # Investor profile
    elems.append(Paragraph("Investor Profile", styles["label"]))
    prof_rows = [
        ["Legal Name", investor["name"]],
        ["Investor ID", investor["investor_id"]],
        ["Share Class", investor.get("share_class") or "A"],
        ["Committed Capital", fmt_usd(investor.get("committed", 0))],
        ["Capital Called to Date", fmt_usd(investor.get("called", 0))],
        ["Uncalled Capital", fmt_usd(investor.get("uncalled", 0))],
        ["Call Rate", f"{investor.get('call_rate', 0):.1f}%"],
    ]
    prof_tbl = Table(prof_rows, colWidths=[5.0 * cm, 10.5 * cm])
    prof_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT),
        ("ALIGN", (1, 3), (1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    elems.append(prof_tbl)
    elems.append(Spacer(1, 0.6 * cm))

    # Capital Call History
    elems.append(Paragraph("Capital Call History", styles["label"]))
    hist_rows = [["Call Name", "Issued", "Due", "Amount", "Status"]]
    for c in calls_for_investor:
        hist_rows.append([
            c["call_name"],
            c["issue_date"],
            c["due_date"],
            fmt_usd(c["amount"]),
            c["status"].title(),
        ])
    hist_tbl = Table(
        hist_rows,
        colWidths=[5.5 * cm, 2.7 * cm, 2.7 * cm, 2.5 * cm, 2.1 * cm],
    )
    hist_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    elems.append(hist_tbl)
    elems.append(Spacer(1, 0.5 * cm))

    # Payment instructions
    elems.append(Paragraph("Payment Instructions (Future Calls)",
                           styles["label"]))
    pay_rows = [
        ["Beneficiary", fund_ctx["fund_name"]],
        ["Bank", fund_ctx["bank_name"]],
        ["Account Number", fund_ctx["bank_account_number"]],
        ["SWIFT / BIC", fund_ctx["swift_code"]],
        ["Reference", f"{investor['name']} — Capital Call"],
    ]
    pay_tbl = Table(pay_rows, colWidths=[5.0 * cm, 10.5 * cm])
    pay_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
    ]))
    elems.append(pay_tbl)

    elems.append(Spacer(1, 0.5 * cm))
    elems.append(HRFlowable(width="100%", thickness=0.4, color=BORDER))
    elems.append(Spacer(1, 0.2 * cm))
    elems.append(Paragraph(
        "CONFIDENTIAL — This report is prepared exclusively for the named "
        "investor. Figures reconcile with the back-office capital call ledger "
        "and the Investor Portal dashboard.",
        styles["small"],
    ))

    doc.build(
        elems,
        onFirstPage=page_header("Capital Call Report",
                                fund_ctx["fund_name"],
                                fund_ctx["license_number"]),
        onLaterPages=page_header("Capital Call Report",
                                 fund_ctx["fund_name"],
                                 fund_ctx["license_number"]),
    )
    print(f"  ✓ {os.path.basename(path)}  ({os.path.getsize(path):,} bytes)")


# ── Document catalogue ───────────────────────────────────────────────────────
FUND_DOCS = [
    {
        "title": "Audited Financial Statement 2025",
        "subtitle": "For the Period Ended 31 December 2025",
        "doc_type_label": "Audited Financial Statement",
        "category": "audited_financials",
        "version": "v1.0 — FY2025",
        "file_name": "ZephyrCGF1_AuditedFinancials_FY2025.pdf",
        "regulatory_note": (
            "Prepared in accordance with IFRS and audited by an SCB-recognised "
            "independent auditor. Filed with the Securities Commission of The "
            "Bahamas within six months of fiscal year-end per s.51 of the "
            "Investment Funds Act 2019."
        ),
    },
    {
        "title": "Fund Factsheet (Fund Overview)",
        "subtitle": "Strategy, Structure & Key Terms",
        "doc_type_label": "Fund Factsheet",
        "category": "fund_factsheet",
        "version": "April 2026",
        "file_name": "ZephyrCGF1_FundFactsheet_April2026.pdf",
        "regulatory_note": None,
    },
    {
        "title": "Q1 2026 Quarterly Report",
        "subtitle": "Portfolio Activity, NAV Update & Liquidity Position",
        "doc_type_label": "Quarterly Report",
        "category": "quarterly_report",
        "version": "Q1 2026",
        "file_name": "ZephyrCGF1_QuarterlyReport_Q1_2026.pdf",
        "regulatory_note": None,
    },
    {
        "title": "Fund Prospectus (Offering Memorandum)",
        "subtitle": "Private Placement Memorandum",
        "doc_type_label": "Fund Prospectus",
        "category": "fund_prospectus",
        "version": "v3.2 — March 2026",
        "file_name": "ZephyrCGF1_Prospectus_v3.2.pdf",
        "nda_required": True,
        "regulatory_note": (
            "Issued under the Investment Funds Act 2019. Filed with the "
            "Securities Commission of The Bahamas. Available to accredited "
            "and professional investors only."
        ),
    },
    {
        "title": "Limited Partnership Agreement",
        "subtitle": "Constitutional Document of the Fund",
        "doc_type_label": "LPA",
        "category": "lpa",
        "version": "Executed 15 January 2025",
        "file_name": "ZephyrCGF1_LPA_2025.pdf",
        "nda_required": True,
        "regulatory_note": None,
    },
    {
        "title": "Investment Fund License (SCB)",
        "subtitle": "Certificate of Registration — Professional Fund",
        "doc_type_label": "SCB License Certificate",
        "category": "scb_license",
        "version": "Issued 2024",
        "file_name": "ZephyrCGF1_SCB_License_Certificate.pdf",
        "regulatory_note": (
            "Issued by the Securities Commission of The Bahamas under the "
            "Investment Funds Act 2019. License Number SCB-2024-PE-0042."
        ),
    },
    {
        "title": "AML / CFT Policy Manual",
        "subtitle": "Compliance with FTRA 2018 & FATF Standards",
        "doc_type_label": "AML / CFT Policy",
        "category": "aml_policy",
        "version": "v2.0 — January 2026",
        "file_name": "ZephyrCGF1_AML_CFT_Policy_v2.0.pdf",
        "regulatory_note": (
            "Aligned with the Financial Transactions Reporting Act 2018, the "
            "Proceeds of Crime Act, and current FATF Recommendations."
        ),
    },
    {
        "title": "Investor Risk Disclosure Statement",
        "subtitle": "Material Risk Factors",
        "doc_type_label": "Risk Disclosure Statement",
        "category": "risk_disclosure",
        "version": "v1.1 — April 2026",
        "file_name": "ZephyrCGF1_RiskDisclosure_v1.1.pdf",
        "regulatory_note": None,
    },
    {
        "title": "Subscription Agreement (Template)",
        "subtitle": "Investor Subscription Form",
        "doc_type_label": "Subscription Agreement",
        "category": "subscription_agreement",
        "version": "Template v2.0",
        "file_name": "ZephyrCGF1_SubscriptionAgreement_v2.0.pdf",
        "nda_required": True,
        "regulatory_note": None,
    },
]


async def main():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]

    # Pull fund profile + bank info
    fp = await db.fund_profile.find_one({}) or {}
    fund_ctx = {
        "fund_name": fp.get("fund_name", "Zephyr Caribbean Growth Fund I"),
        "license_number": fp.get("license_number", "SCB-2024-PE-0042"),
        "fund_manager": fp.get("fund_manager", "Zephyr Asset Management Ltd"),
        "bank_name": fp.get("bank_name", "Bank of The Bahamas"),
        "bank_account_number": fp.get("bank_account_number", "4521-9900-0087"),
        "swift_code": fp.get("swift_code", "BAHABSNA"),
    }

    # Compute fund-level KPIs (match the back-office dashboard)
    total_investors = await db.investors.count_documents({})
    approved = await db.investors.count_documents({"kyc_status": "approved"})
    pending = await db.investors.count_documents({"kyc_status": "pending"})
    deals_pipeline = await db.deals.count_documents(
        {"pipeline_stage": {"$exists": True}}
    )

    committed = 0.0
    called = 0.0
    async for inv in db.investors.find({"kyc_status": "approved"}):
        committed += float(inv.get("committed_capital", 0) or 0)
        called += float(inv.get("capital_called", 0) or 0)
    uncalled = max(0.0, committed - called)
    call_rate = (called / committed * 100) if committed > 0 else 0.0

    kpis = [
        ("Total Investors", str(total_investors)),
        ("Approved Investors", str(approved)),
        ("Pending KYC", str(pending)),
        ("Deals in Pipeline", str(deals_pipeline)),
        ("Total Committed Capital", fmt_usd(committed)),
        ("Total Capital Called", fmt_usd(called)),
        ("Total Uncalled Capital", fmt_usd(uncalled)),
        ("Call Rate", f"{call_rate:.1f}%"),
    ]

    now = datetime.now(timezone.utc)
    print("📄 Generating Fund-level documents (placeholders):")
    fund_doc_records = []
    for d in FUND_DOCS:
        path = os.path.join(UPLOAD_DIR, d["file_name"])
        build_placeholder_pdf(
            path=path,
            title=d["title"],
            subtitle=d["subtitle"],
            doc_type_label=d["doc_type_label"],
            version=d["version"],
            fund_ctx=fund_ctx,
            kpis=kpis,
            regulatory_note=d["regulatory_note"],
        )
        fund_doc_records.append({
            "entity_type": "fund",
            "entity_id": "fund",
            "document_type": d["category"],
            "category": d["category"],
            "title": d["title"],
            "subtitle": d["subtitle"],
            "file_path": path,
            "file_name": d["file_name"],
            "file_size": os.path.getsize(path),
            "version": d["version"],
            "nda_required": d.get("nda_required", False),
            "uploaded_at": now,
        })

    # Seed fund-level documents (idempotent by file_name + entity_type=fund)
    inserted_fund = 0
    for rec in fund_doc_records:
        existing = await db.documents.find_one({
            "entity_type": "fund",
            "file_name": rec["file_name"],
        })
        if existing:
            # Update size + version + uploaded_at so re-runs refresh content
            await db.documents.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "file_size": rec["file_size"],
                    "file_path": rec["file_path"],
                    "uploaded_at": rec["uploaded_at"],
                    "version": rec["version"],
                    "title": rec["title"],
                    "subtitle": rec["subtitle"],
                    "category": rec["category"],
                    "nda_required": rec["nda_required"],
                }},
            )
        else:
            await db.documents.insert_one(rec)
            inserted_fund += 1
    print(f"   Fund-level docs inserted: {inserted_fund} / "
          f"{len(fund_doc_records)}  ({len(fund_doc_records) - inserted_fund} updated)")

    # ── Capital Call Report for investor1 ────────────────────────────────────
    inv_user = await db.investor_users.find_one(
        {"email": "investor1@caymantech.com"}
    )
    if not inv_user:
        print("⚠ investor1@caymantech.com not found — skipping capital call report")
        client.close()
        return

    inv_id = inv_user["investor_id"]
    inv = await db.investors.find_one({"_id": ObjectId(inv_id)})
    inv_committed = float(inv.get("committed_capital", 0) or 0)
    inv_called = float(inv.get("capital_called", 0) or 0)
    inv_uncalled = max(0.0, inv_committed - inv_called)
    inv_call_rate = (inv_called / inv_committed * 100) if inv_committed else 0.0

    investor_ctx = {
        "investor_id": inv_id,
        "name": inv.get("legal_name") or inv.get("name", ""),
        "share_class": inv.get("share_class", "A"),
        "committed": inv_committed,
        "called": inv_called,
        "uncalled": inv_uncalled,
        "call_rate": inv_call_rate,
    }

    calls_for_investor = []
    async for cc in db.capital_calls.find().sort("call_date", 1):
        for li in cc.get("line_items", []):
            if li.get("investor_id") != inv_id:
                continue
            cd = cc.get("call_date") or cc.get("created_at")
            dd = cc.get("due_date")
            calls_for_investor.append({
                "call_name": cc.get("call_name", ""),
                "issue_date": cd.strftime("%d %b %Y")
                              if isinstance(cd, datetime) else "—",
                "due_date": dd.strftime("%d %b %Y")
                            if isinstance(dd, datetime) else "—",
                "amount": li.get("call_amount", 0),
                "status": li.get("status", "pending"),
            })

    cc_file_name = "ZephyrCGF1_CapitalCallReport_CaymanTechVentures.pdf"
    cc_path = os.path.join(UPLOAD_DIR, cc_file_name)
    print("\n📄 Generating Investor-specific document:")
    build_capital_call_report(cc_path, investor_ctx, fund_ctx,
                              calls_for_investor)

    cc_rec = {
        "entity_type": "investor",
        "entity_id": inv_id,
        "document_type": "capital_call_report",
        "category": "capital_call_report",
        "title": "Capital Call Report",
        "subtitle": f"{investor_ctx['name']} — All Calls",
        "file_path": cc_path,
        "file_name": cc_file_name,
        "file_size": os.path.getsize(cc_path),
        "uploaded_at": now,
    }
    existing_cc = await db.documents.find_one({
        "entity_id": inv_id,
        "file_name": cc_file_name,
    })
    if existing_cc:
        await db.documents.update_one(
            {"_id": existing_cc["_id"]},
            {"$set": {
                "file_size": cc_rec["file_size"],
                "file_path": cc_rec["file_path"],
                "uploaded_at": cc_rec["uploaded_at"],
                "title": cc_rec["title"],
                "subtitle": cc_rec["subtitle"],
                "category": cc_rec["category"],
                "document_type": cc_rec["document_type"],
            }},
        )
        print("   Capital Call Report: updated existing record")
    else:
        await db.documents.insert_one(cc_rec)
        print("   Capital Call Report: inserted new record")

    # Clean up old legacy fund_overview / financials docs that were previously
    # attached per-investor (Phase 6 first cut) — fund-level supersedes them.
    LEGACY_FNAMES = [
        "ZephyrCGF1_FundOverview_April2026.pdf",
        "ZephyrCGF1_AuditedFinancials_FY2025.pdf",
    ]
    legacy_removed = await db.documents.delete_many({
        "entity_type": {"$ne": "fund"},
        "file_name": {"$in": LEGACY_FNAMES},
    })
    if legacy_removed.deleted_count:
        print(f"   Legacy per-investor copies removed: "
              f"{legacy_removed.deleted_count}")

    client.close()
    print("\n✅ Done.")


if __name__ == "__main__":
    asyncio.run(main())
