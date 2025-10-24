"""
Webhooks Mailjet pour gérer les événements email.
Gère les bounces, spam complaints, unsubscribes automatiques.
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, List
import logging
from app.repositories.subscriber_repo import subscriber_repo

logger = logging.getLogger(__name__)
router = APIRouter()


# Types d'événements Mailjet
# https://dev.mailjet.com/email/guides/webhooks/#event-types
EVENT_TYPES = {
    "bounce": "Email bounced (invalid email)",
    "blocked": "Email blocked (Mailjet blacklist)",
    "spam": "Marked as spam by recipient",
    "unsub": "Unsubscribed via Mailjet link",
    "sent": "Email sent successfully",
    "open": "Email opened",
    "click": "Link clicked in email"
}


@router.post("/")
async def handle_mailjet_webhook(request: Request):
    """
    Endpoint webhook pour recevoir les événements Mailjet.
    
    Mailjet envoie un tableau d'événements :
    [
        {
            "event": "bounce",
            "time": 1430812195,
            "MessageID": 19421777835146490,
            "email": "bounce@mailjet.com",
            "mj_campaign_id": 0,
            "mj_contact_id": 0,
            "customcampaign": "",
            "mj_message_id": "19421777835146490",
            "smtp_reply": "user unknown",
            "hard_bounce": true,
            "blocked": false,
            "comment": "Mailjet has blocked this email"
        }
    ]
    
    Returns:
        200 OK si traité avec succès
    """
    try:
        # Récupérer le body JSON
        events = await request.json()
        
        if not isinstance(events, list):
            logger.warning("Webhook payload is not a list")
            raise HTTPException(status_code=400, detail="Invalid payload format")
        
        logger.info(f"📬 Received {len(events)} Mailjet event(s)")
        
        # Traiter chaque événement
        for event in events:
            await process_mailjet_event(event)
        
        return {"message": "Webhook processed", "events": len(events)}
        
    except Exception as e:
        logger.error(f"Error processing Mailjet webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_mailjet_event(event: Dict):
    """
    Traite un événement Mailjet individuel.
    
    Args:
        event: Événement Mailjet (dict)
    """
    event_type = event.get("event")
    email = event.get("email", "").lower()
    
    if not email:
        logger.warning(f"Event without email: {event}")
        return
    
    logger.info(f"Processing event '{event_type}' for {email}")
    
    # Récupérer l'abonné
    subscriber = subscriber_repo.get_by_email(email)
    
    if not subscriber:
        logger.warning(f"Subscriber not found for webhook event: {email}")
        return
    
    # Traiter selon le type d'événement
    if event_type == "bounce":
        await handle_bounce(email, event)
    elif event_type == "blocked":
        await handle_blocked(email, event)
    elif event_type == "spam":
        await handle_spam(email, event)
    elif event_type == "unsub":
        await handle_unsub(email, event)
    elif event_type == "sent":
        await handle_sent(email, event)
    elif event_type == "open":
        await handle_open(email, event)
    elif event_type == "click":
        await handle_click(email, event)
    else:
        logger.info(f"Unhandled event type: {event_type}")


async def handle_bounce(email: str, event: Dict):
    """
    Gère les bounces (emails invalides).
    
    Hard bounce : email invalide définitivement → marquer comme bounced
    Soft bounce : erreur temporaire → logger seulement
    """
    is_hard_bounce = event.get("hard_bounce", False)
    smtp_reply = event.get("smtp_reply", "")
    
    if is_hard_bounce:
        # Email définitivement invalide
        success = subscriber_repo.mark_bounced(email)
        if success:
            logger.warning(f"⚠️ Hard bounce - Subscriber marked as bounced: {email} - {smtp_reply}")
        else:
            logger.error(f"Failed to mark subscriber as bounced: {email}")
    else:
        # Soft bounce - erreur temporaire
        logger.info(f"Soft bounce for {email}: {smtp_reply}")


async def handle_blocked(email: str, event: Dict):
    """
    Gère les emails bloqués par Mailjet.
    Similaire aux hard bounces.
    """
    comment = event.get("comment", "")
    success = subscriber_repo.mark_bounced(email)
    
    if success:
        logger.warning(f"⚠️ Email blocked - Subscriber marked as bounced: {email} - {comment}")
    else:
        logger.error(f"Failed to mark subscriber as bounced: {email}")


async def handle_spam(email: str, event: Dict):
    """
    Gère les plaintes pour spam.
    Marque l'abonné comme complained et arrête l'envoi.
    """
    source = event.get("source", "")
    success = subscriber_repo.mark_complained(email)
    
    if success:
        logger.warning(f"⚠️ Spam complaint - Subscriber marked as complained: {email} - Source: {source}")
    else:
        logger.error(f"Failed to mark subscriber as complained: {email}")


async def handle_unsub(email: str, event: Dict):
    """
    Gère les désinscriptions via les liens Mailjet.
    """
    mj_list_id = event.get("mj_list_id", "")
    success = subscriber_repo.unsubscribe(email, "Désinscription via lien Mailjet")
    
    if success:
        logger.info(f"📭 Mailjet unsubscribe - Subscriber unsubscribed: {email}")
    else:
        logger.error(f"Failed to unsubscribe: {email}")


async def handle_sent(email: str, event: Dict):
    """
    Gère les événements d'envoi réussi.
    Incrémente le compteur d'emails envoyés.
    """
    success = subscriber_repo.increment_email_stats(email, sent=True)
    if success:
        logger.debug(f"✅ Email sent event recorded for {email}")


async def handle_open(email: str, event: Dict):
    """
    Gère les événements d'ouverture d'email.
    Incrémente le compteur d'emails ouverts.
    """
    success = subscriber_repo.increment_email_stats(email, opened=True)
    if success:
        logger.debug(f"👁️ Email opened event recorded for {email}")


async def handle_click(email: str, event: Dict):
    """
    Gère les événements de clic sur un lien.
    Incrémente le compteur de clics.
    """
    url = event.get("url", "")
    success = subscriber_repo.increment_email_stats(email, clicked=True)
    if success:
        logger.debug(f"🖱️ Email click event recorded for {email} - URL: {url}")


@router.get("/health")
async def webhook_health():
    """
    Endpoint de santé pour vérifier que le webhook est actif.
    """
    return {
        "status": "ok",
        "webhook": "mailjet",
        "supported_events": list(EVENT_TYPES.keys())
    }
