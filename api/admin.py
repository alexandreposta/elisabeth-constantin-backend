from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.auth_simple import authenticate_admin, create_session, verify_session, cleanup_sessions

# Créer l'app FastAPI
app = FastAPI()

# Configuration CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
allowed_origins = [
    frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://elisabeth-constantin.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/login")
async def admin_login(request: Request, response: Response, login_data: LoginRequest):
    """Connexion admin simplifiée"""
    try:
        # Nettoyer les sessions expirées
        cleanup_sessions()
        
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
            secure=True,
            samesite="none",
            max_age=7200  # 2 heures
        )
        
        return {"message": "Connexion réussie", "success": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.post("/logout")
async def admin_logout(response: Response):
    """Déconnexion admin"""
    response.delete_cookie(key="session_id", httponly=True, secure=True, samesite="none")
    return {"message": "Déconnexion réussie"}

@app.get("/verify")
async def verify_admin_session(request: Request):
    """Vérification de session admin"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(status_code=401, detail="Aucune session")
        
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "unknown")
        
        if verify_session(session_id, ip_address, user_agent):
            return {"valid": True, "message": "Session valide"}
        else:
            raise HTTPException(status_code=401, detail="Session invalide")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
