"""
Endpoints de gestion de la newsletter avec double opt-in.
Inscription, confirmation, désinscription conforme RGPD.
"""

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
import secrets
import os
import logging

from app.models.subscriber import (
    SubscribeRequest,
    UnsubscribeRequest,
    SubscriberStatus,
    SubscriberSource,
    SubscriberStats
)
from app.repositories.subscriber_repo import subscriber_repo
from app.services.email.jwt_utils import (
    generate_confirmation_token,
    generate_unsubscribe_token,
    verify_confirmation_token,
    verify_unsubscribe_token
)
from app.services.email.mailerlite_client import (
    ensure_newsletter_subscriber,
    mark_subscriber_confirmed,
    mark_subscriber_unsubscribed,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# URL de base du frontend (pour les redirections)
_FRONTEND_RAW = os.getenv("FRONTEND_URL", "http://localhost:5173")
FRONTEND_URL = _FRONTEND_RAW.split(",")[0].strip() if _FRONTEND_RAW else "http://localhost:5173"


@router.post("/subscribe", response_model=dict)
async def subscribe_to_newsletter(request: SubscribeRequest, req: Request):
    """
    Endpoint d'inscription à la newsletter avec double opt-in.
    
    Flow:
    1. Crée l'abonné avec status='pending'
    2. Génère un token JWT de confirmation
    3. Envoie un email avec lien de confirmation
    4. Retourne un message de succès
    
    Args:
        request: Données d'inscription (email + consentement)
        req: Request FastAPI pour récupérer l'IP et user agent
        
    Returns:
        Message de succès
    """
    email = request.email.strip().lower()
    
    # Vérifier le consentement RGPD
    if not request.consent_accepted:
        raise HTTPException(
            status_code=400,
            detail="Le consentement RGPD doit être accepté pour s'inscrire"
        )
    
    # Vérifier si l'email existe déjà
    existing = subscriber_repo.get_by_email(email)
    
    if existing:
        # Si déjà confirmé, retourner erreur
        if existing.get("status") == SubscriberStatus.CONFIRMED.value:
            raise HTTPException(
                status_code=409,
                detail="Adresse email déjà abonnée."
            )
        
        # Si désabonné, permettre la réinscription
        if existing.get("status") == SubscriberStatus.UNSUBSCRIBED.value:
            # Réinitialiser le statut à pending
            subscriber_repo.update(email, {
                "status": SubscriberStatus.PENDING.value,
                "consent_accepted": True,
                "consent_ip": client_ip,
                "consent_user_agent": user_agent,
                "unsubscribed_at": None,
                "unsubscribe_reason": None
            })
            # Renvoyer via MailerLite
            mailerlite_result = ensure_newsletter_subscriber(email=email)
            return {
                "message": "Email de vérification envoyé."
            }
        
        # Si pending, renvoyer l'email de confirmation
        if existing.get("status") == SubscriberStatus.PENDING.value:
            # Renvoyer via MailerLite
            mailerlite_result = ensure_newsletter_subscriber(email=email)
            return {
                "message": "Email de vérification renvoyé."
            }
    
    # Récupérer IP et User Agent pour RGPD
    client_ip = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent", "Unknown")
    
    # Générer les tokens
    confirmation_token = generate_confirmation_token(email)
    unsubscribe_token = generate_unsubscribe_token(email)
    
    # Créer l'abonné
    subscriber_data = {
        "email": email,
        "status": SubscriberStatus.PENDING.value,
        "consent_accepted": True,
        "consent_ip": client_ip,
        "consent_user_agent": user_agent,
        "source": SubscriberSource.FRONT_FORM.value,
        "confirmation_token": confirmation_token,
        "unsubscribe_token": unsubscribe_token
    }
    
    subscriber_id = subscriber_repo.create(subscriber_data)
    
    if not subscriber_id:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'inscription. Veuillez réessayer."
        )

    # Ajouter dans MailerLite avec double opt-in
    # MailerLite enverra automatiquement l'email de confirmation si:
    # Account Settings → Subscribe Settings → "Double opt-in for API" est activé
    mailerlite_result = ensure_newsletter_subscriber(email=email)
    
    if not mailerlite_result:
        logger.warning(f"Failed to add subscriber to MailerLite: {email}")
    else:
        logger.debug(f"Subscriber added to MailerLite with double opt-in: {email}")
    
    logger.debug(f"New subscriber (pending confirmation): {email}")
    
    return {
        "message": "Email de vérification envoyé.",
        "email": email,
        "status": "pending",
        "benefit": "Vous recevrez 10% de réduction sur votre premier achat une fois confirmé !"
    }


