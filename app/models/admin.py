from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class AdminRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"

class Admin(BaseModel):
    username: str
    email: str
    password: str  # Sera hashé
    role: AdminRole = AdminRole.ADMIN
    is_active: bool = True
    created_at: datetime = datetime.now()
    last_login: Optional[datetime] = None

class AdminInDB(Admin):
    id: str
    hashed_password: str

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminCreate(BaseModel):
    username: str
    email: str
    password: str
    role: AdminRole = AdminRole.ADMIN

class AdminUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
