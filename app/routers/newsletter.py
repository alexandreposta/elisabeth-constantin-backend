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
from app.services.email.mailjet_client import (
    send_confirmation_email,
    send_welcome_email
)

logger = logging.getLogger(__name__)
router = APIRouter()

# URL de base du frontend (pour les redirections)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


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
                detail="Cet email est déjà abonné à la newsletter"
            )
        
        # Si pending, renvoyer l'email de confirmation
        if existing.get("status") == SubscriberStatus.PENDING.value:
            confirmation_token = generate_confirmation_token(email)
            send_confirmation_email(email, confirmation_token, FRONTEND_URL)
            return {
                "message": "Email de confirmation renvoyé. Veuillez vérifier votre boîte email."
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
    
    # Envoyer l'email de confirmation
    email_sent = send_confirmation_email(email, confirmation_token, FRONTEND_URL)
    
    if not email_sent:
        logger.warning(f"Failed to send confirmation email to {email}")
        # Ne pas bloquer l'inscription, mais logger
    
    logger.info(f"✅ New subscriber (pending): {email}")
    
    return {
        "message": "Inscription réussie ! Un email de confirmation vous a été envoyé.",
        "email": email,
        "status": "pending"
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
    
    # Envoyer l'email de bienvenue
    welcome_sent = send_welcome_email(email, promo_code)
    
    if not welcome_sent:
        logger.warning(f"Failed to send welcome email to {email}")
    
    logger.info(f"✅ Subscriber confirmed: {email} - Promo: {promo_code}")
    
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
    
    logger.info(f"📭 Subscriber unsubscribed: {email}")
    
    return {
        "message": "Vous avez été désinscrit de la newsletter avec succès.",
        "email": email
    }


@router.get("/unsubscribe")
async def unsubscribe_get(token: str = Query(..., description="Token de désinscription")):
    """
    Endpoint GET de désinscription (lien dans les emails).
    Redirige vers une page de confirmation de désinscription.
    """
    # Vérifier le token
    email = verify_unsubscribe_token(token)
    
    if not email:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/newsletter/error?reason=invalid_unsubscribe_token",
            status_code=302
        )
    
    # Désinscrire directement
    success = subscriber_repo.unsubscribe(email, "Désinscription via lien email")
    
    if not success:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/newsletter/error?reason=unsubscribe_failed",
            status_code=302
        )
    
    logger.info(f"📭 Subscriber unsubscribed via link: {email}")
    
    # Rediriger vers une page de confirmation
    return RedirectResponse(
        url=f"{FRONTEND_URL}/newsletter/unsubscribed",
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
    
    # Renvoyer l'email
    email_sent = send_confirmation_email(email, confirmation_token, FRONTEND_URL)
    
    if not email_sent:
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de l'envoi de l'email"
        )
    
    return {
        "message": "Email de confirmation renvoyé avec succès"
    }
