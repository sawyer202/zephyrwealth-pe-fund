"""
Generate two fund documents for the Investor Portal:
1. Fund Overview (matches BPIF-style professional layout)
2. Audited Financial Statements 2025

Run: python3 /app/backend/generate_fund_docs.py
"""
import os, sys, asyncio
from datetime import datetime, timezone
sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.pdfgen import canvas as pdfcanvas
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# ── Brand colours ──────────────────────────────────────────────────────────────
DARK   = colors.HexColor("#111110")
AQUA   = colors.HexColor("#00A8C6")
WHITE  = colors.white
OFFWHT = colors.HexColor("#FAFAF8")
BORDER = colors.HexColor("#E8E6E0")
MUTED  = colors.HexColor("#888880")
TEXT   = colors.HexColor("#0F0F0E")
LIGHT  = colors.HexColor("#F3F4F6")
GREEN  = colors.HexColor("#15803D")
GBKG   = colors.HexColor("#F0FDF4")

UPLOAD_DIR = "/app/backend/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

W, H = A4

# ── Shared header/footer canvas callback ─────────────────────────────────────
def make_page_header(doc_title: str, fund_name: str):
    def on_page(canv, doc):
        canv.saveState()
        # dark header bar
        canv.setFillColor(DARK)
        canv.rect(0, H - 2.2*cm, W, 2.2*cm, fill=1, stroke=0)
        # "Zephyr" white
        canv.setFillColor(WHITE)
        canv.setFont("Helvetica-Bold", 14)
        canv.drawString(1.8*cm, H - 1.45*cm, "Zephyr")
        # "Wealth" aqua
        canv.setFillColor(AQUA)
        canv.setFont("Helvetica-Bold", 14)
        canv.drawString(3.7*cm, H - 1.45*cm, "Wealth")
        # doc title right-aligned
        canv.setFillColor(colors.HexColor("#E8E8E4"))
        canv.setFont("Helvetica", 9)
        canv.drawRightString(W - 1.8*cm, H - 1.45*cm, doc_title)
        # footer
        canv.setFillColor(MUTED)
        canv.setFont("Helvetica", 7.5)
        footer = f"{fund_name}  |  SCB Licensed Fund SCB-2024-PE-0042  |  Confidential  —  Page {doc.page}"
        canv.drawCentredString(W/2, 1.1*cm, footer)
        # footer line
        canv.setStrokeColor(BORDER)
        canv.setLineWidth(0.5)
        canv.line(1.8*cm, 1.6*cm, W - 1.8*cm, 1.6*cm)
        canv.restoreState()
    return on_page


def base_styles():
    s = getSampleStyleSheet()
    return {
        "h1":    ParagraphStyle("h1",    fontName="Helvetica-Bold",  fontSize=16, textColor=TEXT,  spaceAfter=4,  leading=20),
        "h2":    ParagraphStyle("h2",    fontName="Helvetica-Bold",  fontSize=11, textColor=TEXT,  spaceAfter=3,  spaceBefore=10, leading=15),
        "h3":    ParagraphStyle("h3",    fontName="Helvetica-Bold",  fontSize=9,  textColor=MUTED, spaceAfter=2,  leading=13, textTransform="uppercase"),
        "body":  ParagraphStyle("body",  fontName="Helvetica",       fontSize=9,  textColor=TEXT,  leading=14,    spaceAfter=6),
        "small": ParagraphStyle("small", fontName="Helvetica",       fontSize=7.5,textColor=MUTED, leading=11,    spaceAfter=4),
        "bold":  ParagraphStyle("bold",  fontName="Helvetica-Bold",  fontSize=9,  textColor=TEXT,  leading=14),
        "aqua":  ParagraphStyle("aqua",  fontName="Helvetica-Bold",  fontSize=20, textColor=AQUA,  leading=24,    spaceAfter=2),
    }


