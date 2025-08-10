from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class NewsletterSubscription(BaseModel):
    email: EmailStr
    subscribed_at: Optional[datetime] = None
    is_active: bool = True
    unsubscribe_token: Optional[str] = None

class NewsletterSubscriptionInDB(NewsletterSubscription):
    id: str = Field(..., alias="_id")

class NewsletterUnsubscribe(BaseModel):
    token: str
