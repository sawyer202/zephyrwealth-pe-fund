import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from bson import ObjectId

from database import db
from utils import (
    get_current_user, create_access_token, create_refresh_token,
    verify_password, JWT_SECRET, JWT_ALGORITHM,
)
from models import LoginRequest

import jwt

router = APIRouter(tags=["auth"])


@router.post("/api/auth/login")
async def login(request: Request, response: Response, body: LoginRequest):
    email = body.email.lower().strip()
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{email}"
    attempt_doc = await db.login_attempts.find_one({"identifier": identifier})
    if attempt_doc:
        locked_until = attempt_doc.get("locked_until")
        if locked_until and datetime.now(timezone.utc) < locked_until:
            remaining = int((locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
            raise HTTPException(status_code=429, detail=f"Account locked. Try again in {remaining} minute(s).")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        now = datetime.now(timezone.utc)
        if attempt_doc:
            nc = attempt_doc.get("failed_count", 0) + 1
            upd = {"failed_count": nc, "last_attempt": now}
            if nc >= 5:
                upd["locked_until"] = now + timedelta(minutes=15)
            await db.login_attempts.update_one({"identifier": identifier}, {"$set": upd})
        else:
            await db.login_attempts.insert_one({"identifier": identifier, "failed_count": 1, "last_attempt": now})
        raise HTTPException(status_code=401, detail="Invalid email or password")
    await db.login_attempts.delete_one({"identifier": identifier})
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, user["email"], user["role"])
    refresh_token = create_refresh_token(user_id)
    cookie_secure = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=cookie_secure, samesite="lax", max_age=28800, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=cookie_secure, samesite="lax", max_age=604800, path="/")
    await db.audit_logs.insert_one({"user_id": user_id, "action": "login", "target_id": None, "target_type": "auth", "timestamp": datetime.now(timezone.utc), "notes": f"Login from {client_ip}"})
    return {"id": user_id, "email": user["email"], "role": user["role"], "name": user.get("name", ""), "title": user.get("title", "")}


@router.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}


@router.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/api/auth/refresh")
async def refresh_token_endpoint(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user_id = str(user["_id"])
        new_token = create_access_token(user_id, user["email"], user["role"])
        cookie_secure = os.environ.get("COOKIE_SECURE", "true").lower() == "true"
        response.set_cookie(key="access_token", value=new_token, httponly=True, secure=cookie_secure, samesite="lax", max_age=28800, path="/")
        return {"message": "Token refreshed"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