@router.get("/confirm")
async def confirm_subscription(token: str = Query(..., description="Token JWT de confirmation")):
    """
    Endpoint de confirmation d'inscription (double opt-in).
    
    Flow:
    1. Vérifie le token JWT
    2. Passe l'abonné en status='confirmed'
    3. Génère un code promo
    4. Envoie un email de bienvenue avec le code promo
    5. Redirige vers une page de confirmation
    
    Args:
        token: Token JWT de confirmation
        
    Returns:
        Redirection vers la page de confirmation avec le code promo
    """
    # Vérifier le token
    email = verify_confirmation_token(token)
    
    if not email:
        # Rediriger vers une page d'erreur
        return RedirectResponse(
            url=f"{FRONTEND_URL}/newsletter/error?reason=invalid_token",
            status_code=302
        )
    
    # Récupérer l'abonné
    subscriber = subscriber_repo.get_by_email(email)
    
    if not subscriber:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/newsletter/error?reason=not_found",
            status_code=302
        )
    
    # Vérifier s'il est déjà confirmé
    if subscriber.get("status") == SubscriberStatus.CONFIRMED.value:
        # Déjà confirmé, rediriger avec le code promo existant
        promo_code = subscriber.get("promo_code", "")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/newsletter/confirmed?promo={promo_code}&already=true",
            status_code=302
        )
    
    # Générer un code promo
    promo_code = f"EC10-{secrets.token_hex(3).upper()}"
    
    # Confirmer l'abonné
    success = subscriber_repo.confirm(email, promo_code)
    
    if not success:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/newsletter/error?reason=update_failed",
            status_code=302
        )

    # Marquer l'abonné comme actif dans MailerLite
    mark_subscriber_confirmed(email)
    
    logger.debug(f"Subscriber confirmed: {email} - Promo: {promo_code}")
    
    # Rediriger vers la page de confirmation avec le code promo
    return RedirectResponse(
        url=f"{FRONTEND_URL}/newsletter/confirmed?promo={promo_code}",
        status_code=302
    )


@router.post("/unsubscribe", response_model=dict)
async def unsubscribe_from_newsletter(request: UnsubscribeRequest):
    """
    Endpoint de désinscription de la newsletter.
    
    Args:
        request: Token de désinscription + raison optionnelle
        
    Returns:
        Message de confirmation
    """
    # Vérifier le token
    email = verify_unsubscribe_token(request.token)
    
    if not email:
        raise HTTPException(
            status_code=400,
            detail="Token de désinscription invalide ou expiré"
        )
    
    # Récupérer l'abonné
    subscriber = subscriber_repo.get_by_email(email)
    
    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="Abonné introuvable"
        )
    
    # Désinscrire
    success = subscriber_repo.unsubscribe(email, request.reason)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la désinscription"
        )

    # Retirer de MailerLite
    mark_subscriber_unsubscribed(email)
    
    logger.debug(f"Subscriber unsubscribed: {email}")
    
    return {
        "message": "Vous avez été désinscrit de la newsletter avec succès.",
        "email": email
    }


@router.get("/unsubscribe")
async def unsubscribe_get(token: str = Query(..., description="Token de désinscription")):
    """
    Endpoint GET de désinscription (lien dans les emails).
    Redirige vers une page de confirmation de désinscription avec le token.
    L'utilisateur devra confirmer sa désinscription sur le frontend.
    """
    # Vérifier le token
    email = verify_unsubscribe_token(token)
    
    if not email:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/newsletter/error?reason=invalid_unsubscribe_token",
            status_code=302
        )
    
    # Rediriger vers la page de confirmation avec le token
    return RedirectResponse(
        url=f"{FRONTEND_URL}/newsletter/unsubscribe?token={token}",
        status_code=302
    )