# ── TABLE HELPERS ─────────────────────────────────────────────────────────────
def kv_table(rows, col_widths=None):
    """Two-column key-value table."""
    cw = col_widths or [5.5*cm, 9.5*cm]
    t = Table(rows, colWidths=cw)
    t.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8.5),
        ("FONTNAME",    (0, 0), (0, -1),  "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 0), (0, -1),  MUTED),
        ("TEXTCOLOR",   (1, 0), (1, -1),  TEXT),
        ("BACKGROUND",  (0, 0), (-1, 0),  LIGHT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT]),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0),(-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",(0, 0), (-1, -1), 8),
        ("GRID",        (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    return t


def header_table(cols, data, col_widths=None):
    """Standard data table with dark header."""
    all_rows = [cols] + data
    cw = col_widths
    t = Table(all_rows, colWidths=cw)
    style = [
        ("BACKGROUND",   (0, 0), (-1, 0),  DARK),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  8),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 8.5),
        ("TEXTCOLOR",    (0, 1), (-1, -1), TEXT),
        ("ROWBACKGROUNDS",(0, 1),(-1, -1), [WHITE, LIGHT]),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0),(-1, -1),  5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("GRID",         (0, 0), (-1, -1), 0.5, BORDER),
    ]
    t.setStyle(TableStyle(style))
    return t


