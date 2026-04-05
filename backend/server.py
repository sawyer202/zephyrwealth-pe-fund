from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Annotated
from pydantic import BaseModel
import os
import jwt
import bcrypt
import secrets
from bson import ObjectId

app = FastAPI(title="ZephyrWealth API", version="1.0.0")

# ─── CORS ───────────────────────────────────────────────────────────────────
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Database ────────────────────────────────────────────────────────────────
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# ─── JWT Config ──────────────────────────────────────────────────────────────
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

# ─── Password Helpers ────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def validate_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

# ─── JWT Helpers ─────────────────────────────────────────────────────────────
def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ─── Pydantic Models ─────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: str
    password: str

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

# ─── Seeding ─────────────────────────────────────────────────────────────────
SEED_USERS = [
    {
        "email": "compliance@zephyrwealth.ai",
        "password": "Comply1234!",
        "role": "compliance",
        "name": "Sarah Chen",
        "title": "Chief Compliance Officer",
    },
    {
        "email": "risk@zephyrwealth.ai",
        "password": "Risk1234!",
        "role": "risk",
        "name": "Marcus Webb",
        "title": "Head of Risk",
    },
    {
        "email": "manager@zephyrwealth.ai",
        "password": "Manager1234!",
        "role": "manager",
        "name": "Jonathan Morrow",
        "title": "Fund Manager",
    },
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
    if await db.investors.count_documents({}) == 0:
        await db.investors.insert_many([
            {
                "name": "Harrington & Associates LLC",
                "type": "Corporate Entity",
                "submitted_date": datetime(2025, 1, 15, tzinfo=timezone.utc),
                "risk_rating": "medium",
                "kyc_status": "pending",
                "scorecard_completed": False,
                "country": "Cayman Islands",
                "investment_amount": 5000000,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "name": "Castlebrook Family Office",
                "type": "Family Office",
                "submitted_date": datetime(2025, 2, 3, tzinfo=timezone.utc),
                "risk_rating": "low",
                "kyc_status": "approved",
                "scorecard_completed": True,
                "country": "Bahamas",
                "investment_amount": 12000000,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "name": "Meridian Capital Fund III",
                "type": "Investment Fund",
                "submitted_date": datetime(2025, 2, 18, tzinfo=timezone.utc),
                "risk_rating": "high",
                "kyc_status": "flagged",
                "scorecard_completed": False,
                "country": "British Virgin Islands",
                "investment_amount": 8500000,
                "created_at": datetime.now(timezone.utc),
            },
        ])

    if await db.deals.count_documents({}) == 0:
        await db.deals.insert_many([
            {
                "name": "Nassau Waterfront Development",
                "type": "Real Estate",
                "submitted_date": datetime(2025, 1, 20, tzinfo=timezone.utc),
                "risk_rating": "medium",
                "stage": "due_diligence",
                "scorecard_completed": False,
                "target_return": "18%",
                "deal_size": 25000000,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "name": "Caribbean Logistics Group",
                "type": "Private Equity",
                "submitted_date": datetime(2025, 2, 10, tzinfo=timezone.utc),
                "risk_rating": "low",
                "stage": "term_sheet",
                "scorecard_completed": True,
                "target_return": "22%",
                "deal_size": 15000000,
                "created_at": datetime.now(timezone.utc),
            },
        ])

# ─── Startup ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.login_attempts.create_index(
        "last_attempt", expireAfterSeconds=3600
    )
    await seed_users()
    await seed_demo_data()
    print("✅ ZephyrWealth API ready")

# ─── Health ──────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ZephyrWealth API", "version": "1.0.0"}