@router.get("/stats", response_model=SubscriberStats)
async def get_subscriber_stats():
    """
    Endpoint pour récupérer les statistiques des abonnés.
    (Protection admin recommandée en production)
    """
    stats = subscriber_repo.get_stats()
    return SubscriberStats(**stats)


@router.get("/check-subscriber/{email}")
async def check_subscriber_status(email: str):
    """
    Vérifie si un email est abonné et actif pour appliquer une réduction.
    Retourne le code promo si l'abonné est confirmé ET n'a pas encore utilisé son code.
    """
    # Nettoyer et normaliser l'email
    clean_email = email.strip().lower()
    logger.debug(f"Checking subscriber status for: {clean_email}")
    
    subscriber = subscriber_repo.get_by_email(clean_email)
    
    if not subscriber:
        logger.debug(f"Subscriber not found: {clean_email}")
        return {
            "is_subscriber": False,
            "discount": 0,
            "promo_code": None
        }
    
    logger.debug(f"Subscriber found - Status: {subscriber.get('status')}, Promo used: {subscriber.get('promo_used', False)}")
    
    # Vérifier si l'abonné est confirmé
    if subscriber.get("status") == SubscriberStatus.CONFIRMED.value:
        # Vérifier si le promo a déjà été utilisé
        if subscriber.get("promo_used", False):
            logger.debug(f"Promo already used for: {clean_email}")
            return {
                "is_subscriber": True,
                "discount": 0,
                "promo_code": None,
                "message": "Code promo déjà utilisé"
            }
        
        logger.debug(f"Discount applicable for: {clean_email}")
        return {
            "is_subscriber": True,
            "discount": 10,  # 10% de réduction
            "promo_code": subscriber.get("promo_code"),
            "message": "Réduction abonné newsletter appliquée"
        }
    
    return {
        "is_subscriber": False,
        "discount": 0,
        "promo_code": None
    }


@router.post("/mark-promo-used/{email}")
async def mark_promo_as_used(email: str):
    """
    Marque le code promo comme utilisé pour un email.
    Appelé après un paiement réussi.
    """
    clean_email = email.strip().lower()
    subscriber = subscriber_repo.get_by_email(clean_email)
    
    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="Abonné introuvable"
        )
    
    # Marquer comme utilisé
    success = subscriber_repo.update(clean_email, {
        "promo_used": True,
        "promo_used_at": datetime.utcnow()
    })
    
    if success:
        logger.debug(f"Promo code marked as used for: {clean_email}")
        return {"message": "Code promo marqué comme utilisé"}
    
    raise HTTPException(
        status_code=500,
        detail="Erreur lors de la mise à jour"
    )


class ResendConfirmationRequest(BaseModel):
    """Requête de renvoi d'email de confirmation"""
    email: EmailStr


@router.post("/resend-confirmation", response_model=dict)
async def resend_confirmation(request: ResendConfirmationRequest):
    """
    Renvoie l'email de confirmation pour un abonné pending.
    """
    email = request.email.strip().lower()
    
    # Récupérer l'abonné
    subscriber = subscriber_repo.get_by_email(email)
    
    if not subscriber:
        raise HTTPException(
            status_code=404,
            detail="Email non trouvé dans notre base"
        )
    
    if subscriber.get("status") != SubscriberStatus.PENDING.value:
        raise HTTPException(
            status_code=400,
            detail="Cet email est déjà confirmé ou inactif"
        )
    
    # Générer un nouveau token
    confirmation_token = generate_confirmation_token(email)
    
    # Mettre à jour le token
    subscriber_repo.update(email, {"confirmation_token": confirmation_token})
    
    # MailerLite gère le renvoi automatiquement via le double opt-in
    logger.debug(f"Confirmation email will be resent by MailerLite for {email}")
    
    return {
        "message": "Email de confirmation renvoyé avec succès"
    }