def highlight_box(text_top, text_bottom, width=4.5*cm):
    """Aqua-bordered highlight metric box."""
    t = Table([[text_top], [text_bottom]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), WHITE),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("BOX",          (0, 0), (-1, -1), 1.5, AQUA),
        ("LINEABOVE",    (0, 0), (-1, 0),  3, AQUA),
    ]))
    return t


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT 1 — FUND OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
def build_fund_overview(path: str):
    st = base_styles()
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=3.0*cm, bottomMargin=2.0*cm,
    )

    elems = []

    # ── Cover section ─────────────────────────────────────────────────────────
    elems.append(Spacer(1, 0.4*cm))
    elems.append(Paragraph("Zephyr Caribbean Growth Fund I", st["h1"]))
    elems.append(Paragraph("FUND OVERVIEW  |  April 2026", st["h3"]))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=10))

    # Summary paragraph
    elems.append(Paragraph(
        "Zephyr Caribbean Growth Fund I is a Bahamas-incorporated semi-liquid evergreen Professional Fund, "
        "licensed by the Securities Commission of The Bahamas (SCB) under the Investment Funds Act 2019. "
        "The Fund targets Caribbean private equity and real estate opportunities while maintaining a "
        "three-tier liquidity architecture that enables quarterly tender offers without compromising "
        "long-term return objectives.",
        st["body"]
    ))

    # ── Highlight metrics (3 boxes inline) ───────────────────────────────────
    def metric_cell(val, lbl):
        v = Paragraph(f'<font color="#00A8C6"><b>{val}</b></font>', ParagraphStyle("v", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=AQUA))
        l = Paragraph(lbl, ParagraphStyle("l", fontName="Helvetica", fontSize=8, textColor=MUTED, leading=12))
        inner = Table([[v], [l]], colWidths=[4.8*cm])
        inner.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("BOX", (0,0), (-1,-1), 1.5, AQUA),
            ("LINEABOVE", (0,0), (-1,0), 3, AQUA),
        ]))
        return inner

    metrics_row = Table(
        [[metric_cell("$25M", "Target AUM"),
          metric_cell("3", "Share Classes"),
          metric_cell("Quarterly", "Liquidity Window")]],
        colWidths=[5.0*cm, 5.0*cm, 5.0*cm],
        hAlign="LEFT",
    )
    metrics_row.setStyle(TableStyle([("ALIGN",(0,0),(-1,-1),"CENTER"), ("LEFTPADDING",(0,0),(-1,-1),0), ("RIGHTPADDING",(0,0),(-1,-1),8)]))
    elems.append(metrics_row)
    elems.append(Spacer(1, 0.5*cm))

    # ── Key Fund Highlights ───────────────────────────────────────────────────
    elems.append(Paragraph("Key Fund Highlights", st["h2"]))
    kv = [
        ["Fund Name",         "Zephyr Caribbean Growth Fund I"],
        ["Structure",         "Semi-Liquid Evergreen Professional Fund (Bahamas IBC)"],
        ["Regulator",         "Securities Commission of The Bahamas (SCB)"],
        ["License Number",    "SCB-2024-PE-0042"],
        ["Fund Manager",      "Zephyr Asset Management Ltd"],
        ["Inception",         "Q1 2025"],
        ["Target AUM",        "USD 25,000,000 (Seed: USD 5,000,000)"],
        ["Minimum Investment","USD 500,000 (Class A) · USD 100,000 (Class B)"],
        ["Subscription",      "Monthly — first business day of each calendar month"],
        ["Redemption",        "Quarterly tender offer — up to 5% of fund NAV per quarter"],
        ["NAV Frequency",     "Quarterly (published within 20 business days of quarter-end)"],
        ["ESG Classification","Article 8 — SFDR (PAI Indicators 1, 13, 18 disclosed annually)"],
        ["Auditor",           "TBA — Independent SCB-compliant auditor"],
        ["Administrator",     "TBA — Licensed fund administrator"],
    ]
    elems.append(kv_table(kv, col_widths=[5.5*cm, 9.7*cm]))
    elems.append(Spacer(1, 0.4*cm))

    # ── Investment Strategy ───────────────────────────────────────────────────
    elems.append(Paragraph("Investment Strategy", st["h2"]))
    elems.append(Paragraph(
        "The Fund pursues a two-pronged strategy: (1) <b>Private Equity</b> — growth-stage Caribbean fintech and "
        "financial services companies, and (2) <b>Real Estate</b> — boutique resort, residential development and "
        "mixed-use commercial assets across The Bahamas and the broader Caribbean region. "
        "Individual deal hold periods target 4–7 years with exits via trade sale, secondary or IPO on BISX.",
        st["body"]
    ))

    elems.append(PageBreak())

    # ── Liquidity Architecture ────────────────────────────────────────────────
    elems.append(Paragraph("Three-Tier Liquidity Architecture", st["h2"]))
    elems.append(Paragraph(
        "The Fund's liquidity sleeve is designed to service quarterly redemptions without forced sales of "
        "illiquid core holdings. Allocations are dynamically managed against target NAV milestones.",
        st["body"]
    ))

    tier_cols = ["Tier", "Name", "% of NAV", "Instruments", "Settlement"]
    tier_data = [
        ["1", "Illiquid Core",        "75–80%",  "Caribbean RE & PE deals (4–7yr hold)",     "N/A — not available for redemptions"],
        ["2", "Semi-Liquid Bridge",   "10–12%",  "BGRS, BISX equities, Caribbean bonds",      "T+2 to T+30"],
        ["3", "Liquid Reserve",       "12–15%",  "BSD T-Bills · USDC · USDT · Sand Dollar",   "Instant to T+3"],
    ]
    elems.append(header_table(tier_cols, tier_data, col_widths=[1.0*cm, 3.2*cm, 2.2*cm, 5.8*cm, 3.0*cm]))
    elems.append(Spacer(1, 0.3*cm))

    # Tier 3 composition
    elems.append(Paragraph("Tier 3 Composition (Liquid Reserve)", st["h3"]))
    t3_cols = ["Instrument", "Allocation", "Rationale"]
    t3_data = [
        ["Bahamas Govt T-Bills (BSD)", "40%", "Zero ICM friction for Bahamian residents · Central Bank issued"],
        ["USDC (USD Coin)",            "25%", "Circle-issued · monthly reserve audits · DARE 2024 custodian"],
        ["USDT (Tether)",              "20%", "Largest stablecoin depth · Caribbean familiarity · DARE custodian"],
        ["Sand Dollar (CBDC)",         "10%", "Central Bank of Bahamas · instant settlement · zero exchange control"],
        ["BSD Cash (bank deposit)",    "5%",  "Operational float · immediate liquidity for expenses"],
    ]
    elems.append(header_table(t3_cols, t3_data, col_widths=[4.5*cm, 2.2*cm, 8.5*cm]))
    elems.append(Spacer(1, 0.3*cm))
    elems.append(Paragraph(
        "Stablecoin risk controls: Max 45% of Tier 3 in stablecoins combined · Each capped at 25% individually · "
        "Custodian must hold DARE 2024 registration with SCB · Algorithmic stablecoins expressly prohibited.",
        st["small"]
    ))

    elems.append(Spacer(1, 0.4*cm))

    # ── Redemption mechanics ──────────────────────────────────────────────────
    elems.append(Paragraph("Redemption Mechanics", st["h2"]))
    redemption_kv = [
        ["Frequency",            "Quarterly tender offer"],
        ["Maximum per quarter",  "5% of fund NAV (excess rolled to next quarter with priority)"],
        ["Early redemption fee", "2% if redeemed within 12 months of subscription"],
        ["Settlement",           "Within 30 days of NAV publication"],
        ["Gate mechanism",       "Board may suspend in extraordinary circumstances — written notice to LPs + SCB within 5 business days"],
    ]
    elems.append(kv_table(redemption_kv, col_widths=[4.5*cm, 10.7*cm]))

    elems.append(PageBreak())

    # ── Fee Structure ─────────────────────────────────────────────────────────
    elems.append(Paragraph("Share Class Fee Structure", st["h2"]))
    fee_cols = ["", "Class A\n(Founding Anchor)", "Class B\n(Professional)", "Class C\n(Co-Investment)"]
    fee_data = [
        ["Management Fee",       "1.5% p.a. committed capital", "2.0% p.a. committed capital", "1.0% p.a. deployed capital"],
        ["Carried Interest",     "15% above 8% hurdle",         "20% above 8% hurdle",         "20% above deal-level 8% hurdle"],
        ["Waterfall",            "European (whole fund)",        "European (whole fund)",        "American-style (deal level)"],
        ["Early Redemption Fee", "2% within 12 months",         "2% within 12 months",         "N/A — deal lock-up applies"],
        ["Trailer Fee (Agents)", "N/A",                         "N/A",                         "0.75% p.a. committed capital"],
        ["Min Investment",       "USD 500,000",                 "USD 100,000",                 "Deal-specific"],
        ["Capital Calls",        "No (monthly subscription)",   "No (monthly subscription)",   "Yes — deal-specific"],
        ["Priority",             "Priority distributions",       "Standard LP",                 "Deal-specific waterfall"],
    ]
    elems.append(header_table(fee_cols, fee_data, col_widths=[4.0*cm, 3.7*cm, 3.7*cm, 3.8*cm]))
    elems.append(Spacer(1, 0.3*cm))
    elems.append(Paragraph(
        "No performance fee on the liquidity sleeve — carried interest applies only to illiquid core returns. "
        "Class A and B investors subscribe monthly at prior month-end NAV. Class C investors participate "
        "through deal-specific capital calls outside the evergreen pool.",
        st["small"]
    ))

    elems.append(Spacer(1, 0.4*cm))

    # ── Regulatory & ESG ─────────────────────────────────────────────────────
    elems.append(Paragraph("Regulatory & ESG Framework", st["h2"]))
    reg_kv = [
        ["Regulatory Status",    "Professional Fund under Investment Funds Act 2019 · SCB Licensed"],
        ["Digital Assets",       "Stablecoin custodian must hold DARE 2024 SCB registration — not self-custodied"],
        ["Exchange Control",     "BSD T-Bills: no ICM required · Foreign currency assets: ICM rules may apply to resident investors"],
        ["ESG Classification",   "SFDR Article 8 — ESG data collected per deal · PAI Indicators 1, 13, 18 disclosed annually"],
        ["Audit Requirement",    "Annual independent audit including stablecoin reserve documentation review"],
    ]
    elems.append(kv_table(reg_kv, col_widths=[4.2*cm, 11.0*cm]))

    elems.append(Spacer(1, 0.4*cm))

    # ── Liquidity milestones table ────────────────────────────────────────────
    elems.append(Paragraph("Liquidity Sleeve Targets by AUM Milestone", st["h2"]))
    ms_cols = ["AUM Target", "Tier 3 (Liquid)", "Tier 2 (Semi-liquid)", "Tier 1 (Illiquid Core)"]
    ms_data = [
        ["$5M (Seed)",       "25%", "15%", "60%"],
        ["$15M (First Close)","15%","12%", "73%"],
        ["$25M (Target)",    "12%", "10%", "78%"],
        ["$50M+ (Mature)",   "10%", "10%", "80%"],
    ]
    elems.append(header_table(ms_cols, ms_data, col_widths=[4.5*cm, 3.5*cm, 3.7*cm, 3.5*cm]))

    elems.append(Spacer(1, 0.6*cm))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    elems.append(Spacer(1, 0.2*cm))
    elems.append(Paragraph(
        "This document is for information purposes only and does not constitute an offer or invitation to subscribe "
        "for shares. Investments in the Fund involve risk, including possible loss of principal. Past performance "
        "is not indicative of future results. This document is confidential and intended solely for the named recipient. "
        "Prospective investors should review the Fund's Offering Memorandum and consult their own advisors.",
        st["small"]
    ))

    doc.build(elems, onFirstPage=make_page_header("Fund Overview — April 2026", "Zephyr Caribbean Growth Fund I"),
              onLaterPages=make_page_header("Fund Overview — April 2026", "Zephyr Caribbean Growth Fund I"))
    print(f"  Generated: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT 2 — AUDITED FINANCIAL STATEMENTS 2025
# ═══════════════════════════════════════════════════════════════════════════════
def build_audited_financials(path: str):
    st = base_styles()
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=3.0*cm, bottomMargin=2.0*cm,
    )
    elems = []

    # ── Cover ─────────────────────────────────────────────────────────────────
    elems.append(Spacer(1, 0.4*cm))
    elems.append(Paragraph("Zephyr Caribbean Growth Fund I", st["h1"]))
    elems.append(Paragraph("AUDITED FINANCIAL STATEMENTS", st["h3"]))
    elems.append(Paragraph("For the Period Ended 31 December 2025", ParagraphStyle("sub", fontName="Helvetica", fontSize=10, textColor=MUTED, spaceAfter=4)))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=10))

    elems.append(Paragraph(
        "Incorporated in The Bahamas as an International Business Company · "
        "Licensed Professional Fund · SCB-2024-PE-0042 · "
        "Registered Address: Nassau, The Bahamas",
        st["small"]
    ))
    elems.append(Spacer(1, 0.4*cm))

    # ── Independent Auditor's Report ──────────────────────────────────────────
    elems.append(Paragraph("Independent Auditor's Report", st["h2"]))
    elems.append(Paragraph("To the Board of Directors and Investors of Zephyr Caribbean Growth Fund I", st["bold"]))
    elems.append(Spacer(1, 0.2*cm))
    elems.append(Paragraph(
        "<b>Opinion</b><br/>"
        "We have audited the financial statements of Zephyr Caribbean Growth Fund I (the \"Fund\"), "
        "which comprise the Statement of Net Assets as at 31 December 2025, the Statement of Operations "
        "and the Statement of Changes in Net Assets for the period then ended, and notes to the financial "
        "statements, including a summary of significant accounting policies.",
        st["body"]
    ))
    elems.append(Paragraph(
        "In our opinion, the accompanying financial statements present fairly, in all material respects, "
        "the financial position of the Fund as at 31 December 2025, and its financial performance and "
        "changes in net assets for the period then ended in accordance with International Financial "
        "Reporting Standards (IFRS).",
        st["body"]
    ))
    elems.append(Paragraph(
        "<b>Basis for Opinion</b><br/>"
        "We conducted our audit in accordance with International Standards on Auditing (ISAs). Our "
        "responsibilities under those standards are further described in the Auditor's Responsibilities "
        "section of our report. We are independent of the Fund in accordance with the ethical requirements "
        "applicable to our audit and we have fulfilled our other ethical responsibilities in accordance "
        "with these requirements.",
        st["body"]
    ))
    elems.append(Paragraph(
        "Signed: Caribbean Assurance Partners (CAP) · Nassau, The Bahamas · 28 March 2026",
        ParagraphStyle("sig", fontName="Helvetica-Oblique", fontSize=8.5, textColor=MUTED, spaceAfter=6)
    ))

    elems.append(PageBreak())

    # ── Statement of Net Assets ───────────────────────────────────────────────
    elems.append(Paragraph("Statement of Net Assets", st["h2"]))
    elems.append(Paragraph("As at 31 December 2025  (USD)", st["h3"]))

    sna_cols = ["", "Note", "2025 (USD)", "2024 (USD)"]
    sna_data = [
        [Paragraph("<b>ASSETS</b>", st["bold"]), "", "", ""],
        ["Private Equity Investments (at fair value)", "4", "3,285,000", "—"],
        ["Real Estate Investments (at fair value)", "5", "1,650,000", "—"],
        ["Bahamas Govt T-Bills (at amortised cost)", "6", "550,000", "—"],
        ["USDC Holdings (at fair value)", "6", "343,750", "—"],
        ["USDT Holdings (at fair value)", "6", "275,000", "—"],
        ["Sand Dollar — CBDC Holdings", "6", "137,500", "—"],
        ["BSD Cash and Bank Balances", "7", "68,750", "15,000"],
        ["Receivables and Prepaid Expenses", "8", "42,300", "—"],
        [Paragraph("<b>Total Assets</b>", st["bold"]), "", Paragraph("<b>6,352,300</b>", st["bold"]), Paragraph("<b>15,000</b>", st["bold"])],
        ["", "", "", ""],
        [Paragraph("<b>LIABILITIES</b>", st["bold"]), "", "", ""],
        ["Management Fee Payable", "9", "(95,925)", "(—)"],
        ["Carried Interest Accrual", "9", "(24,375)", "(—)"],
        ["Accrued Expenses and Other Payables", "10", "(31,200)", "(2,500)"],
        [Paragraph("<b>Total Liabilities</b>", st["bold"]), "", Paragraph("<b>(151,500)</b>", st["bold"]), Paragraph("<b>(2,500)</b>", st["bold"])],
        ["", "", "", ""],
        [Paragraph("<b>NET ASSETS ATTRIBUTABLE TO INVESTORS</b>", st["bold"]), "", Paragraph("<b>6,200,800</b>", st["bold"]), Paragraph("<b>12,500</b>", st["bold"])],
        ["", "", "", ""],
        ["Class A (Founding Anchor) — 2 investors", "", "4,650,600", "—"],
        ["Class B (Professional) — 2 investors", "", "1,550,200", "—"],
        ["Seed Capital (founder shares)", "", "—", "12,500"],
        [Paragraph("<b>Total Investor Equity</b>", st["bold"]), "", Paragraph("<b>6,200,800</b>", st["bold"]), Paragraph("<b>12,500</b>", st["bold"])],
        ["", "", "", ""],
        ["NAV per Unit — Class A", "", "103.42", "100.00"],
        ["NAV per Unit — Class B", "", "102.68", "100.00"],
    ]
    t = Table(sna_data, colWidths=[7.8*cm, 1.5*cm, 3.5*cm, 2.4*cm])
    t.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR",    (0, 0), (-1, -1), TEXT),
        ("TEXTCOLOR",    (1, 0), (1, -1),  MUTED),
        ("ALIGN",        (2, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("LINEBELOW",    (0, 9), (-1, 9),  0.5, BORDER),
        ("LINEBELOW",    (0, 14),(-1, 14), 0.5, BORDER),
        ("LINEBELOW",    (0, 16),(-1, 16), 1.2, DARK),
        ("BACKGROUND",   (0, 16),(-1, 16), LIGHT),
        ("LINEBELOW",    (0, 20),(-1, 20), 0.5, BORDER),
        ("LINEBELOW",    (0, 22),(-1, 22), 1.2, DARK),
        ("BACKGROUND",   (0, 22),(-1, 22), LIGHT),
    ]))
    elems.append(t)
    elems.append(Spacer(1, 0.4*cm))

    elems.append(PageBreak())

    # ── Statement of Operations ───────────────────────────────────────────────
    elems.append(Paragraph("Statement of Operations", st["h2"]))
    elems.append(Paragraph("For the Period 1 January 2025 to 31 December 2025  (USD)", st["h3"]))

    ops_data = [
        [Paragraph("<b>INVESTMENT INCOME</b>", st["bold"]), "", ""],
        ["Interest income — T-Bills and cash",             "7", "12,430"],
        ["Stablecoin yield income",                         "6", "18,750"],
        ["Unrealised gain on PE investments",               "4", "285,000"],
        ["Unrealised gain on Real Estate investments",      "5", "150,000"],
        [Paragraph("<b>Total Investment Income</b>", st["bold"]), "", Paragraph("<b>466,180</b>", st["bold"])],
        ["", "", ""],
        [Paragraph("<b>EXPENSES</b>", st["bold"]), "", ""],
        ["Management fees",                                 "9", "(95,925)"],
        ["Carried interest accrual",                        "9", "(24,375)"],
        ["Administration and compliance fees",              "10", "(22,400)"],
        ["Legal and professional fees",                     "10", "(8,800)"],
        [Paragraph("<b>Total Expenses</b>", st["bold"]), "", Paragraph("<b>(151,500)</b>", st["bold"])],
        ["", "", ""],
        [Paragraph("<b>NET INCREASE IN NET ASSETS FROM OPERATIONS</b>", st["bold"]), "", Paragraph("<b>314,680</b>", st["bold"])],
    ]
    t2 = Table(ops_data, colWidths=[8.5*cm, 1.5*cm, 5.2*cm])
    t2.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR",    (0, 0), (-1, -1), TEXT),
        ("TEXTCOLOR",    (1, 0), (1, -1),  MUTED),
        ("ALIGN",        (2, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("LINEBELOW",    (0, 5), (-1, 5),  0.5, BORDER),
        ("LINEBELOW",    (0, 12),(-1, 12), 0.5, BORDER),
        ("LINEBELOW",    (0, 14),(-1, 14), 1.2, DARK),
        ("BACKGROUND",   (0, 14),(-1, 14), LIGHT),
    ]))
    elems.append(t2)
    elems.append(Spacer(1, 0.4*cm))

    # ── Notes summary ─────────────────────────────────────────────────────────
    elems.append(Paragraph("Selected Notes to the Financial Statements", st["h2"]))

    notes = [
        ("Note 1 — Organisation",
         "Zephyr Caribbean Growth Fund I (the \"Fund\") was incorporated in The Bahamas as an IBC on "
         "15 January 2025. The Fund is licensed as a Professional Fund under the Investment Funds Act 2019 "
         "by the Securities Commission of The Bahamas (SCB-2024-PE-0042). The Fund's registered office "
         "is located in Nassau, The Bahamas."),
        ("Note 2 — Basis of Preparation",
         "These financial statements have been prepared in accordance with International Financial Reporting "
         "Standards (IFRS) as adopted. The functional and presentation currency is US Dollars (USD). "
         "The financial statements cover the Fund's first full operating period from 1 January 2025 to "
         "31 December 2025."),
        ("Note 3 — Significant Accounting Policies",
         "Private equity and real estate investments are carried at fair value through profit or loss. "
         "Stablecoin holdings are measured at fair value using the closing spot rate from a DARE 2024-licensed "
         "custodian as at the reporting date. BSD T-Bills are carried at amortised cost using the effective "
         "interest method."),
        ("Note 4 — Private Equity Investments",
         "As at 31 December 2025, the Fund holds a minority stake in CaribPay Solutions Ltd (fintech — "
         "Barbados) at a carrying value of USD 3,285,000. The investment was made at USD 3,000,000; the "
         "unrealised gain of USD 285,000 reflects the most recent third-party valuation dated "
         "30 November 2025."),
        ("Note 6 — Stablecoin and Liquid Reserve Holdings",
         "USDC and USDT are held through a DARE 2024-registered Digital Asset Service Provider. "
         "Combined stablecoin exposure is 36.6% of the Tier 3 liquid reserve sleeve, within the Fund's "
         "45% combined cap. Sand Dollar (Bahamas CBDC) is held directly with an authorised commercial "
         "bank and represents 10% of Tier 3. Algorithmic stablecoins are expressly prohibited by the "
         "Fund's investment mandate."),
        ("Note 9 — Management and Carried Interest Fees",
         "Management fees are charged at 1.5% per annum of committed capital for Class A investors "
         "and 2.0% per annum for Class B investors. Carried interest of 15% (Class A) and 20% (Class B) "
         "is accrued on investment gains in excess of the 8% preferred return hurdle rate, calculated "
         "on a European waterfall basis."),
    ]
    for title, text in notes:
        elems.append(KeepTogether([
            Paragraph(title, st["bold"]),
            Paragraph(text, st["body"]),
        ]))

    elems.append(Spacer(1, 0.4*cm))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    elems.append(Spacer(1, 0.2*cm))
    elems.append(Paragraph(
        "These financial statements were approved by the Board of Directors of Zephyr Asset Management Ltd "
        "and authorised for issue on 28 March 2026. Signed on behalf of the Board.",
        st["small"]
    ))

    doc.build(elems,
              onFirstPage=make_page_header("Audited Financial Statements — FY 2025", "Zephyr Caribbean Growth Fund I"),
              onLaterPages=make_page_header("Audited Financial Statements — FY 2025", "Zephyr Caribbean Growth Fund I"))
    print(f"  Generated: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — generate PDFs + seed MongoDB
# ═══════════════════════════════════════════════════════════════════════════════
async def seed_documents():
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL'))
    db = client[os.environ.get('DB_NAME')]

    # Get both portal investor IDs
    users = await db.investor_users.find({}, {'investor_id': 1}).to_list(10)
    investor_ids = [u['investor_id'] for u in users]
    print(f"Found {len(investor_ids)} portal investors")

    now = datetime.now(timezone.utc)
    overview_fname = "ZephyrCGF1_FundOverview_April2026.pdf"
    financials_fname = "ZephyrCGF1_AuditedFinancials_FY2025.pdf"
    overview_path = f"{UPLOAD_DIR}/{overview_fname}"
    financials_path = f"{UPLOAD_DIR}/{financials_fname}"

    # Build PDFs
    print("Building PDFs...")
    build_fund_overview(overview_path)
    build_audited_financials(financials_path)

    overview_size = os.path.getsize(overview_path)
    financials_size = os.path.getsize(financials_path)
    print(f"  Fund Overview: {overview_size:,} bytes")
    print(f"  Audited Financials: {financials_size:,} bytes")

    # Seed into documents collection for each investor
    for inv_id in investor_ids:
        for fname, fpath, doc_type, fsize in [
            (overview_fname, overview_path, "fund_report", overview_size),
            (financials_fname, financials_path, "financials", financials_size),
        ]:
            existing = await db.documents.find_one({"entity_id": inv_id, "file_name": fname})
            if existing:
                print(f"  SKIP (already exists): {fname} for investor {inv_id}")
                continue
            doc = {
                "entity_id": inv_id,
                "entity_type": "investor",
                "document_type": doc_type,
                "file_path": fpath,
                "file_name": fname,
                "file_size": fsize,
                "uploaded_at": now,
            }
            await db.documents.insert_one(doc)
            print(f"  INSERTED: {fname} → investor {inv_id}")

    client.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(seed_documents())
