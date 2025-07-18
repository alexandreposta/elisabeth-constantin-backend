from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderItem(BaseModel):
    artwork_id: str
    title: str
    price: float

class BuyerInfo(BaseModel):
    email: str
    firstName: str
    lastName: str
    address: str
    city: str
    postalCode: str
    country: str
    phone: Optional[str] = None

class Order(BaseModel):
    items: List[OrderItem]
    buyer_info: BuyerInfo
    total: float
    status: OrderStatus = OrderStatus.PENDING
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class OrderInDB(Order):
    id: str = Field(..., alias="_id")
