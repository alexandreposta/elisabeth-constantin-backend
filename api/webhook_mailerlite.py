"""
Webhook endpoint pour MailerLite.
Reçoit les notifications de MailerLite quand un subscriber change de statut.
"""

from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any
import logging
import os

from app.repositories.subscriber_repo import subscriber_repo
from app.models.subscriber import SubscriberStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# Secret pour valider les webhooks (optionnel mais recommandé)
WEBHOOK_SECRET = os.getenv("MAILERLITE_WEBHOOK_SECRET", "")


@router.post("/subscriber-updated")
async def mailerlite_webhook_subscriber_updated(request: Request):
    """
    Webhook appelé par MailerLite quand un subscriber est mis à jour.
    
    Events possibles:
    - subscriber.created
    - subscriber.updated  
    - subscriber.unsubscribed
    - subscriber.complaint
    - subscriber.bounced
    - subscriber.double_opt_in (quand le user confirme son email)
    
    Payload exemple:
    {
        "events": [{
            "type": "subscriber.double_opt_in",
            "data": {
                "subscriber": {
                    "id": "123",
                    "email": "user@example.com",
                    "status": "active",
                    ...
                }
            }
        }]
    }
    """
    try:
        payload = await request.json()
        logger.info(f"Received MailerLite webhook: {payload}")
        
        # Valider le secret si configuré
        if WEBHOOK_SECRET:
            webhook_secret = request.headers.get("X-MailerLite-Signature")
            if webhook_secret != WEBHOOK_SECRET:
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        events = payload.get("events", [])
        
        for event in events:
            event_type = event.get("type")
            event_data = event.get("data", {})
            subscriber_data = event_data.get("subscriber", {})
            
            email = subscriber_data.get("email")
            mailerlite_status = subscriber_data.get("status")
            
            if not email:
                logger.warning(f"No email in webhook event: {event_type}")
                continue
            
            # Récupérer l'abonné dans notre DB
            existing = subscriber_repo.get_by_email(email)
            
            if not existing:
                logger.warning(f"Subscriber {email} not found in DB, skipping webhook update")
                continue
            
            # Mapper le statut MailerLite vers notre statut
            if event_type == "subscriber.double_opt_in" or mailerlite_status == "active":
                # Le user a confirmé son email
                if existing.get("status") != SubscriberStatus.CONFIRMED.value:
                    # Générer un code promo si pas déjà fait
                    promo_code = existing.get("promo_code")
                    if not promo_code:
                        import secrets
                        promo_code = f"EC10-{secrets.token_hex(3).upper()}"
                    
                    subscriber_repo.confirm(email, promo_code)
                    logger.info(f"✅ Subscriber confirmed via webhook: {email}")
            
            elif event_type == "subscriber.unsubscribed" or mailerlite_status == "unsubscribed":
                if existing.get("status") != SubscriberStatus.UNSUBSCRIBED.value:
                    subscriber_repo.unsubscribe(email, "Unsubscribed via MailerLite")
                    logger.info(f"📭 Subscriber unsubscribed via webhook: {email}")
            
            elif event_type == "subscriber.bounced" or mailerlite_status == "bounced":
                subscriber_repo.mark_bounced(email)
                logger.info(f"⚠️ Subscriber bounced via webhook: {email}")
            
            elif event_type == "subscriber.complaint" or mailerlite_status == "junk":
                subscriber_repo.mark_complained(email)
                logger.info(f"⚠️ Subscriber complained via webhook: {email}")
        
        return {"status": "success", "processed": len(events)}
    
    except Exception as e:
        logger.error(f"Error processing MailerLite webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def webhook_health():
    """Health check pour le webhook"""
    return {"status": "healthy", "service": "mailerlite-webhook"}
