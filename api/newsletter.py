from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import EmailStr
from app.models.newsletter import NewsletterSubscription, NewsletterUnsubscribe
from app.crud.newsletter import (
    subscribe_to_newsletter, 
    unsubscribe_from_newsletter, 
    get_active_subscribers,
    get_newsletter_stats,
    check_email_subscribed
)
from api.auth_admin import require_admin_auth

router = APIRouter()

@router.post("/subscribe", response_model=dict)
def subscribe_email(email_data: dict):
    """
    Abonne un email à la newsletter
    """
    try:
        email = email_data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email requis")
        
        subscription_id = subscribe_to_newsletter(email)
        return {"message": "Abonnement réussi", "id": subscription_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de l'abonnement")

@router.post("/unsubscribe", response_model=dict)
def unsubscribe_email(unsubscribe_data: NewsletterUnsubscribe):
    """
    Désabonne un email via son token
    """
    try:
        success = unsubscribe_from_newsletter(unsubscribe_data.token)
        if success:
            return {"message": "Désabonnement réussi"}
        else:
            raise HTTPException(status_code=404, detail="Token invalide ou déjà utilisé")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors du désabonnement")

@router.get("/subscribers", response_model=list)
def get_subscribers(_: bool = Depends(require_admin_auth)):
    """
    Récupère la liste des abonnés (admin seulement)
    """
    try:
        return get_active_subscribers()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des abonnés")

@router.get("/stats", response_model=dict)
def get_stats(_: bool = Depends(require_admin_auth)):
    """
    Récupère les statistiques de la newsletter (admin seulement)
    """
    try:
        return get_newsletter_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des statistiques")

@router.get("/check/{email}", response_model=dict)
def check_subscription(email: str, _: bool = Depends(require_admin_auth)):
    """
    Vérifie si un email est abonné (admin seulement)
    """
    try:
        is_subscribed = check_email_subscribed(email)
        return {"email": email, "is_subscribed": is_subscribed}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erreur lors de la vérification")
