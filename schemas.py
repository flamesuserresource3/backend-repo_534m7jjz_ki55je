"""
Database Schemas for BRACKK

Each Pydantic model corresponds to a MongoDB collection. The collection name is the lowercase of the class name.
Example: class User -> collection "user"
"""
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime

# Core domain models

class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    password_hash: str = Field(..., description="Hashed password")
    address: Optional[str] = Field(None, description="Primary delivery address")
    is_active: bool = Field(True, description="Whether user is active")
    is_admin: bool = Field(False, description="Admin flag")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in INR")
    image_url: Optional[str] = Field(None, description="Image URL")
    category: Optional[str] = Field(None, description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

class CartItem(BaseModel):
    user_id: str = Field(..., description="User ObjectId as string")
    product_id: str = Field(..., description="Product ObjectId as string")
    quantity: int = Field(1, ge=1, description="Quantity of the product")

class Order(BaseModel):
    user_id: str = Field(..., description="User ObjectId as string")
    items: List[CartItem] = Field(..., description="Items in the order")
    total_amount: float = Field(..., ge=0, description="Total amount in INR")
    status: str = Field("placed", description="Order status")

class CreditAccount(BaseModel):
    user_id: str = Field(..., description="User ObjectId as string")
    credit_limit: float = Field(5000.0, ge=0)
    credit_used: float = Field(0.0, ge=0)
    billing_day: int = Field(1, ge=1, le=28, description="Day of month for billing")

class CreditIncreaseRequest(BaseModel):
    user_id: str
    current_limit: float
    requested_limit: float
    status: str = Field("pending")

class SubscriptionPlan(BaseModel):
    name: str
    price_per_month: float
    features: List[str] = []
    is_active: bool = True

# Response helpers
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MeResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    address: Optional[str] = None
    is_admin: bool = False

