"""
Script pour synchroniser les statuts des subscribers entre MailerLite et notre DB.
À exécuter périodiquement (cron job) ou manuellement si les webhooks ne sont pas configurés.
"""

import sys
import os
from pathlib import Path

# Ajouter le dossier parent au path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.repositories.subscriber_repo import subscriber_repo
from app.services.email.mailerlite_client import get_subscriber, list_group_subscribers, ensure_group
from app.models.subscriber import SubscriberStatus
import logging
import secrets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NEWSLETTER_GROUP_NAME = os.getenv("MAILERLITE_NEWSLETTER_GROUP", "newsletter_site")


def sync_mailerlite_to_db():
    """
    Synchronise les statuts depuis MailerLite vers notre DB.
    """
    logger.info("Starting MailerLite to DB synchronization...")
    
    # Récupérer le groupe newsletter
    group_id = ensure_group(NEWSLETTER_GROUP_NAME)
    if not group_id:
        logger.error(f"Could not find group: {NEWSLETTER_GROUP_NAME}")
        return
    
    # Récupérer tous les subscribers du groupe (tous statuts)
    all_subscribers = list_group_subscribers(group_id, limit=1000, status=None)
    
    logger.info(f"Found {len(all_subscribers)} subscribers in MailerLite")
    
    updated_count = 0
    confirmed_count = 0
    
    for ml_subscriber in all_subscribers:
        email = ml_subscriber.get("email")
        ml_status = ml_subscriber.get("status")  # active, unconfirmed, unsubscribed, bounced, junk
        
        if not email:
            continue
        
        # Récupérer l'abonné dans notre DB
        db_subscriber = subscriber_repo.get_by_email(email)
        
        if not db_subscriber:
            logger.info(f"Subscriber {email} exists in MailerLite but not in DB, skipping")
            continue
        
        db_status = db_subscriber.get("status")
        
        # Synchroniser les statuts
        if ml_status == "active" and db_status != SubscriberStatus.CONFIRMED.value:
            # Le user est actif dans MailerLite mais pas confirmé dans notre DB
            promo_code = db_subscriber.get("promo_code")
            if not promo_code:
                promo_code = f"EC10-{secrets.token_hex(3).upper()}"
            
            subscriber_repo.confirm(email, promo_code)
            logger.info(f"✅ Confirmed {email} (was {db_status} in DB, active in MailerLite)")
            confirmed_count += 1
            updated_count += 1
        
        elif ml_status == "unsubscribed" and db_status != SubscriberStatus.UNSUBSCRIBED.value:
            subscriber_repo.unsubscribe(email, "Synced from MailerLite")
            logger.info(f"📭 Unsubscribed {email} (was {db_status} in DB)")
            updated_count += 1
        
        elif ml_status == "bounced" and db_status != SubscriberStatus.BOUNCED.value:
            subscriber_repo.mark_bounced(email)
            logger.info(f"⚠️ Marked {email} as bounced")
            updated_count += 1
        
        elif ml_status == "junk" and db_status != SubscriberStatus.COMPLAINED.value:
            subscriber_repo.mark_complained(email)
            logger.info(f"⚠️ Marked {email} as complained")
            updated_count += 1
    
    logger.info(f"Synchronization complete: {updated_count} subscribers updated, {confirmed_count} confirmed")
    return {
        "total_checked": len(all_subscribers),
        "total_updated": updated_count,
        "newly_confirmed": confirmed_count
    }


if __name__ == "__main__":
    sync_mailerlite_to_db()
