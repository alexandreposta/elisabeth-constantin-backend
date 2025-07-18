"""
Système d'authentification ultra-simple avec admin unique en variables d'environnement
"""
import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from app.database import get_database

# Configuration depuis les variables d'environnement
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SESSION_DURATION_HOURS = int(os.getenv("SESSION_DURATION_HOURS", "2"))

def authenticate_admin(username: str, password: str) -> bool:
    """Authentifie l'admin unique via les variables d'environnement"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def generate_session_id() -> str:
    """Génère un ID de session sécurisé"""
    return secrets.token_urlsafe(32)

def hash_session_id(session_id: str) -> str:
    """Hash l'ID de session pour stockage sécurisé"""
    return hashlib.sha256(session_id.encode()).hexdigest()

def create_session(ip_address: str, user_agent: str) -> str:
    """Crée une session simple en MongoDB"""
    db = get_database()
    
    # Générer un ID de session unique
    session_id = generate_session_id()
    hashed_id = hash_session_id(session_id)
    
    # Calculer l'expiration
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_DURATION_HOURS)
    
    # Créer la session en DB
    session_data = {
        "session_id": hashed_id,
        "username": ADMIN_USERNAME,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "is_active": True,
        "last_activity": datetime.utcnow()
    }
    
    # Nettoyer les anciennes sessions expirées
    db.admin_sessions.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    
    # Insérer la nouvelle session
    db.admin_sessions.insert_one(session_data)
    
    # Logger la connexion
    log_admin_activity("LOGIN", ip_address, user_agent, "Successful login")
    
    return session_id  # Retourner l'ID non-hashé pour le cookie

def verify_session(session_id: str, ip_address: str) -> bool:
    """Vérifie une session simple"""
    if not session_id:
        return False
        
    db = get_database()
    hashed_id = hash_session_id(session_id)
    
    # Chercher la session
    session = db.admin_sessions.find_one({
        "session_id": hashed_id,
        "is_active": True,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not session:
        return False
    
    # Mettre à jour la dernière activité
    db.admin_sessions.update_one(
        {"session_id": hashed_id},
        {"$set": {"last_activity": datetime.utcnow()}}
    )
    
    return True

def invalidate_session(session_id: str):
    """Invalide une session (logout)"""
    if not session_id:
        return
        
    db = get_database()
    hashed_id = hash_session_id(session_id)
    
    # Marquer comme inactive
    db.admin_sessions.update_one(
        {"session_id": hashed_id},
        {"$set": {"is_active": False}}
    )
    
    log_admin_activity("LOGOUT", "", "", "Successful logout")

def log_admin_activity(action: str, ip_address: str, user_agent: str, details: str):
    """Log simple des activités admin"""
    db = get_database()
    
    log_entry = {
        "username": ADMIN_USERNAME,
        "action": action,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "details": details,
        "timestamp": datetime.utcnow()
    }
    
    db.admin_activity_logs.insert_one(log_entry)

def cleanup_expired_sessions():
    """Nettoie les sessions expirées (optionnel)"""
    db = get_database()
    result = db.admin_sessions.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    return result.deleted_count
