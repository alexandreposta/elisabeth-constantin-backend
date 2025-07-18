from fastapi import APIRouter, HTTPException, Response, Request, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from app.auth_simple import authenticate_admin, create_session, verify_session, cleanup_sessions
import json

router = APIRouter()
security = HTTPBearer(auto_error=False)

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
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

@router.post("/logout")
async def admin_logout(response: Response):
    """Déconnexion admin"""
    response.delete_cookie(key="session_id", httponly=True, secure=True, samesite="none")
    return {"message": "Déconnexion réussie"}

@router.get("/verify")
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
