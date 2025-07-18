from fastapi import HTTPException, Request
from app.auth_simple import verify_session

async def require_admin_auth(request: Request):
    """Middleware pour vérifier l'authentification admin"""
    try:
        session_id = request.cookies.get("session_id")
        if not session_id:
            raise HTTPException(status_code=401, detail="Authentification requise")
        
        ip_address = request.client.host
        user_agent = request.headers.get("user-agent", "unknown")
        
        if not verify_session(session_id, ip_address, user_agent):
            raise HTTPException(status_code=401, detail="Session invalide")
            
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
