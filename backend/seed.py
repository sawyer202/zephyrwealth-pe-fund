from datetime import datetime, timezone, timedelta
from pathlib import Path
from bson import ObjectId

from database import db, DOCUMENTS_DIR
from utils import hash_password, verify_password

# ─── Seed Users ───────────────────────────────────────────────────────────────
SEED_USERS = [
    {"email": "compliance@zephyrwealth.ai", "password": "Comply1234!", "role": "compliance", "name": "Sarah Chen", "title": "Chief Compliance Officer"},
    {"email": "risk@zephyrwealth.ai", "password": "Risk1234!", "role": "risk", "name": "Marcus Webb", "title": "Head of Risk"},
    {"email": "manager@zephyrwealth.ai", "password": "Manager1234!", "role": "manager", "name": "Jonathan Morrow", "title": "Fund Manager"},
]


async def seed_users():
    for u in SEED_USERS:
        existing = await db.users.find_one({"email": u["email"]})
        if existing is None:
            await db.users.insert_one({
                "email": u["email"],
                "password_hash": hash_password(u["password"]),
                "role": u["role"],
                "name": u["name"],
                "title": u["title"],
                "created_at": datetime.now(timezone.utc),
            })
        elif not verify_password(u["password"], existing["password_hash"]):
            await db.users.update_one(
                {"email": u["email"]},
                {"$set": {"password_hash": hash_password(u["password"])}},
            )