# ─── Auth: Login ─────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
async def login(request: Request, response: Response, body: LoginRequest):
    email = body.email.lower().strip()
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{email}"

    # Check lockout
    attempt_doc = await db.login_attempts.find_one({"identifier": identifier})
    if attempt_doc:
        locked_until = attempt_doc.get("locked_until")
        if locked_until and datetime.now(timezone.utc) < locked_until:
            remaining = int(
                (locked_until - datetime.now(timezone.utc)).total_seconds() / 60
            )
            raise HTTPException(
                status_code=429,
                detail=f"Account locked due to too many failed attempts. Try again in {remaining} minute(s).",
            )

    user = await db.users.find_one({"email": email})

    if not user or not verify_password(body.password, user["password_hash"]):
        now = datetime.now(timezone.utc)
        if attempt_doc:
            new_count = attempt_doc.get("failed_count", 0) + 1
            update_data = {"failed_count": new_count, "last_attempt": now}
            if new_count >= 5:
                update_data["locked_until"] = now + timedelta(minutes=15)
            await db.login_attempts.update_one(
                {"identifier": identifier}, {"$set": update_data}
            )
        else:
            await db.login_attempts.insert_one(
                {"identifier": identifier, "failed_count": 1, "last_attempt": now}
            )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Clear attempts on success
    await db.login_attempts.delete_one({"identifier": identifier})

    user_id = str(user["_id"])
    access_token = create_access_token(user_id, user["email"], user["role"])
    refresh_token = create_refresh_token(user_id)

    response.set_cookie(
        key="access_token", value=access_token,
        httponly=True, secure=False, samesite="lax", max_age=28800, path="/"
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token,
        httponly=True, secure=False, samesite="lax", max_age=604800, path="/"
    )

    await db.audit_logs.insert_one({
        "user_id": user_id,
        "action": "login",
        "target_id": None,
        "target_type": "auth",
        "timestamp": datetime.now(timezone.utc),
        "notes": f"Login from {client_ip}",
    })

    return {
        "id": user_id,
        "email": user["email"],
        "role": user["role"],
        "name": user.get("name", ""),
        "title": user.get("title", ""),
    }

# ─── Auth: Logout ─────────────────────────────────────────────────────────────
@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

# ─── Auth: Me ────────────────────────────────────────────────────────────────
@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ─── Auth: Refresh ───────────────────────────────────────────────────────────
@app.post("/api/auth/refresh")
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
        response.set_cookie(
            key="access_token", value=new_token,
            httponly=True, secure=False, samesite="lax", max_age=28800, path="/"
        )
        return {"message": "Token refreshed"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# ─── Dashboard: Stats ────────────────────────────────────────────────────────
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    total_investors = await db.investors.count_documents({})
    pending_kyc = await db.investors.count_documents({"kyc_status": "pending"})
    deals_in_pipeline = await db.deals.count_documents({})
    flagged_investors = await db.investors.count_documents({"risk_rating": "high"})
    flagged_deals = await db.deals.count_documents({"risk_rating": "high"})
    return {
        "total_investors": total_investors,
        "pending_kyc": pending_kyc,
        "deals_in_pipeline": deals_in_pipeline,
        "flagged_items": flagged_investors + flagged_deals,
    }

# ─── Investors ───────────────────────────────────────────────────────────────
@app.get("/api/investors")
async def get_investors(current_user: dict = Depends(get_current_user)):
    investors = []
    async for doc in db.investors.find().sort("submitted_date", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("submitted_date"), datetime):
            doc["submitted_date"] = doc["submitted_date"].isoformat()
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        investors.append(doc)
    return investors

# ─── Deals ───────────────────────────────────────────────────────────────────
@app.get("/api/deals")
async def get_deals(current_user: dict = Depends(get_current_user)):
    deals = []
    async for doc in db.deals.find().sort("submitted_date", -1):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("submitted_date"), datetime):
            doc["submitted_date"] = doc["submitted_date"].isoformat()
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        deals.append(doc)
    return deals

# ─── Audit Logs ───────────────────────────────────────────────────────────────
@app.get("/api/audit-logs")
async def get_audit_logs(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("compliance", "manager"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    logs = []
    async for doc in db.audit_logs.find().sort("timestamp", -1).limit(100):
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if isinstance(doc.get("timestamp"), datetime):
            doc["timestamp"] = doc["timestamp"].isoformat()
        logs.append(doc)
    return logs
