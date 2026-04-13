"""
Phase 6 — Investor Portal Authentication
Completely separate from back-office auth. Uses investor_token cookie + INVESTOR_JWT_SECRET.
"""
import os
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from bson import ObjectId

from database import db
from utils import hash_password, verify_password

router = APIRouter(tags=["portal-auth"])

# ─── Secrets & Config ────────────────────────────────────────────────────────
INVESTOR_JWT_SECRET = os.environ["INVESTOR_JWT_SECRET"]
JWT_ALGORITHM = "HS256"
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
TOKEN_EXPIRE_HOURS = 8


# ─── Token helpers ────────────────────────────────────────────────────────────
def create_investor_token(user_id: str, investor_id: str, email: str) -> str:
    return jwt.encode(
        {
            "sub": user_id,
            "investor_id": investor_id,
            "email": email,
            "role": "investor",
            "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
            "type": "investor_access",
        },
        INVESTOR_JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


async def get_current_investor(request: Request) -> dict:
    token = request.cookies.get("investor_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, INVESTOR_JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "investor_access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.investor_users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ─── Request models ───────────────────────────────────────────────────────────
class InvestorLoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CreatePortalAccountRequest(BaseModel):
    investor_id: str
    email: str
    temp_password: str


# ─── Endpoints ────────────────────────────────────────────────────────────────
@router.post("/api/portal/auth/login")
async def portal_login(body: InvestorLoginRequest, response: Response):
    user = await db.investor_users.find_one({"email": body.email.lower().strip()})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(user["_id"])
    investor_id = user.get("investor_id", "")
    token = create_investor_token(user_id, investor_id, user["email"])

    await db.investor_users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc)}},
    )

    response.set_cookie(
        key="investor_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=TOKEN_EXPIRE_HOURS * 3600,
        path="/",
    )

    return {
        "id": user_id,
        "investor_id": investor_id,
        "email": user["email"],
        "name": user.get("name", ""),
        "role": "investor",
        "first_login": user.get("first_login", False),
    }


@router.post("/api/portal/auth/logout")
async def portal_logout(response: Response):
    response.delete_cookie("investor_token", path="/")
    return {"message": "Logged out"}


@router.get("/api/portal/auth/me")
async def portal_me(current_investor: dict = Depends(get_current_investor)):
    return current_investor


@router.post("/api/portal/auth/change-password")
async def portal_change_password(
    body: ChangePasswordRequest,
    current_investor: dict = Depends(get_current_investor),
):
    new = body.new_password
    if len(new) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if not any(c.isupper() for c in new):
        raise HTTPException(400, "Password must contain at least one uppercase letter")
    if not any(c.isdigit() for c in new):
        raise HTTPException(400, "Password must contain at least one number")

    user = await db.investor_users.find_one({"_id": ObjectId(current_investor["_id"])})
    if not user:
        raise HTTPException(404, "User not found")
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")

    await db.investor_users.update_one(
        {"_id": ObjectId(current_investor["_id"])},
        {"$set": {"password_hash": hash_password(new), "first_login": False}},
    )
    return {"message": "Password changed successfully"}


@router.post("/api/portal/admin/create-account")
async def create_portal_account(body: CreatePortalAccountRequest, request: Request):
    """Compliance Officer creates a portal account for an investor."""
    from utils import get_current_user
    try:
        bo_user = await get_current_user(request)
    except HTTPException:
        raise HTTPException(401, "Back-office authentication required")
    if bo_user.get("role") != "compliance":
        raise HTTPException(403, "Compliance role required")

    # Check if investor exists
    try:
        inv_oid = ObjectId(body.investor_id)
    except Exception:
        raise HTTPException(400, "Invalid investor ID")
    investor = await db.investors.find_one({"_id": inv_oid})
    if not investor:
        raise HTTPException(404, "Investor not found")

    # Idempotency: already has an account?
    existing = await db.investor_users.find_one({"investor_id": body.investor_id})
    if existing:
        raise HTTPException(409, "Portal account already exists for this investor")

    # Email uniqueness
    email_lower = body.email.lower().strip()
    if await db.investor_users.find_one({"email": email_lower}):
        raise HTTPException(409, "Email already in use by another portal account")

    inv_name = investor.get("legal_name") or investor.get("name", "")
    result = await db.investor_users.insert_one({
        "investor_id": body.investor_id,
        "email": email_lower,
        "password_hash": hash_password(body.temp_password),
        "name": inv_name,
        "role": "investor",
        "first_login": True,
        "created_at": datetime.now(timezone.utc),
        "last_login": None,
    })
    return {
        "message": f"Portal access created for {inv_name}",
        "user_id": str(result.inserted_id),
        "email": email_lower,
        "investor_id": body.investor_id,
    }


@router.get("/api/portal/admin/account-status/{investor_id}")
async def portal_account_status(investor_id: str, request: Request):
    """Check if a portal account exists for a given investor (Compliance only)."""
    from utils import get_current_user
    try:
        bo_user = await get_current_user(request)
    except HTTPException:
        raise HTTPException(401, "Back-office authentication required")
    if bo_user.get("role") != "compliance":
        raise HTTPException(403, "Compliance role required")

    acc = await db.investor_users.find_one({"investor_id": investor_id})
    if acc:
        return {"has_account": True, "email": acc.get("email", ""), "created_at": acc.get("created_at", "").isoformat() if acc.get("created_at") else None}
    return {"has_account": False}
