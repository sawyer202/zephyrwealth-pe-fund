from fastapi import APIRouter, Depends

from database import db
from utils import get_current_user, OLD_DEAL_STAGE_MAP

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    total_investors = await db.investors.count_documents({})
    pending_kyc = await db.investors.count_documents({"kyc_status": "pending"})
    deals_in_pipeline = await db.deals.count_documents({})
    flagged_investors = await db.investors.count_documents({"risk_rating": "high"})
    flagged_deals = await db.deals.count_documents({"risk_rating": "high"})
    total_committed = 0.0
    total_called = 0.0
    async for inv in db.investors.find({"kyc_status": "approved", "committed_capital": {"$gt": 0}}):
        total_committed += inv.get("committed_capital", 0) or 0
        total_called += inv.get("capital_called", 0) or 0
    total_uncalled = max(0.0, total_committed - total_called)
    call_rate = round(total_called / total_committed * 100, 1) if total_committed > 0 else 0.0
    return {
        "total_investors": total_investors,
        "pending_kyc": pending_kyc,
        "deals_in_pipeline": deals_in_pipeline,
        "flagged_items": flagged_investors + flagged_deals,
        "total_committed_capital": total_committed,
        "total_capital_called": total_called,
        "total_uncalled": total_uncalled,
        "call_rate": call_rate,
    }


@router.get("/api/dashboard/charts")
async def get_dashboard_charts(current_user: dict = Depends(get_current_user)):
    investor_funnel = []
    for status, color in [("pending", "#F59E0B"), ("approved", "#10B981"), ("flagged", "#EF4444"), ("rejected", "#6B7280")]:
        count = await db.investors.count_documents({"kyc_status": status})
        investor_funnel.append({"status": status.capitalize(), "count": count, "color": color})

    stage_counts = {"leads": 0, "due_diligence": 0, "ic_review": 0, "closing": 0}
    async for deal in db.deals.find():
        ps = deal.get("pipeline_stage") or OLD_DEAL_STAGE_MAP.get(deal.get("stage", ""), "leads")
        if ps in stage_counts:
            stage_counts[ps] += 1

    deal_pipeline = [
        {"stage": "Leads", "key": "leads", "count": stage_counts["leads"], "color": "#6B7280"},
        {"stage": "Due Diligence", "key": "due_diligence", "count": stage_counts["due_diligence"], "color": "#F59E0B"},
        {"stage": "IC Review", "key": "ic_review", "count": stage_counts["ic_review"], "color": "#1B3A6B"},
        {"stage": "Closing", "key": "closing", "count": stage_counts["closing"], "color": "#10B981"},
    ]
    return {"investor_funnel": investor_funnel, "deal_pipeline": deal_pipeline}