async def seed_demo_data():
    # Phase 1: Basic investors
    if await db.investors.count_documents({}) == 0:
        await db.investors.insert_many([
            {"name": "Harrington & Associates LLC", "type": "Corporate Entity", "submitted_date": datetime(2025, 1, 15, tzinfo=timezone.utc), "risk_rating": "medium", "kyc_status": "pending", "scorecard_completed": False, "country": "Cayman Islands", "investment_amount": 5000000, "created_at": datetime.now(timezone.utc)},
            {"name": "Castlebrook Family Office", "type": "Family Office", "submitted_date": datetime(2025, 2, 3, tzinfo=timezone.utc), "risk_rating": "low", "kyc_status": "approved", "scorecard_completed": True, "country": "Bahamas", "investment_amount": 12000000, "created_at": datetime.now(timezone.utc)},
            {"name": "Meridian Capital Fund III", "type": "Investment Fund", "submitted_date": datetime(2025, 2, 18, tzinfo=timezone.utc), "risk_rating": "high", "kyc_status": "flagged", "scorecard_completed": False, "country": "British Virgin Islands", "investment_amount": 8500000, "created_at": datetime.now(timezone.utc)},
        ])

    # Phase 1: Basic deals
    if await db.deals.count_documents({}) == 0:
        await db.deals.insert_many([
            {"name": "Nassau Waterfront Development", "type": "Real Estate", "submitted_date": datetime(2025, 1, 20, tzinfo=timezone.utc), "risk_rating": "medium", "stage": "due_diligence", "scorecard_completed": False, "target_return": "18%", "deal_size": 25000000, "created_at": datetime.now(timezone.utc)},
            {"name": "Caribbean Logistics Group", "type": "Private Equity", "submitted_date": datetime(2025, 2, 10, tzinfo=timezone.utc), "risk_rating": "low", "stage": "term_sheet", "scorecard_completed": True, "target_return": "22%", "deal_size": 15000000, "created_at": datetime.now(timezone.utc)},
        ])

    # Phase 2: Full-schema investors
    if await db.investors.count_documents({"legal_name": {"$exists": True}}) == 0:
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        inv1_id = ObjectId(); inv1_str = str(inv1_id)
        await db.investors.insert_one({"_id": inv1_id, "legal_name": "Victoria Pemberton", "name": "Victoria Pemberton", "entity_type": "individual", "type": "Individual", "dob": "1982-07-14", "nationality": "United Kingdom", "residence_country": "Bahamas", "email": "v.pemberton@privatemail.com", "phone": "+1 242-555-0191", "address": {"street": "14 Ocean Club Estates", "city": "Nassau", "postal_code": "N-4861", "country": "Bahamas"}, "net_worth": 8500000, "annual_income": 950000, "source_of_wealth": "Investment", "investment_experience": "5+ years", "classification": "individual_accredited", "ubo_declarations": [], "accredited_declaration": True, "risk_rating": "low", "kyc_status": "approved", "scorecard_completed": True, "investment_amount": 3000000, "submitted_date": datetime(2025, 1, 10, tzinfo=timezone.utc), "submitted_at": datetime(2025, 1, 10, tzinfo=timezone.utc), "country": "Bahamas", "created_at": datetime.now(timezone.utc)})
        for dt, fn in [("passport", "passport_victoria_pemberton.pdf"), ("proof_of_address", "utility_bill_jan2025.pdf"), ("source_of_wealth_doc", "investment_portfolio_statement.pdf")]:
            p = DOCUMENTS_DIR / inv1_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": inv1_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 1, 10, tzinfo=timezone.utc)})
        await db.compliance_scorecards.insert_one({"entity_id": inv1_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Clear", "identity_status": "Verified", "document_status": "Complete", "source_of_funds": "Clear", "pep_status": "No", "mandate_status": "In Mandate", "identity_confidence_score": 91, "score_breakdown": {"documents": 28, "source_of_wealth": 23, "sanctions": 24, "nationality_risk": 16}, "risk_rating": "Low", "edd_required": False, "overall_rating": "Low Risk", "recommendation": "Approve", "summary": "Victoria Pemberton presents a low-risk profile with verified UK identity and clean sanctions screening. Source of wealth through investment activities is well-documented and consistent with declared net worth. All required KYC documents are complete and no adverse findings noted."}, "recommendation": "Approve", "generated_at": datetime(2025, 1, 12, tzinfo=timezone.utc), "reviewed_by": None, "decision": "approve", "decision_at": datetime(2025, 1, 15, tzinfo=timezone.utc)})
        inv2_id = ObjectId(); inv2_str = str(inv2_id)
        await db.investors.insert_one({"_id": inv2_id, "legal_name": "Apex Meridian Holdings Ltd", "name": "Apex Meridian Holdings Ltd", "entity_type": "corporate", "type": "Corporate Entity", "dob": None, "nationality": "British Virgin Islands", "residence_country": "British Virgin Islands", "email": "compliance@apexmeridian.com", "phone": "+1 284-555-0147", "address": {"street": "Wickhams Cay II, Road Town", "city": "Road Town", "postal_code": "VG1110", "country": "British Virgin Islands"}, "net_worth": 45000000, "annual_income": 6200000, "source_of_wealth": "Business", "investment_experience": "5+ years", "classification": "institutional", "ubo_declarations": [{"name": "Richard Apex", "nationality": "United Kingdom", "ownership_percentage": 55.0}, {"name": "Sarah Meridian", "nationality": "Canada", "ownership_percentage": 45.0}], "accredited_declaration": False, "risk_rating": "medium", "kyc_status": "pending", "scorecard_completed": False, "investment_amount": 15000000, "submitted_date": datetime(2025, 2, 1, tzinfo=timezone.utc), "submitted_at": datetime(2025, 2, 1, tzinfo=timezone.utc), "country": "British Virgin Islands", "created_at": datetime.now(timezone.utc)})
        for dt, fn in [("passport", "certificate_of_incorporation.pdf"), ("proof_of_address", "registered_office_proof.pdf"), ("source_of_wealth_doc", "audited_financials_2024.pdf"), ("corporate_documents", "memorandum_and_articles.pdf")]:
            p = DOCUMENTS_DIR / inv2_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": inv2_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 2, 1, tzinfo=timezone.utc)})
        inv3_id = ObjectId(); inv3_str = str(inv3_id)
        await db.investors.insert_one({"_id": inv3_id, "legal_name": "Dmitri Volkov", "name": "Dmitri Volkov", "entity_type": "individual", "type": "Individual", "dob": "1975-03-22", "nationality": "Russia", "residence_country": "Cyprus", "email": "d.volkov@privatemail.ru", "phone": "+357 99-555-0188", "address": {"street": "12 Limassol Marina", "city": "Limassol", "postal_code": "3601", "country": "Cyprus"}, "net_worth": 22000000, "annual_income": 1800000, "source_of_wealth": "Business", "investment_experience": "5+ years", "classification": "individual_accredited", "ubo_declarations": [], "accredited_declaration": True, "risk_rating": "high", "kyc_status": "flagged", "scorecard_completed": True, "investment_amount": 8000000, "submitted_date": datetime(2025, 2, 10, tzinfo=timezone.utc), "submitted_at": datetime(2025, 2, 10, tzinfo=timezone.utc), "country": "Cyprus", "created_at": datetime.now(timezone.utc)})
        for dt, fn in [("passport", "passport_dmitri_volkov.pdf"), ("proof_of_address", "bank_statement_cyprus.pdf")]:
            p = DOCUMENTS_DIR / inv3_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": inv3_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 2, 10, tzinfo=timezone.utc)})
        await db.compliance_scorecards.insert_one({"entity_id": inv3_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Flagged", "identity_status": "Partial", "document_status": "Partial", "source_of_funds": "Unexplained", "pep_status": "Possible", "mandate_status": "Blocked", "identity_confidence_score": 34, "score_breakdown": {"documents": 12, "source_of_wealth": 6, "sanctions": 8, "nationality_risk": 8}, "risk_rating": "High", "edd_required": True, "overall_rating": "High Risk", "recommendation": "Reject", "summary": "Dmitri Volkov presents a high-risk profile with Russian nationality and Cyprus residency, triggering enhanced due diligence under FTRA 2018. Sanctions screening returned a potential match requiring further investigation, and source of business wealth cannot be substantiated. Recommendation is Reject pending full sanctions clearance."}, "recommendation": "Reject", "generated_at": datetime(2025, 2, 12, tzinfo=timezone.utc), "reviewed_by": None, "decision": None, "decision_at": None})

    # Phase 3: Fund mandate
    if await db.fund_mandate.count_documents({}) == 0:
        await db.fund_mandate.insert_one({
            "fund_name": "ZephyrWealth Capital Fund I",
            "allowed_sectors": ["Technology", "Financial Services"],
            "allowed_geographies": ["Caribbean", "Africa"],
            "irr_min": 15.0,
            "irr_max": 25.0,
            "max_single_investment": 25000000,
            "updated_at": datetime.now(timezone.utc),
        })

    # Phase 3: Full-schema deals
    if await db.deals.count_documents({"company_name": {"$exists": True}}) == 0:
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        d1_id = ObjectId(); d1_str = str(d1_id)
        await db.deals.insert_one({"_id": d1_id, "company_name": "NexaTech Caribbean Ltd", "name": "NexaTech Caribbean Ltd", "sector": "Technology", "geography": "Caribbean", "asset_class": "Private Equity", "expected_irr": 18.0, "entry_valuation": 8000000, "entity_type": "IBC", "mandate_status": "In Mandate", "pipeline_stage": "ic_review", "stage": "ic_review", "stamp_duty_estimate": 40000, "status": "active", "type": "Technology", "risk_rating": "low", "scorecard_completed": False, "deal_size": 8000000, "target_return": "18%", "submitted_date": datetime(2025, 1, 20, tzinfo=timezone.utc), "created_at": datetime.now(timezone.utc), "created_by": None})
        for dt, fn in [("financials", "nexatech_financials_2024.pdf"), ("cap_table", "nexatech_cap_table.pdf")]:
            p = DOCUMENTS_DIR / d1_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": d1_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 1, 22, tzinfo=timezone.utc)})
        d2_id = ObjectId(); d2_str = str(d2_id)
        await db.deals.insert_one({"_id": d2_id, "company_name": "West African Fintrust ICON", "name": "West African Fintrust ICON", "sector": "Fintech", "geography": "Africa", "asset_class": "Venture", "expected_irr": 12.0, "entry_valuation": 5000000, "entity_type": "ICON", "mandate_status": "Exception", "pipeline_stage": "due_diligence", "stage": "due_diligence", "stamp_duty_estimate": 25000, "status": "active", "type": "Fintech", "risk_rating": "medium", "scorecard_completed": False, "deal_size": 5000000, "target_return": "12%", "submitted_date": datetime(2025, 2, 5, tzinfo=timezone.utc), "created_at": datetime.now(timezone.utc), "created_by": None})
        for dt, fn in [("financials", "waf_financials.pdf")]:
            p = DOCUMENTS_DIR / d2_str / dt; p.mkdir(parents=True, exist_ok=True); fp = p / fn; fp.write_bytes(b"[Seeded placeholder - ZephyrWealth]")
            await db.documents.insert_one({"entity_id": d2_str, "document_type": dt, "file_path": str(fp), "file_name": fn, "file_size": 35, "uploaded_at": datetime(2025, 2, 6, tzinfo=timezone.utc)})
        d3_id = ObjectId()
        await db.deals.insert_one({"_id": d3_id, "company_name": "Nassau Microfinance Co.", "name": "Nassau Microfinance Co.", "sector": "Financial Services", "geography": "Caribbean", "asset_class": "Private Equity", "expected_irr": 22.0, "entry_valuation": 3500000, "entity_type": "IBC", "mandate_status": "In Mandate", "pipeline_stage": "leads", "stage": "leads", "stamp_duty_estimate": 17500, "status": "active", "type": "Financial Services", "risk_rating": "low", "scorecard_completed": False, "deal_size": 3500000, "target_return": "22%", "submitted_date": datetime(2025, 2, 15, tzinfo=timezone.utc), "created_at": datetime.now(timezone.utc), "created_by": None})


async def seed_demo_phase4():
    """Feature 12 — idempotent demo seed. Guard: fund_profile fund_name."""
    if await db.fund_profile.find_one({"fund_name": "Zephyr Caribbean Growth Fund I"}):
        return

    now = datetime.now(timezone.utc)
    def dag(n): return now - timedelta(days=n)

    await db.fund_profile.insert_one({
        "fund_name": "Zephyr Caribbean Growth Fund I",
        "license_number": "SCB-2024-PE-0042",
        "fund_manager": "Zephyr Asset Management Ltd",
        "mandate_sectors": ["Technology", "Financial Services"],
        "mandate_geographies": ["Caribbean", "Africa"],
        "irr_min": 15.0,
        "irr_max": 25.0,
        "created_at": now,
    })

    c_user = await db.users.find_one({"email": "compliance@zephyrwealth.ai"})
    r_user = await db.users.find_one({"email": "risk@zephyrwealth.ai"})
    m_user = await db.users.find_one({"email": "manager@zephyrwealth.ai"})
    c_id = str(c_user["_id"]) if c_user else "system"
    r_id = str(r_user["_id"]) if r_user else "system"
    m_id = str(m_user["_id"]) if m_user else "system"

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

    def mk_doc(entity_id, doc_type, filename):
        p = DOCUMENTS_DIR / entity_id / doc_type
        p.mkdir(parents=True, exist_ok=True)
        fp = p / filename
        fp.write_bytes(b"[Demo seed placeholder - ZephyrWealth Phase 4]")
        return {"entity_id": entity_id, "document_type": doc_type, "file_path": str(fp), "file_name": filename, "file_size": 46, "uploaded_at": dag(45)}

    inv1_id = ObjectId(); inv1_str = str(inv1_id)
    await db.investors.insert_one({"_id": inv1_id, "legal_name": "Cayman Tech Ventures SPV Ltd", "name": "Cayman Tech Ventures SPV Ltd", "entity_type": "corporate", "type": "Corporate Entity", "dob": None, "nationality": "Cayman Islands", "residence_country": "Cayman Islands", "email": "admin@caymantech.ky", "phone": "+1 345-555-0192", "address": {"street": "Windward 1, Regatta Office Park", "city": "Grand Cayman", "postal_code": "KY1-9006", "country": "Cayman Islands"}, "net_worth": 50000000, "annual_income": 8000000, "source_of_wealth": "Investment", "investment_experience": "5+ years", "classification": "institutional", "ubo_declarations": [{"name": "James Caldwell", "nationality": "United Kingdom", "ownership_percentage": 60.0}, {"name": "Patricia Lau", "nationality": "Canada", "ownership_percentage": 40.0}], "accredited_declaration": True, "risk_rating": "low", "kyc_status": "approved", "scorecard_completed": True, "investment_amount": 5000000, "submitted_date": dag(50), "submitted_at": dag(50), "country": "Cayman Islands", "created_at": dag(50), "reviewed_at": dag(46), "reviewed_by": c_id})
    for dt, fn in [("passport", "cert_of_incorporation_cayman_tech.pdf"), ("proof_of_address", "registered_office_cayman.pdf"), ("source_of_wealth_doc", "audited_financials_cayman_tech.pdf")]:
        await db.documents.insert_one(mk_doc(inv1_str, dt, fn))
    await db.compliance_scorecards.insert_one({"entity_id": inv1_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Clear", "identity_status": "Verified", "document_status": "Complete", "source_of_funds": "Clear", "pep_status": "No", "mandate_status": "In Mandate", "identity_confidence_score": 88, "score_breakdown": {"documents": 27, "source_of_wealth": 22, "sanctions": 23, "nationality_risk": 16}, "risk_rating": "Low", "edd_required": False, "overall_rating": "Low Risk", "recommendation": "Approve", "summary": "Cayman Tech Ventures SPV Ltd is a well-structured Cayman SPV with verified institutional UBOs from low-risk jurisdictions. All KYC documentation is complete and source of wealth through technology investment activities is fully substantiated. Sanctions screening returned no adverse findings."}, "recommendation": "Approve", "generated_at": dag(47), "reviewed_by": c_id, "decision": "approve", "decision_at": dag(46)})

    inv2_id = ObjectId(); inv2_str = str(inv2_id)
    await db.investors.insert_one({"_id": inv2_id, "legal_name": "Nassau Capital Partners IBC", "name": "Nassau Capital Partners IBC", "entity_type": "corporate", "type": "Corporate Entity", "dob": None, "nationality": "Bahamas", "residence_country": "Bahamas", "email": "compliance@nassaucapital.bs", "phone": "+1 242-555-0184", "address": {"street": "Bay Street Financial Centre, Suite 401", "city": "Nassau", "postal_code": "N-1234", "country": "Bahamas"}, "net_worth": 25000000, "annual_income": 3500000, "source_of_wealth": "Business", "investment_experience": "5+ years", "classification": "institutional", "ubo_declarations": [{"name": "Reginald Thompson", "nationality": "Bahamas", "ownership_percentage": 100.0}], "accredited_declaration": True, "risk_rating": "low", "kyc_status": "approved", "scorecard_completed": True, "investment_amount": 3000000, "submitted_date": dag(44), "submitted_at": dag(44), "country": "Bahamas", "created_at": dag(44), "reviewed_at": dag(40), "reviewed_by": c_id})
    for dt, fn in [("corporate_documents", "nassau_capital_ibc_cert.pdf"), ("proof_of_address", "nassau_registered_office.pdf"), ("source_of_wealth_doc", "nassau_capital_financials_2024.pdf")]:
        await db.documents.insert_one(mk_doc(inv2_str, dt, fn))
    await db.compliance_scorecards.insert_one({"entity_id": inv2_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Clear", "identity_status": "Verified", "document_status": "Complete", "source_of_funds": "Clear", "pep_status": "No", "mandate_status": "In Mandate", "identity_confidence_score": 84, "score_breakdown": {"documents": 26, "source_of_wealth": 22, "sanctions": 24, "nationality_risk": 12}, "risk_rating": "Low", "edd_required": False, "overall_rating": "Low Risk", "recommendation": "Approve", "summary": "Nassau Capital Partners IBC is a locally-registered Bahamian entity with a single verified beneficial owner and complete KYC documentation. Business income is well-documented and consistent with declared net worth. No adverse sanctions findings."}, "recommendation": "Approve", "generated_at": dag(42), "reviewed_by": c_id, "decision": "approve", "decision_at": dag(40)})

    inv3_id = ObjectId(); inv3_str = str(inv3_id)
    await db.investors.insert_one({"_id": inv3_id, "legal_name": "Marcus Harrington", "name": "Marcus Harrington", "entity_type": "individual", "type": "Individual", "dob": "1978-04-22", "nationality": "Barbados", "residence_country": "Barbados", "email": "m.harrington@privatemail.bb", "phone": "+1 246-555-0177", "address": {"street": "12 Rockley Golf Estate", "city": "Christ Church", "postal_code": "BB15008", "country": "Barbados"}, "net_worth": 12000000, "annual_income": 1800000, "source_of_wealth": "Business", "investment_experience": "5+ years", "classification": "individual_accredited", "ubo_declarations": [], "accredited_declaration": True, "risk_rating": "low", "kyc_status": "approved", "scorecard_completed": True, "investment_amount": 1500000, "submitted_date": dag(38), "submitted_at": dag(38), "country": "Barbados", "created_at": dag(38), "reviewed_at": dag(35), "reviewed_by": c_id})
    for dt, fn in [("passport", "harrington_passport.pdf"), ("proof_of_address", "harrington_utility_barbados.pdf")]:
        await db.documents.insert_one(mk_doc(inv3_str, dt, fn))
    await db.compliance_scorecards.insert_one({"entity_id": inv3_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Clear", "identity_status": "Verified", "document_status": "Complete", "source_of_funds": "Clear", "pep_status": "No", "mandate_status": "In Mandate", "identity_confidence_score": 82, "score_breakdown": {"documents": 25, "source_of_wealth": 21, "sanctions": 24, "nationality_risk": 12}, "risk_rating": "Low", "edd_required": False, "overall_rating": "Low Risk", "recommendation": "Approve", "summary": "Marcus Harrington is a Barbadian national with a clean KYC profile and verified business income. Two KYC documents on file are complete for an individual investor. No PEP or sanctions exposure."}, "recommendation": "Approve", "generated_at": dag(37), "reviewed_by": c_id, "decision": "approve", "decision_at": dag(35)})

    inv4_id = ObjectId(); inv4_str = str(inv4_id)
    await db.investors.insert_one({"_id": inv4_id, "legal_name": "Yolanda Santos", "name": "Yolanda Santos", "entity_type": "individual", "type": "Individual", "dob": "1990-11-03", "nationality": "Trinidad and Tobago", "residence_country": "Trinidad and Tobago", "email": "y.santos@tntmail.tt", "phone": "+1 868-555-0165", "address": {"street": "7 Federation Park", "city": "Port of Spain", "postal_code": "TT100100", "country": "Trinidad and Tobago"}, "net_worth": 3000000, "annual_income": 420000, "source_of_wealth": "Salary", "investment_experience": "1-3 years", "classification": "individual_accredited", "ubo_declarations": [], "accredited_declaration": True, "risk_rating": "medium", "kyc_status": "pending", "scorecard_completed": False, "investment_amount": 500000, "submitted_date": dag(20), "submitted_at": dag(20), "country": "Trinidad and Tobago", "created_at": dag(20)})
    for dt, fn in [("passport", "santos_passport.pdf")]:
        await db.documents.insert_one(mk_doc(inv4_str, dt, fn))

    inv5_id = ObjectId(); inv5_str = str(inv5_id)
    await db.investors.insert_one({"_id": inv5_id, "legal_name": "Meridian Global Holdings Ltd", "name": "Meridian Global Holdings Ltd", "entity_type": "corporate", "type": "Corporate Entity", "dob": None, "nationality": "Panama", "residence_country": "Panama", "email": "admin@meridianglobal.pa", "phone": "+507-555-0144", "address": {"street": "Calle 50, Torres de las Americas", "city": "Panama City", "postal_code": "0810", "country": "Panama"}, "net_worth": 15000000, "annual_income": 2200000, "source_of_wealth": "Business", "investment_experience": "5+ years", "classification": "institutional", "ubo_declarations": [{"name": "Viktor Stanev", "nationality": "Bulgaria", "ownership_percentage": 72.0}], "accredited_declaration": False, "risk_rating": "high", "kyc_status": "flagged", "scorecard_completed": True, "investment_amount": 4000000, "submitted_date": dag(30), "submitted_at": dag(30), "country": "Panama", "created_at": dag(30)})
    for dt, fn in [("passport", "meridian_cert_of_incorporation.pdf"), ("proof_of_address", "meridian_registered_office.pdf")]:
        await db.documents.insert_one(mk_doc(inv5_str, dt, fn))
    await db.compliance_scorecards.insert_one({"entity_id": inv5_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Pending", "identity_status": "Partial", "document_status": "Partial", "source_of_funds": "Requires Clarification", "pep_status": "Possible", "mandate_status": "Exception", "identity_confidence_score": 42, "score_breakdown": {"documents": 14, "source_of_wealth": 10, "sanctions": 10, "nationality_risk": 8}, "risk_rating": "High", "edd_required": True, "overall_rating": "High Risk", "recommendation": "Review", "summary": "Meridian Global Holdings Ltd presents elevated AML risk. Panama registration with a Bulgarian UBO triggers enhanced due diligence under FTRA 2018. Source of business wealth is insufficiently documented. Potential PEP linkage noted — full sanctions clearance required before proceeding."}, "recommendation": "Review", "generated_at": dag(28), "reviewed_by": c_id, "decision": None, "decision_at": None})

    inv6_id = ObjectId(); inv6_str = str(inv6_id)
    await db.investors.insert_one({"_id": inv6_id, "legal_name": "Olympus Private Capital Ltd", "name": "Olympus Private Capital Ltd", "entity_type": "corporate", "type": "Corporate Entity", "dob": None, "nationality": "British Virgin Islands", "residence_country": "British Virgin Islands", "email": "contact@olympusprivate.vg", "phone": "+1 284-555-0133", "address": {"street": "Wickhams Cay I", "city": "Road Town", "postal_code": "VG1110", "country": "British Virgin Islands"}, "net_worth": 8000000, "annual_income": 1100000, "source_of_wealth": "Business", "investment_experience": "3-5 years", "classification": "institutional", "ubo_declarations": [{"name": "Unknown Beneficial Owner", "nationality": "Unknown", "ownership_percentage": 100.0}], "accredited_declaration": False, "risk_rating": "high", "kyc_status": "rejected", "scorecard_completed": True, "investment_amount": 0, "submitted_date": dag(25), "submitted_at": dag(25), "country": "British Virgin Islands", "created_at": dag(25), "reviewed_at": dag(20), "reviewed_by": c_id})
    for dt, fn in [("passport", "olympus_cert_of_incorporation.pdf")]:
        await db.documents.insert_one(mk_doc(inv6_str, dt, fn))
    await db.compliance_scorecards.insert_one({"entity_id": inv6_str, "entity_type": "investor", "scorecard_data": {"sanctions_status": "Flagged", "identity_status": "Unverified", "document_status": "Partial", "source_of_funds": "Unexplained", "pep_status": "Confirmed", "mandate_status": "Blocked", "identity_confidence_score": 18, "score_breakdown": {"documents": 6, "source_of_wealth": 3, "sanctions": 4, "nationality_risk": 5}, "risk_rating": "High", "edd_required": True, "overall_rating": "High Risk", "recommendation": "Reject", "summary": "Olympus Private Capital Ltd fails the KYC/AML compliance threshold. UBO identity cannot be verified; BVI registration with undisclosed beneficial ownership. Sanctions flag raised. Source of wealth is entirely unexplained. Decision: Reject."}, "recommendation": "Reject", "generated_at": dag(22), "reviewed_by": c_id, "decision": "reject", "decision_at": dag(20)})

    dd1_id = ObjectId(); dd1_str = str(dd1_id)
    await db.deals.insert_one({"_id": dd1_id, "company_name": "CaribPay Solutions Ltd", "name": "CaribPay Solutions Ltd", "sector": "Technology", "geography": "Caribbean", "asset_class": "Private Equity", "expected_irr": 19.0, "entry_valuation": 4200000, "entity_type": "IBC", "mandate_status": "In Mandate", "pipeline_stage": "closing", "stage": "closing", "stamp_duty_estimate": 21000, "status": "active", "type": "Technology", "risk_rating": "low", "scorecard_completed": True, "deal_size": 4200000, "target_return": "19%", "submitted_date": dag(55), "created_at": dag(55), "created_by": c_id})
    for dt, fn in [("financials", "caribpay_financials_2024.pdf"), ("cap_table", "caribpay_cap_table.pdf"), ("im", "caribpay_information_memorandum.pdf")]:
        await db.documents.insert_one(mk_doc(dd1_str, dt, fn))

    dd2_id = ObjectId(); dd2_str = str(dd2_id)
    await db.deals.insert_one({"_id": dd2_id, "company_name": "AgroHub Africa Ltd", "name": "AgroHub Africa Ltd", "sector": "Technology", "geography": "Africa", "asset_class": "Private Equity", "expected_irr": 22.0, "entry_valuation": 2800000, "entity_type": "IBC", "mandate_status": "In Mandate", "pipeline_stage": "ic_review", "stage": "ic_review", "stamp_duty_estimate": 14000, "status": "active", "type": "Technology", "risk_rating": "low", "scorecard_completed": True, "deal_size": 2800000, "target_return": "22%", "submitted_date": dag(45), "created_at": dag(45), "created_by": c_id})
    for dt, fn in [("financials", "agrohub_financials.pdf"), ("cap_table", "agrohub_cap_table.pdf")]:
        await db.documents.insert_one(mk_doc(dd2_str, dt, fn))

    dd3_id = ObjectId(); dd3_str = str(dd3_id)
    await db.deals.insert_one({"_id": dd3_id, "company_name": "InsureSync Caribbean ICON", "name": "InsureSync Caribbean ICON", "sector": "Insurance", "geography": "Caribbean", "asset_class": "Venture", "expected_irr": 17.0, "entry_valuation": 3100000, "entity_type": "ICON", "mandate_status": "Exception", "pipeline_stage": "ic_review", "stage": "ic_review", "stamp_duty_estimate": 15500, "status": "active", "type": "Insurance", "risk_rating": "medium", "scorecard_completed": False, "deal_size": 3100000, "target_return": "17%", "submitted_date": dag(35), "created_at": dag(35), "created_by": c_id, "mandate_override_note": "IC approved sector exception — insurance SaaS classified as Financial Services adjacent. Risk Officer override applied."})
    for dt, fn in [("financials", "insuresync_financials.pdf")]:
        await db.documents.insert_one(mk_doc(dd3_str, dt, fn))

    dd4_id = ObjectId(); dd4_str = str(dd4_id)
    await db.deals.insert_one({"_id": dd4_id, "company_name": "SaaSAfrica BV", "name": "SaaSAfrica BV", "sector": "Technology", "geography": "Africa", "asset_class": "Venture", "expected_irr": 24.0, "entry_valuation": 1500000, "entity_type": "IBC", "mandate_status": "In Mandate", "pipeline_stage": "due_diligence", "stage": "due_diligence", "stamp_duty_estimate": 7500, "status": "active", "type": "Technology", "risk_rating": "low", "scorecard_completed": False, "deal_size": 1500000, "target_return": "24%", "submitted_date": dag(25), "created_at": dag(25), "created_by": c_id})
    for dt, fn in [("financials", "saasafrica_pitch_deck.pdf")]:
        await db.documents.insert_one(mk_doc(dd4_str, dt, fn))

    dd5_id = ObjectId(); dd5_str = str(dd5_id)
    await db.deals.insert_one({"_id": dd5_id, "company_name": "CariLogix Ltd", "name": "CariLogix Ltd", "sector": "Financial Services", "geography": "Caribbean", "asset_class": "Private Equity", "expected_irr": 12.0, "entry_valuation": 900000, "entity_type": "ICON", "mandate_status": "Exception", "pipeline_stage": "leads", "stage": "leads", "stamp_duty_estimate": 4500, "status": "active", "type": "Financial Services", "risk_rating": "medium", "scorecard_completed": False, "deal_size": 900000, "target_return": "12%", "submitted_date": dag(10), "created_at": dag(10), "created_by": c_id})

    await db.audit_logs.insert_many([
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "login", "target_id": None, "target_type": "auth", "timestamp": dag(60), "notes": "Login from 10.0.0.1"},
        {"user_id": r_id, "user_email": "risk@zephyrwealth.ai", "user_role": "risk", "user_name": "Marcus Webb", "action": "login", "target_id": None, "target_type": "auth", "timestamp": dag(58), "notes": "Login from 10.0.0.2"},
        {"user_id": m_id, "user_email": "manager@zephyrwealth.ai", "user_role": "manager", "user_name": "Jonathan Morrow", "action": "login", "target_id": None, "target_type": "auth", "timestamp": dag(56), "notes": "Login from 10.0.0.3"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_created", "target_id": inv1_str, "target_type": "investor", "timestamp": dag(50), "notes": "New investor: Cayman Tech Ventures SPV Ltd"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_approved", "target_id": inv1_str, "target_type": "investor", "timestamp": dag(46), "notes": "Decision: approve for Cayman Tech Ventures SPV Ltd"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_created", "target_id": inv2_str, "target_type": "investor", "timestamp": dag(44), "notes": "New investor: Nassau Capital Partners IBC"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "deal_created", "target_id": dd1_str, "target_type": "deal", "timestamp": dag(42), "notes": "New deal: CaribPay Solutions Ltd | In Mandate"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_approved", "target_id": inv2_str, "target_type": "investor", "timestamp": dag(40), "notes": "Decision: approve for Nassau Capital Partners IBC"},
        {"user_id": r_id, "user_email": "risk@zephyrwealth.ai", "user_role": "risk", "user_name": "Marcus Webb", "action": "deal_stage_moved", "target_id": dd1_str, "target_type": "deal", "timestamp": dag(35), "notes": "Moved to ic_review"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "login", "target_id": None, "target_type": "auth", "timestamp": dag(28), "notes": "Login from 10.0.0.1"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "investor_rejected", "target_id": inv6_str, "target_type": "investor", "timestamp": dag(20), "notes": "Decision: reject for Olympus Private Capital Ltd"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "deal_stage_moved", "target_id": dd2_str, "target_type": "deal", "timestamp": dag(18), "notes": "Moved to ic_review"},
        {"user_id": r_id, "user_email": "risk@zephyrwealth.ai", "user_role": "risk", "user_name": "Marcus Webb", "action": "deal_stage_moved", "target_id": dd3_str, "target_type": "deal", "timestamp": dag(12), "notes": "Moved to ic_review | Override: IC approved sector exception — insurance SaaS classified as Financial Services adjacent. Risk Officer override applied."},
        {"user_id": r_id, "user_email": "risk@zephyrwealth.ai", "user_role": "risk", "user_name": "Marcus Webb", "action": "deal_stage_moved", "target_id": dd1_str, "target_type": "deal", "timestamp": dag(7), "notes": "Moved to closing"},
        {"user_id": c_id, "user_email": "compliance@zephyrwealth.ai", "user_role": "compliance", "user_name": "Sarah Chen", "action": "deal_executed", "target_id": dd1_str, "target_type": "deal", "timestamp": dag(5), "notes": "Transaction executed: CaribPay Solutions Ltd | IBC"},
    ])


async def seed_demo_phase5():
    """Phase 5 idempotent demo seed. Guard: placement_agents count."""
    if await db.placement_agents.count_documents({}) > 0:
        return
    now = datetime.now(timezone.utc)
    def dag(n): return now - timedelta(days=n)

    ag1 = {"agent_name": "Island Capital Advisors Ltd", "company_name": "Island Capital Advisors Ltd", "email": "fees@islandcapital.bs", "phone": "+1 242-555-0201", "bank_name": "RBC Royal Bank (Bahamas)", "bank_account_number": "1234567890", "swift_code": "ROYCBSNA", "vat_registered": True, "vat_number": "VAT-BS-20240042", "created_at": dag(90)}
    ag2 = {"agent_name": "Caribbean Wealth Partners", "company_name": "Caribbean Wealth Partners LLC", "email": "admin@caribwealthpartners.com", "phone": "+1 345-555-0188", "bank_name": "Cayman National Bank", "bank_account_number": "9876543210", "swift_code": "CANACAYK", "vat_registered": False, "vat_number": None, "created_at": dag(80)}
    ag1_res = await db.placement_agents.insert_one(ag1)
    ag2_res = await db.placement_agents.insert_one(ag2)
    ag1_id = str(ag1_res.inserted_id)
    ag2_id = str(ag2_res.inserted_id)

    inv_updates = [
        ("Cayman Tech Ventures SPV Ltd", {"share_class": "A", "committed_capital": 750000.0, "capital_called": 0.0, "capital_uncalled": 750000.0}),
        ("Nassau Capital Partners IBC", {"share_class": "A", "committed_capital": 500000.0, "capital_called": 0.0, "capital_uncalled": 500000.0}),
        ("Marcus Harrington", {"share_class": "B", "committed_capital": 150000.0, "capital_called": 0.0, "capital_uncalled": 150000.0}),
        ("Yolanda Santos", {"share_class": "B", "committed_capital": 100000.0, "capital_called": 0.0, "capital_uncalled": 100000.0}),
        ("Meridian Global Holdings Ltd", {"share_class": "C", "committed_capital": 200000.0, "capital_called": 0.0, "capital_uncalled": 200000.0, "placement_agent_id": ag1_id, "deal_associations": []}),
        ("Olympus Private Capital Ltd", {"share_class": "C", "committed_capital": 0.0, "capital_called": 0.0, "capital_uncalled": 0.0, "placement_agent_id": ag2_id, "deal_associations": []}),
    ]

    alt_names = {
        "Cayman Tech Ventures SPV Ltd": ["Cayman Tech Ventures SPV Ltd"],
        "Nassau Capital Partners IBC": ["Nassau Capital Partners IBC", "Nassau Capital Partners"],
        "Marcus Harrington": ["Marcus Harrington"],
        "Yolanda Santos": ["Yolanda Santos"],
        "Meridian Global Holdings Ltd": ["Meridian Global Holdings Ltd", "Meridian Global Holdings"],
        "Olympus Private Capital Ltd": ["Olympus Private Capital Ltd", "Olympus Private Capital"],
    }

    inv_ids: dict = {}
    for primary, fields in inv_updates:
        names_to_try = alt_names.get(primary, [primary])
        found = None
        for name in names_to_try:
            found = await db.investors.find_one({"$or": [{"legal_name": name}, {"name": name}]})
            if found:
                break
        if found:
            await db.investors.update_one({"_id": found["_id"]}, {"$set": fields})
            inv_ids[primary] = str(found["_id"])

    caribpay_deal = await db.deals.find_one({"$or": [{"company_name": {"$regex": "CaribPay", "$options": "i"}}, {"name": {"$regex": "CaribPay", "$options": "i"}}]})
    if caribpay_deal and "Meridian Global Holdings Ltd" in inv_ids:
        deal_id = str(caribpay_deal["_id"])
        meridian_id = ObjectId(inv_ids["Meridian Global Holdings Ltd"])
        await db.investors.update_one({"_id": meridian_id}, {"$set": {"deal_associations": [deal_id]}})

    cc1_due = dag(60)
    cc1_li = []
    for name, cls in [("Cayman Tech Ventures SPV Ltd", "A"), ("Nassau Capital Partners IBC", "A"), ("Marcus Harrington", "B"), ("Yolanda Santos", "B")]:
        if name in inv_ids:
            inv = await db.investors.find_one({"_id": ObjectId(inv_ids[name])})
            committed = inv.get("committed_capital", 0) or 0
            cc1_li.append({"investor_id": inv_ids[name], "investor_name": name, "share_class": cls, "committed_capital": committed, "call_amount": round(committed * 0.20, 2), "status": "received"})
    cc1_total = sum(li["call_amount"] for li in cc1_li)
    cc1_doc = {"call_name": "Q1 2026 — Initial Drawdown", "call_date": dag(75), "due_date": cc1_due, "deal_id": None, "call_type": "fund_level", "target_classes": ["A", "B"], "call_percentage": 20.0, "total_amount": cc1_total, "status": "issued", "line_items": cc1_li, "created_by": "system", "created_at": dag(80)}
    await db.capital_calls.insert_one(cc1_doc)

    for li in cc1_li:
        inv_oid = ObjectId(li["investor_id"])
        inv = await db.investors.find_one({"_id": inv_oid})
        if inv:
            new_called = (inv.get("capital_called", 0) or 0) + li["call_amount"]
            committed = inv.get("committed_capital", 0) or 0
            await db.investors.update_one({"_id": inv_oid}, {"$set": {"capital_called": new_called, "capital_uncalled": max(0, committed - new_called)}})

    cc2_due = now + timedelta(days=10)
    cc2_li = []
    for name, cls in [("Cayman Tech Ventures SPV Ltd", "A"), ("Nassau Capital Partners IBC", "A"), ("Marcus Harrington", "B"), ("Yolanda Santos", "B")]:
        if name in inv_ids:
            inv = await db.investors.find_one({"_id": ObjectId(inv_ids[name])})
            committed = inv.get("committed_capital", 0) or 0
            status = "pending" if name == "Yolanda Santos" else "received"
            cc2_li.append({"investor_id": inv_ids[name], "investor_name": name, "share_class": cls, "committed_capital": committed, "call_amount": round(committed * 0.25, 2), "status": status})
    cc2_total = sum(li["call_amount"] for li in cc2_li)
    cc2_doc = {"call_name": "Q2 2026 — Harbour House Acquisition", "call_date": dag(5), "due_date": cc2_due, "deal_id": None, "call_type": "fund_level", "target_classes": ["A", "B"], "call_percentage": 25.0, "total_amount": cc2_total, "status": "issued", "line_items": cc2_li, "created_by": "system", "created_at": dag(7)}
    await db.capital_calls.insert_one(cc2_doc)

    for li in cc2_li:
        inv_oid = ObjectId(li["investor_id"])
        inv = await db.investors.find_one({"_id": inv_oid})
        if inv:
            new_called = (inv.get("capital_called", 0) or 0) + li["call_amount"]
            committed = inv.get("committed_capital", 0) or 0
            await db.investors.update_one({"_id": inv_oid}, {"$set": {"capital_called": new_called, "capital_uncalled": max(0, committed - new_called)}})

    meridian_inv = await db.investors.find_one({"_id": ObjectId(inv_ids["Meridian Global Holdings Ltd"])}) if "Meridian Global Holdings Ltd" in inv_ids else None
    if meridian_inv:
        committed_m = meridian_inv.get("committed_capital", 200000.0) or 200000.0
        fee_amount = round(committed_m * 0.0075, 2)
        tf_doc = {
            "agent_id": ag1_id, "agent_name": "Island Capital Advisors Ltd",
            "invoice_number": "TF-2025-001", "period_year": 2025,
            "period_start": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "period_end": datetime(2025, 12, 31, tzinfo=timezone.utc),
            "line_items": [{"investor_id": inv_ids["Meridian Global Holdings Ltd"], "investor_name": "Meridian Global Holdings Ltd", "deal_name": "General Fund", "committed_capital": committed_m, "fee_rate": 0.0075, "fee_amount": fee_amount}],
            "subtotal": fee_amount, "vat_applicable": True,
            "vat_amount": round(fee_amount * 0.10, 2),
            "total_due": round(fee_amount * 1.10, 2),
            "status": "issued", "issued_date": dag(30),
            "due_date": dag(30) + timedelta(days=30),
            "created_by": "system", "created_at": dag(35),
        }
        await db.trailer_fee_invoices.insert_one(tf_doc)
