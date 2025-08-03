# app/auth_admin.py
from fastapi import APIRouter, Request, Response, HTTPException
from pydantic import BaseModel
import os
import secrets
from datetime import datetime, timedelta

router = APIRouter()

# Configuration
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SESSION_DURATION_SECONDS = 2 * 60 * 60  # 2 heures

# Sessions en mémoire
_sessions = {}

def authenticate_admin(username: str, password: str) -> bool:
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def create_session() -> str:
    session_id = secrets.token_urlsafe(32)
    _sessions[session_id] = datetime.utcnow() + timedelta(seconds=SESSION_DURATION_SECONDS)
    return session_id

def verify_session(session_id: str) -> bool:
    if not session_id or session_id not in _sessions:
        return False
    if datetime.utcnow() > _sessions[session_id]:
        _sessions.pop(session_id, None)
        return False
    return True

def invalidate_session(session_id: str):
    _sessions.pop(session_id, None)

# === Routes API ===

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: Request, response: Response, creds: LoginRequest):
    if not authenticate_admin(creds.username, creds.password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    session_id = create_session()
    
    # Détecter si on est en production
    is_production = request.url.hostname not in ["localhost", "127.0.0.1"]
    
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=SESSION_DURATION_SECONDS,
        secure=is_production,  # HTTPS en production seulement
        samesite="lax",
        domain=None  # Permet cross-domain
    )
    return {"success": True, "message": "Connexion réussie"}

@router.get("/verify")
async def verify(request: Request):
    session_id = request.cookies.get("session_id")
    if not verify_session(session_id):
        raise HTTPException(status_code=401, detail="Session invalide")
    return {"valid": True}

@router.post("/logout")
async def logout(request: Request, response: Response):
    session_id = request.cookies.get("session_id")
    if session_id:
        invalidate_session(session_id)
    response.delete_cookie("session_id")
    return {"message": "Déconnexion réussie"}
