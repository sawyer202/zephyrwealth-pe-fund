from pydantic import BaseModel
from typing import Optional, List


class LoginRequest(BaseModel):
    email: str
    password: str


class AddressModel(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str


class UBODeclaration(BaseModel):
    name: str
    nationality: str
    ownership_percentage: float


class InvestorCreateRequest(BaseModel):
    entity_type: str
    legal_name: str
    dob: Optional[str] = None
    nationality: str
    residence_country: str
    email: str
    phone: str
    address: AddressModel
    net_worth: float
    annual_income: float
    source_of_wealth: str
    investment_experience: str
    classification: str
    ubo_declarations: Optional[List[UBODeclaration]] = []
    accredited_declaration: Optional[bool] = False
    terms_accepted: bool


class DecisionRequest(BaseModel):
    decision: str
    notes: Optional[str] = None


class DealCreateRequest(BaseModel):
    company_name: str
    sector: str
    geography: str
    asset_class: str
    expected_irr: float
    entry_valuation: float
    entity_type: str  # IBC | ICON


class DealStageUpdate(BaseModel):
    stage: str
    override_note: Optional[str] = None


# ─── Phase 5 Models ──────────────────────────────────────────────────────────

class PlacementAgentCreate(BaseModel):
    agent_name: str
    company_name: str
    email: str
    phone: str
    bank_name: str
    bank_account_number: str
    swift_code: str
    vat_registered: bool
    vat_number: Optional[str] = None


class PlacementAgentUpdate(BaseModel):
    agent_name: Optional[str] = None
    company_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    swift_code: Optional[str] = None
    vat_registered: Optional[bool] = None
    vat_number: Optional[str] = None


class FundParticipationUpdate(BaseModel):
    share_class: str
    committed_capital: float
    placement_agent_id: Optional[str] = None
    deal_associations: Optional[List[str]] = []


class CapitalCallCreate(BaseModel):
    call_name: str
    call_type: str
    target_classes: List[str]
    call_percentage: float
    due_date: str
    deal_id: Optional[str] = None


class LineItemStatusUpdate(BaseModel):
    status: str


class TrailerFeeGenerateRequest(BaseModel):
    year: int
    agent_ids: Optional[List[str]] = None
