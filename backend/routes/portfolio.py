from fastapi import APIRouter, Depends

from database import db
from utils import get_current_user, normalize_deal

router = APIRouter(tags=["portfolio"])


@router.get("/api/portfolio/summary")
async def get_portfolio_summary(current_user: dict = Depends(get_current_user)):
    deals = []
    async for doc in db.deals.find():
        deals.append(normalize_deal(doc))

    total_portfolio_value = sum(d.get("entry_valuation", 0) or 0 for d in deals)
    active_investments = sum(1 for d in deals if d.get("pipeline_stage") in ("ic_review", "closing"))

    total_val_for_irr = sum((d.get("entry_valuation", 0) or 0) for d in deals)
    weighted_irr_sum = sum((d.get("expected_irr", 0) or 0) * (d.get("entry_valuation", 0) or 0) for d in deals)
    weighted_avg_irr = (weighted_irr_sum / total_val_for_irr) if total_val_for_irr > 0 else 0

    total_deals = len(deals)
    exception_deals = sum(1 for d in deals if d.get("mandate_status") == "Exception")
    mandate_exception_rate = (exception_deals / total_deals * 100) if total_deals > 0 else 0

    sector_map: dict = {}
    for d in deals:
        sector = d.get("sector") or "Unknown"
        val = d.get("entry_valuation", 0) or 0
        if sector not in sector_map:
            sector_map[sector] = {"name": sector, "value": 0, "count": 0}
        sector_map[sector]["value"] += val
        sector_map[sector]["count"] += 1

    geo_map: dict = {}
    for d in deals:
        geo = d.get("geography") or "Unknown"
        val = d.get("entry_valuation", 0) or 0
        if geo not in geo_map:
            geo_map[geo] = {"name": geo, "value": 0, "count": 0}
        geo_map[geo]["value"] += val
        geo_map[geo]["count"] += 1

    irr_distribution = sorted([
        {
            "id": d.get("id", ""),
            "name": d.get("company_name", ""),
            "irr": d.get("expected_irr", 0) or 0,
            "valuation": d.get("entry_valuation", 0) or 0,
            "mandate_status": d.get("mandate_status", "In Mandate"),
        }
        for d in deals
    ], key=lambda x: x["irr"], reverse=True)

    stage_map: dict = {"leads": 0, "due_diligence": 0, "ic_review": 0, "closing": 0}
    for d in deals:
        ps = d.get("pipeline_stage", "leads")
        if ps in stage_map:
            stage_map[ps] += d.get("entry_valuation", 0) or 0
    pipeline_stage_value = [
        {"stage": "Leads", "key": "leads", "value": stage_map["leads"]},
        {"stage": "Due Diligence", "key": "due_diligence", "value": stage_map["due_diligence"]},
        {"stage": "IC Review", "key": "ic_review", "value": stage_map["ic_review"]},
        {"stage": "Closing", "key": "closing", "value": stage_map["closing"]},
    ]

    mandate = await db.fund_mandate.find_one({})
    holdings = []
    for d in deals:
        ms = d.get("mandate_status", "In Mandate")
        irr_val = d.get("expected_irr", 0) or 0
        if mandate:
            in_irr = mandate.get("irr_min", 0) <= irr_val <= mandate.get("irr_max", 100)
        else:
            in_irr = True
        if ms in ("In Mandate", "Exception Cleared") and in_irr:
            health_score = "Good"
        elif ms == "Exception":
            health_score = "Review"
        else:
            health_score = "Poor"
        holdings.append({
            "id": d.get("id", ""),
            "company_name": d.get("company_name", ""),
            "sector": d.get("sector", ""),
            "geography": d.get("geography", ""),
            "entity_type": d.get("entity_type", "IBC"),
            "pipeline_stage": d.get("pipeline_stage", "leads"),
            "entry_valuation": d.get("entry_valuation", 0) or 0,
            "expected_irr": irr_val,
            "mandate_status": ms,
            "health_score": health_score,
        })

    class_capital: dict = {"A": {"called": 0.0, "uncalled": 0.0}, "B": {"called": 0.0, "uncalled": 0.0}, "C": {"called": 0.0, "uncalled": 0.0}}
    async for inv in db.investors.find({"committed_capital": {"$gt": 0}}):
        cls = inv.get("share_class", "")
        if cls in class_capital:
            class_capital[cls]["called"] += inv.get("capital_called", 0) or 0
            class_capital[cls]["uncalled"] += inv.get("capital_uncalled", 0) or (inv.get("committed_capital", 0) - (inv.get("capital_called", 0) or 0))
    capital_by_class = [{"class_label": f"Class {k}", "called": round(v["called"], 2), "uncalled": round(v["uncalled"], 2)} for k, v in class_capital.items()]

    return {
        "kpis": {
            "total_portfolio_value": total_portfolio_value,
            "active_investments": active_investments,
            "weighted_avg_irr": round(weighted_avg_irr, 2),
            "mandate_exception_rate": round(mandate_exception_rate, 1),
        },
        "charts": {
            "sector_allocation": list(sector_map.values()),
            "geography_allocation": list(geo_map.values()),
            "irr_distribution": irr_distribution,
            "pipeline_stage_value": pipeline_stage_value,
            "capital_by_class": capital_by_class,
        },
        "holdings": holdings,
    }
