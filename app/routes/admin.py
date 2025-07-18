from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import timedelta
from app.models.admin import AdminLogin, AdminCreate, Token, AdminInDB
from app.crud.admin import (
    authenticate_admin,
    create_access_token,
    verify_token,
    get_admin_by_username,
    create_admin,
    update_last_login,
    get_all_admins,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from typing import Optional

router = APIRouter()
security = HTTPBearer()

def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    admin = get_admin_by_username(username)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin

@router.post("/login", response_model=Token)
async def login(admin_data: AdminLogin):
    admin = authenticate_admin(admin_data.username, admin_data.password)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not admin.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte désactivé",
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": admin["username"]}, expires_delta=access_token_expires
    )
    
    # Mettre à jour la dernière connexion
    update_last_login(admin["username"])
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/create")
async def create_admin_account(admin_data: AdminCreate, current_admin: dict = Depends(get_current_admin)):
    # Seuls les super admins peuvent créer des comptes
    if current_admin.get("role") != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les super admins peuvent créer des comptes"
        )
    
    try:
        admin_id = create_admin(admin_data)
        return {"message": "Admin créé avec succès", "admin_id": admin_id}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/me")
async def get_current_admin_info(current_admin: dict = Depends(get_current_admin)):
    admin_data = {
        "id": str(current_admin["_id"]),
        "username": current_admin["username"],
        "email": current_admin["email"],
        "role": current_admin["role"],
        "is_active": current_admin["is_active"],
        "created_at": current_admin["created_at"],
        "last_login": current_admin.get("last_login")
    }
    return admin_data

@router.get("/verify-token")
async def verify_admin_token(current_admin: dict = Depends(get_current_admin)):
    return {"valid": True, "username": current_admin["username"], "role": current_admin["role"]}

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_admin: dict = Depends(get_current_admin)):
    """Récupère les statistiques pour le dashboard"""
    from app.crud.orders import get_all_orders
    from app.crud.artworks import get_all_artworks
    from app.crud.events import get_all_events
    
    try:
        # Récupérer toutes les données
        orders = get_all_orders()
        artworks = get_all_artworks()
        events = get_all_events()
        
        # Calculer les statistiques de base
        total_orders = len(orders)
        total_revenue = sum(order.get("total", 0) for order in orders)
        total_artworks = len(artworks)
        available_artworks = len([art for art in artworks if art.get("is_available", True)])
        total_events = len(events)
        active_events = len([event for event in events if event.get("is_active", True)])
        
        # Statistiques par statut de commande
        order_stats = {}
        for order in orders:
            status = order.get("status", "pending")
            order_stats[status] = order_stats.get(status, 0) + 1
        
        # Revenus par mois (derniers 6 mois)
        from datetime import datetime, timedelta
        monthly_revenue = {}
        six_months_ago = datetime.now() - timedelta(days=180)
        
        for order in orders:
            order_date = order.get("created_at")
            if order_date and isinstance(order_date, datetime) and order_date >= six_months_ago:
                month_key = order_date.strftime("%Y-%m")
                monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + order.get("total", 0)
        
        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "total_artworks": total_artworks,
            "available_artworks": available_artworks,
            "total_events": total_events,
            "active_events": active_events,
            "order_stats": order_stats,
            "monthly_revenue": monthly_revenue
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des statistiques: {str(e)}"
        )
