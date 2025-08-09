# app/auth_admin.py
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
import os
import hmac
import hashlib
import base64
import json
from datetime import datetime, timedelta

router = APIRouter()

# Configuration
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
SESSION_DURATION_HOURS = int(os.getenv("SESSION_DURATION_HOURS", "2"))

def authenticate_admin(username: str, password: str) -> bool:
    """Vérifier les identifiants admin"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def create_signed_cookie() -> str:
    """Créer un cookie signé avec seulement la date d'expiration en timestamp UTC"""
    # Créer le payload avec timestamp UTC
    expiry = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    payload = {"exp": int(expiry.timestamp())}  # Timestamp UTC entier
    
    # Encoder en base64
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip('=')
    
    # Créer la signature HMAC
    signature = hmac.new(
        SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    
    # Retourner le cookie signé : payload.signature
    return f"{payload_b64}.{signature_b64}"

def verify_signed_cookie(cookie_value: str) -> bool:
    """Vérifier un cookie signé"""
    if not cookie_value:
        return False
    
    try:
        # Séparer payload et signature
        parts = cookie_value.split('.')
        if len(parts) != 2:
            return False
        
        payload_b64, signature_b64 = parts
        
        # Vérifier la signature
        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).digest()
        expected_signature_b64 = base64.urlsafe_b64encode(expected_signature).decode().rstrip('=')
        
        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            return False
        
        # Décoder le payload
        # Ajouter le padding manquant pour base64
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
            
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        payload = json.loads(payload_json)
        
        # Vérifier l'expiration avec timestamp UTC
        expiry_timestamp = payload["exp"]
        current_timestamp = int(datetime.utcnow().timestamp())
        if current_timestamp > expiry_timestamp:
            return False
        
        return True
        
    except Exception:
        return False

def get_cookie_settings(request: Request, is_delete: bool = False):
    """Déterminer les paramètres de cookie selon l'environnement"""
    # Détecter si on est en production/Vercel
    is_production = request.url.hostname not in ["localhost", "127.0.0.1"]
    is_vercel_preview = "vercel" in str(request.url.hostname).lower()
    
    if is_delete:
        return {
            "httponly": True,
            "secure": is_production or is_vercel_preview,
            "samesite": "none" if is_vercel_preview else "lax",
            "domain": None,
            "max_age": 0,  # Suppression immédiate
            "expires": "Thu, 01 Jan 1970 00:00:00 GMT"  # Date passée
        }
    else:
        return {
            "httponly": True,
            "max_age": SESSION_DURATION_HOURS * 3600,
            "secure": is_production or is_vercel_preview,
            "samesite": "none" if is_vercel_preview else "lax",
            "domain": None
        }

# === Dépendance FastAPI pour l'authentification ===

async def require_admin_auth(request: Request) -> bool:
    """
    Dépendance FastAPI pour vérifier l'authentification admin.
    À utiliser avec Depends() dans les routes protégées.
    """
    auth_token = request.cookies.get("auth_token")
    if not auth_token:
        raise HTTPException(
            status_code=401,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not verify_signed_cookie(auth_token):
        raise HTTPException(
            status_code=401,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return True

# === Routes API ===

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(request: Request, response: Response, creds: LoginRequest):
    if not authenticate_admin(creds.username, creds.password):
        raise HTTPException(status_code=401, detail="Identifiants invalides")
    
    # Créer le cookie signé
    signed_cookie = create_signed_cookie()
    cookie_settings = get_cookie_settings(request)
    
    response.set_cookie(
        key="auth_token",
        value=signed_cookie,
        **cookie_settings
    )
    return {"success": True, "message": "Connexion réussie"}

@router.get("/verify")
async def verify(request: Request, response: Response, _: bool = Depends(require_admin_auth)):
    # Ajouter Cache-Control pour éviter la mise en cache
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return {"valid": True, "username": ADMIN_USERNAME}

@router.post("/logout")
async def logout(request: Request, response: Response):
    cookie_settings = get_cookie_settings(request, is_delete=True)
    response.set_cookie(key="auth_token", value="", **cookie_settings)
    return {"message": "Déconnexion réussie"}

@router.post("/clear-auth")
async def clear_auth(request: Request, response: Response):
    cookie_settings = get_cookie_settings(request, is_delete=True)
    response.set_cookie(key="auth_token", value="", **cookie_settings)
    return {"message": "Authentification nettoyée"}
