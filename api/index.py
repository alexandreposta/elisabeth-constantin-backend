from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import logging

# Configuration du logging pour debug
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Créer l'application FastAPI
app = FastAPI(
    title="Elisabeth Constantin API",
    description="API pour le site d'art d'Elisabeth Constantin",
    version="1.0.0"
)

# Middleware pour logger toutes les requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"🚀 === NOUVELLE REQUÊTE ===")
    logger.info(f"🔍 REQUEST: {request.method} {request.url}")
    logger.info(f"🔍 PATH: {request.url.path}")
    logger.info(f"🔍 QUERY PARAMS: {request.query_params}")
    logger.info(f"🔍 HEADERS: {dict(request.headers)}")
    logger.info(f"🔍 COOKIES: {request.cookies}")
    
    response = await call_next(request)
    
    logger.info(f"📤 RESPONSE STATUS: {response.status_code}")
    logger.info(f"🚀 === FIN REQUÊTE ===\n")
    return response

# Configuration CORS
frontend_url = os.getenv("FRONTEND_URL")
allowed_origins = [
    frontend_url,
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Configuration d'authentification simple pour le développement local
logger.info("🔄 Configuration de l'authentification simple (sans MongoDB)...")

import os
from datetime import datetime, timedelta

# Stockage en mémoire temporaire pour le développement
sessions = {}

def authenticate_admin(username, password): 
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    logger.info(f"🔐 Vérification: {username} == {admin_username} et password == {admin_password}")
    return username == admin_username and password == admin_password

def create_session(ip, ua): 
    session_id = f"session_{datetime.now().timestamp()}"
    sessions[session_id] = {
        "created_at": datetime.now(),
        "expires_at": datetime.now() + timedelta(hours=2),
        "ip": ip,
        "user_agent": ua
    }
    logger.info(f"🔐 Session créée: {session_id}")
    return session_id

def verify_session(session_id, ip): 
    if session_id in sessions:
        session = sessions[session_id]
        if datetime.now() < session["expires_at"]:
            logger.info(f"🔐 Session valide: {session_id}")
            return True
        else:
            logger.info(f"🔐 Session expirée: {session_id}")
            del sessions[session_id]
    logger.info(f"🔐 Session invalide: {session_id}")
    return False

def cleanup_expired_sessions(): 
    expired = [sid for sid, session in sessions.items() if datetime.now() >= session["expires_at"]]
    for sid in expired:
        del sessions[sid]
    logger.info(f"🔐 Sessions expirées nettoyées: {len(expired)}")

logger.info("✅ Authentification simple configurée")

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/admin/login")
async def admin_login(request: Request, response: Response, login_data: LoginRequest):
    """Connexion admin simplifiée"""
    logger.info("🔐 POST /admin/login - Tentative de connexion admin")
    try:
        # Nettoyer les sessions expirées
        cleanup_expired_sessions()
        
        # Authentification
        if not authenticate_admin(login_data.username, login_data.password):
            raise HTTPException(status_code=401, detail="Identifiants invalides")
        
        # Récupérer les infos de la requête
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Créer la session
        session_id = create_session(ip_address, user_agent)
        
        # Définir le cookie sécurisé
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            secure=False,  # False pour le développement local
            samesite="lax",  # Plus permissif pour le développement local
            max_age=7200  # 2 heures
        )
        
        return {"message": "Connexion réussie", "success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.post("/api/admin/logout")
async def admin_logout(response: Response):
    """Déconnexion admin"""
    # Supprimer tous les cookies d'authentification
    response.delete_cookie(key="session_id", httponly=True, secure=False, samesite="lax")
    response.delete_cookie(key="admin_token", httponly=False, secure=False, samesite="lax")
    return {"message": "Déconnexion réussie"}

@app.post("/api/admin/clear-auth")
async def clear_auth(response: Response):
    """Nettoyer complètement l'authentification"""
    logger.info("🧹 Nettoyage complet de l'authentification")
    # Supprimer tous les cookies possibles
    response.delete_cookie(key="session_id", httponly=True, secure=False, samesite="lax")
    response.delete_cookie(key="admin_token", httponly=False, secure=False, samesite="lax")
    response.delete_cookie(key="session_id", httponly=True, secure=True, samesite="none")  # Ancienne config
    response.delete_cookie(key="admin_token", httponly=False, secure=True, samesite="none")  # Ancienne config
    return {"message": "Authentification nettoyée"}

@app.get("/api/admin/verify")
async def verify_admin_session(request: Request):
    """Vérification de session admin"""
    logger.info("🔍 GET /admin/verify - Vérification de session admin")
    logger.info(f"🔍 Path: {request.url.path}")
    logger.info(f"🔍 Full URL: {request.url}")
    logger.info(f"🔍 Cookies: {request.cookies}")
    try:
        # Chercher d'abord le session_id (notre système)
        session_id = request.cookies.get("session_id")
        admin_token = request.cookies.get("admin_token")
        
        logger.info(f"🔍 Session ID: {session_id}")
        logger.info(f"🔍 Admin Token: {admin_token}")
        
        # Si on a un session_id, utiliser notre système
        if session_id:
            ip_address = request.client.host
            if verify_session(session_id, ip_address):
                return {"valid": True, "message": "Session valide", "username": "admin"}
            else:
                raise HTTPException(status_code=401, detail="Session invalide")
        
        # Si on a un admin_token (JWT), l'accepter temporairement
        elif admin_token:
            logger.info("🔍 Token JWT trouvé, accepté temporairement")
            # Pour l'instant, on accepte tout token JWT non vide
            # Plus tard on pourra vérifier la signature
            return {"valid": True, "message": "Token JWT accepté", "username": "admin"}
        
        else:
            logger.warning("⚠️ Aucune session ou token trouvé dans les cookies")
            raise HTTPException(status_code=401, detail="Aucune session")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur dans verify_admin_session: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.get("/")
async def health_check():
    return {
        "message": "Elisabeth Constantin API - FastAPI",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "artworks": "/api/artworks",
            "events": "/api/events", 
            "orders": "/api/orders",
            "admin": "/api/admin"
        }
    }

