import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import (
    User, Product, CartItem, Order, CreditAccount,
    CreditIncreaseRequest, SubscriptionPlan, TokenResponse, MeResponse
)

# App and CORS
app = FastAPI(title="BRACKK API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth setup
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Utilities

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Auth dependencies
class DBUser(BaseModel):
    id: str
    name: str
    email: EmailStr
    password_hash: str
    is_admin: bool = False

async def get_current_user(token: str = Depends(oauth2_scheme)) -> DBUser:
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    doc = db["user"].find_one({"_id": ObjectId(user_id)})
    if not doc:
        raise credentials_exception
    return DBUser(
        id=str(doc["_id"]), name=doc.get("name"), email=doc.get("email"), password_hash=doc.get("password_hash"), is_admin=doc.get("is_admin", False)
    )


# Routes
@app.get("/")
def root():
    return {"status": "ok", "service": "BRACKK API"}

@app.get("/test")
def test_database():
    info = {
        "backend": "running",
        "database": "connected" if db is not None else "not_configured",
    }
    if db is not None:
        info["collections"] = db.list_collection_names()
    return info

# Request models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Auth endpoints
@app.post("/auth/register", response_model=TokenResponse)
def register(user: User):
    if db["user"].find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = user.password_hash if user.password_hash.startswith("$2b$") else hash_password(user.password_hash)
    user_dict = user.model_dump()
    user_dict["password_hash"] = hashed
    user_id = create_document("user", user_dict)
    token = create_access_token({"sub": user_id})
    # create credit account
    if not db["creditaccount"].find_one({"user_id": user_id}):
        create_document("creditaccount", CreditAccount(user_id=user_id).model_dump())
    return TokenResponse(access_token=token)

@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user_doc = db["user"].find_one({"email": body.email})
    if not user_doc:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not verify_password(body.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user_doc["_id"])})
    return TokenResponse(access_token=token)

@app.get("/auth/me", response_model=MeResponse)
async def me(current: DBUser = Depends(get_current_user)):
    return MeResponse(id=current.id, name=current.name, email=current.email)

# Product endpoints
@app.get("/products")
def list_products(limit: int = 50):
    docs = get_documents("product", {}, limit)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

@app.post("/products")
def create_product(product: Product, current: DBUser = Depends(get_current_user)):
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Admins only")
    pid = create_document("product", product)
    return {"id": pid}

# Cart endpoints (basic persisted cart items)
@app.post("/cart/add")
def add_to_cart(item: CartItem, current: DBUser = Depends(get_current_user)):
    if item.user_id != current.id:
        raise HTTPException(status_code=403, detail="Cannot modify another user's cart")
    # upsert style
    existing = db["cartitem"].find_one({"user_id": item.user_id, "product_id": item.product_id})
    if existing:
        db["cartitem"].update_one({"_id": existing["_id"]}, {"$set": {"quantity": item.quantity, "updated_at": datetime.now(timezone.utc)}})
        return {"status": "updated"}
    else:
        cid = create_document("cartitem", item)
        return {"id": cid}

@app.get("/cart")
async def get_cart(current: DBUser = Depends(get_current_user)):
    items = list(db["cartitem"].find({"user_id": current.id}))
    for it in items:
        it["id"] = str(it.pop("_id"))
    return items

# Orders
@app.post("/orders")
def place_order(order: Order, current: DBUser = Depends(get_current_user)):
    if order.user_id != current.id:
        raise HTTPException(status_code=403, detail="Cannot place for another user")
    # check credit
    acct = db["creditaccount"].find_one({"user_id": current.id})
    if not acct:
        raise HTTPException(status_code=400, detail="No credit account")
    remaining = float(acct.get("credit_limit", 0)) - float(acct.get("credit_used", 0))
    if order.total_amount > remaining:
        raise HTTPException(status_code=402, detail="Insufficient credit")
    oid = create_document("order", order)
    # increment credit used
    db["creditaccount"].update_one({"user_id": current.id}, {"$inc": {"credit_used": float(order.total_amount)}, "$set": {"updated_at": datetime.now(timezone.utc)}})
    # clear cart
    db["cartitem"].delete_many({"user_id": current.id})
    return {"id": oid, "status": "placed"}

@app.get("/orders")
async def list_orders(current: DBUser = Depends(get_current_user)):
    docs = list(db["order"].find({"user_id": current.id}).sort("created_at", -1))
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

# Credit
@app.get("/credit")
async def get_credit(current: DBUser = Depends(get_current_user)):
    acct = db["creditaccount"].find_one({"user_id": current.id})
    if not acct:
        acct_id = create_document("creditaccount", CreditAccount(user_id=current.id))
        acct = db["creditaccount"].find_one({"_id": ObjectId(acct_id)})
    acct["id"] = str(acct.pop("_id"))
    return acct

@app.post("/credit/request-increase")
async def request_increase(req: CreditIncreaseRequest, current: DBUser = Depends(get_current_user)):
    if req.user_id != current.id:
        raise HTTPException(status_code=403, detail="Cannot request for another user")
    rid = create_document("creditincreaserequest", req)
    return {"id": rid, "status": "pending"}

# Subscription plans (seed + list)
@app.post("/plans")
def create_plan(plan: SubscriptionPlan, current: DBUser = Depends(get_current_user)):
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Admins only")
    pid = create_document("subscriptionplan", plan)
    return {"id": pid}

@app.get("/plans")
async def list_plans():
    docs = get_documents("subscriptionplan", {}, 20)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return docs

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
