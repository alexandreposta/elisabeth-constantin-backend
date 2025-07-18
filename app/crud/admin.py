from pymongo import MongoClient
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from app.models.admin import Admin, AdminInDB, AdminCreate, AdminUpdate
from app.database import get_database

# Configuration de sécurité
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

def get_admin_by_username(username: str):
    db = get_database()
    collection = db["admins"]
    admin = collection.find_one({"username": username})
    return admin

def get_admin_by_id(admin_id: str):
    db = get_database()
    collection = db["admins"]
    from bson import ObjectId
    admin = collection.find_one({"_id": ObjectId(admin_id)})
    return admin

def create_admin(admin_data: AdminCreate):
    db = get_database()
    collection = db["admins"]
    
    # Vérifier si l'admin existe déjà
    if collection.find_one({"username": admin_data.username}):
        raise ValueError("Un admin avec ce nom d'utilisateur existe déjà")
    
    if collection.find_one({"email": admin_data.email}):
        raise ValueError("Un admin avec cet email existe déjà")
    
    # Hasher le mot de passe
    hashed_password = get_password_hash(admin_data.password)
    
    admin_dict = {
        "username": admin_data.username,
        "email": admin_data.email,
        "hashed_password": hashed_password,
        "role": admin_data.role,
        "is_active": True,
        "created_at": datetime.now(),
        "last_login": None
    }
    
    result = collection.insert_one(admin_dict)
    return str(result.inserted_id)

def authenticate_admin(username: str, password: str):
    admin = get_admin_by_username(username)
    if not admin:
        return False
    if not verify_password(password, admin["hashed_password"]):
        return False
    return admin

def update_last_login(username: str):
    db = get_database()
    collection = db["admins"]
    collection.update_one(
        {"username": username},
        {"$set": {"last_login": datetime.now()}}
    )

def get_all_admins():
    db = get_database()
    collection = db["admins"]
    admins = list(collection.find({}))
    return admins

def update_admin(admin_id: str, admin_data: AdminUpdate):
    db = get_database()
    collection = db["admins"]
    from bson import ObjectId
    
    update_data = {}
    if admin_data.email is not None:
        update_data["email"] = admin_data.email
    if admin_data.role is not None:
        update_data["role"] = admin_data.role
    if admin_data.is_active is not None:
        update_data["is_active"] = admin_data.is_active
    
    if update_data:
        result = collection.update_one(
            {"_id": ObjectId(admin_id)},
            {"$set": update_data}
        )
        return result.modified_count
    return 0
