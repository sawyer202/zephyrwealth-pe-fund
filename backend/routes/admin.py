from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId

from database import db
from utils import get_current_user
from seed import seed_demo_phase4, seed_demo_phase5

router = APIRouter(tags=["admin"])


@router.post("/api/admin/demo-reset")
async def demo_reset(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "compliance":
        raise HTTPException(status_code=403, detail="Compliance role required")

    cleaned: dict = {}

    # 1. TEST_ prefixed investors + related data
    test_inv_ids = []
    async for inv in db.investors.find({"$or": [
        {"name": {"$regex": "^TEST_", "$options": "i"}},
        {"legal_name": {"$regex": "^TEST_", "$options": "i"}},
        {"name": "Test API User"},
    ]}):
        test_inv_ids.append(str(inv["_id"]))
    if test_inv_ids:
        await db.documents.delete_many({"entity_id": {"$in": test_inv_ids}})
        await db.compliance_scorecards.delete_many({"entity_id": {"$in": test_inv_ids}})
        r = await db.investors.delete_many({"_id": {"$in": [ObjectId(i) for i in test_inv_ids]}})
        cleaned["test_investors_removed"] = r.deleted_count

    # 2. TEST_ prefixed deals + related data
    test_deal_ids = []
    async for deal in db.deals.find({"$or": [
        {"company_name": {"$regex": "^TEST_", "$options": "i"}},
        {"name": {"$regex": "^TEST_", "$options": "i"}},
    ]}):
        test_deal_ids.append(str(deal["_id"]))
    if test_deal_ids:
        await db.documents.delete_many({"entity_id": {"$in": test_deal_ids}})
        r = await db.deals.delete_many({"_id": {"$in": [ObjectId(i) for i in test_deal_ids]}})
        cleaned["test_deals_removed"] = r.deleted_count

    # 3. Phase 4 demo investors (by exact name) + related data
    DEMO_INV_NAMES = [
        "Cayman Tech Ventures SPV Ltd", "Nassau Capital Partners IBC",
        "Marcus Harrington", "Yolanda Santos",
        "Meridian Global Holdings Ltd", "Olympus Private Capital Ltd",
    ]
    demo_inv_ids = []
    async for inv in db.investors.find({"$or": [
        {"name": {"$in": DEMO_INV_NAMES}},
        {"legal_name": {"$in": DEMO_INV_NAMES}},
    ]}):
        demo_inv_ids.append(str(inv["_id"]))
    if demo_inv_ids:
        await db.documents.delete_many({"entity_id": {"$in": demo_inv_ids}})
        await db.compliance_scorecards.delete_many({"entity_id": {"$in": demo_inv_ids}})
        r = await db.investors.delete_many({"_id": {"$in": [ObjectId(i) for i in demo_inv_ids]}})
        cleaned["demo_investors_removed"] = r.deleted_count

    # 4. Phase 4 demo deals (by exact name) + related data
    DEMO_DEAL_NAMES = [
        "CaribPay Solutions Ltd", "AgroHub Africa Ltd",
        "InsureSync Caribbean ICON", "SaaSAfrica BV", "CariLogix Ltd",
    ]
    demo_deal_ids = []
    async for deal in db.deals.find({"$or": [
        {"company_name": {"$in": DEMO_DEAL_NAMES}},
        {"name": {"$in": DEMO_DEAL_NAMES}},
    ]}):
        demo_deal_ids.append(str(deal["_id"]))
    if demo_deal_ids:
        await db.documents.delete_many({"entity_id": {"$in": demo_deal_ids}})
        r = await db.deals.delete_many({"_id": {"$in": [ObjectId(i) for i in demo_deal_ids]}})
        cleaned["demo_deals_removed"] = r.deleted_count

    # 5. Clear ALL audit logs for a pristine log history
    r = await db.audit_logs.delete_many({})
    cleaned["audit_logs_cleared"] = r.deleted_count

    # 6. Remove idempotency guard so Phase 4 seed runs fresh
    await db.fund_profile.delete_one({"fund_name": "Zephyr Caribbean Growth Fund I"})
    cleaned["fund_profile_reset"] = True

    # 7. Clear Phase 5 data
    r5a = await db.placement_agents.delete_many({})
    r5b = await db.capital_calls.delete_many({})
    r5c = await db.trailer_fee_invoices.delete_many({})
    cleaned["placement_agents_cleared"] = r5a.deleted_count
    cleaned["capital_calls_cleared"] = r5b.deleted_count
    cleaned["trailer_fee_invoices_cleared"] = r5c.deleted_count

    # 8. Re-seed Phase 4 pristine data
    await seed_demo_phase4()
    await seed_demo_phase5()
    cleaned["seed_restored"] = True

    # 9. Log the reset (in the freshly seeded audit log)
    await db.audit_logs.insert_one({
        "user_id": current_user.get("_id"),
        "user_email": current_user.get("email", ""),
        "user_role": current_user.get("role", ""),
        "user_name": current_user.get("name", ""),
        "action": "demo_reset",
        "target_id": None,
        "target_type": "system",
        "timestamp": datetime.now(timezone.utc),
        "notes": f"Demo data reset executed by {current_user.get('name', '')}. Cleaned: test_investors={cleaned.get('test_investors_removed', 0)}, test_deals={cleaned.get('test_deals_removed', 0)}, demo_investors={cleaned.get('demo_investors_removed', 0)}, demo_deals={cleaned.get('demo_deals_removed', 0)}, audit_logs={cleaned.get('audit_logs_cleared', 0)}",
    })

    return {
        "message": "Demo data reset successful. Pristine Phase 4 & 5 data restored.",
        "cleaned": cleaned,
    }