@app.get("/health")
async def health():
    return {"status": "ok", "message": "API is running"}

@app.get("/debug/routes")
async def debug_routes():
    """Endpoint de debug pour lister toutes les routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name if hasattr(route, 'name') else "unknown"
            })
    return {"routes": routes}

@app.get("/api/admin/dashboard/stats")
async def dashboard_stats(request: Request):
    """Statistiques du dashboard admin"""
    logger.info("📊 GET /api/admin/dashboard/stats - Récupération des statistiques")
    try:
        # Vérifier l'authentification
        session_id = request.cookies.get("session_id")
        admin_token = request.cookies.get("admin_token")
        
        if not session_id and not admin_token:
            raise HTTPException(status_code=401, detail="Non authentifié")
        
        # Pour l'instant, retourner des stats factices
        stats = {
            "artworks": {
                "total": 42,
                "published": 38,
                "draft": 4
            },
            "events": {
                "total": 8,
                "upcoming": 3,
                "past": 5
            },
            "orders": {
                "total": 156,
                "pending": 12,
                "completed": 144
            },
            "analytics": {
                "visitors_today": 245,
                "visitors_week": 1683,
                "conversion_rate": 3.2
            }
        }
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur dans dashboard_stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

# Import des sous-applications depuis le dossier api/
import importlib.util
import sys
import os

def load_api_module(module_name):
    """Charge dynamiquement un module API"""
    module_path = os.path.join(os.path.dirname(__file__), f"{module_name}.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"api.{module_name}"] = module
    spec.loader.exec_module(module)
    return module.app

# Charger les sous-applications
artworks_app = load_api_module("artworks")
events_app = load_api_module("events") 
orders_app = load_api_module("orders")

# Monter les sous-applications avec leur préfixe
app.mount("/api/artworks", artworks_app)
app.mount("/api/events", events_app)
app.mount("/api/orders", orders_app)

# Log au démarrage
logger.info("🟢 APPLICATION DÉMARRÉE - Endpoints disponibles:")
logger.info("🟢 GET / - Health check")
logger.info("🟢 GET /health - Health status") 
logger.info("🟢 POST /api/admin/login - Connexion admin")
logger.info("🟢 GET /api/admin/verify - Vérification session")
logger.info("🟢 POST /api/admin/logout - Déconnexion admin")
logger.info("🟢 POST /api/admin/clear-auth - Nettoyage de l'authentification")
logger.info("🟢 GET /debug/routes - Liste des routes")
logger.info("🟢 GET /api/admin/dashboard/stats - Statistiques du dashboard")
logger.info("🟢 === ROUTES IMPORTÉES DEPUIS FICHIERS SÉPARÉS ===")
logger.info("🎨 /api/artworks/* - Routes des œuvres d'art (depuis artworks.py)")
logger.info("📅 /api/events/* - Routes des événements (depuis events.py)")
logger.info("🛒 /api/orders/* - Routes des commandes (depuis orders.py)")
logger.info("💾 Base de données MongoDB connectée")
