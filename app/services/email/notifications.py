"""
Service de notifications automatiques pour les événements artworks.
Envoi d'emails aux abonnés lors de l'ajout ou suppression d'une œuvre.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from app.repositories.subscriber_repo import subscriber_repo
from app.services.email.mailjet_client import (
    send_batch_emails,
    get_artwork_variables,
    TEMPLATE_NEW_ARTWORK,
    TEMPLATE_REMOVED_ARTWORK
)
from app.services.email.jwt_utils import generate_unsubscribe_token
from app.crud import artworks as artworks_crud

logger = logging.getLogger(__name__)

# URL de base du frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


def notify_new_artwork(artwork_id: str) -> Dict[str, Any]:
    """
    Notifie tous les abonnés actifs qu'une nouvelle œuvre a été ajoutée.
    
    Args:
        artwork_id: ID de l'œuvre ajoutée
        
    Returns:
        Statistiques d'envoi {sent: int, failed: int, errors: List}
    """
    logger.info(f"📧 Starting notification for new artwork: {artwork_id}")
    
    # Vérifier que le template est configuré
    if not TEMPLATE_NEW_ARTWORK:
        logger.warning("New artwork template not configured. Skipping notification.")
        return {"sent": 0, "failed": 0, "errors": ["Template not configured"]}
    
    # Récupérer l'artwork
    artwork = artworks_crud.get_artwork_by_id(artwork_id)
    if not artwork:
        logger.error(f"Artwork not found: {artwork_id}")
        return {"sent": 0, "failed": 0, "errors": ["Artwork not found"]}
    
    # Récupérer les abonnés actifs
    subscribers = subscriber_repo.get_active_subscribers()
    
    if not subscribers:
        logger.info("No active subscribers to notify")
        return {"sent": 0, "failed": 0, "errors": []}
    
    logger.info(f"Notifying {len(subscribers)} subscribers about new artwork")
    
    # Préparer la liste des emails
    recipients = [sub["email"] for sub in subscribers]
    
    # Fonction pour générer les variables (identiques pour tous)
    def variables_generator(batch):
        # Pour chaque email dans le batch, on peut personnaliser
        # Ici on utilise les mêmes variables pour tous
        # Récupérer le token de désinscription pour le premier (sera le même pour tous)
        sample_email = batch[0]
        unsubscribe_token = generate_unsubscribe_token(sample_email)
        
        return get_artwork_variables(artwork, unsubscribe_token, FRONTEND_URL)
    
    # Envoyer en batches
    try:
        stats = send_batch_emails(
            recipients=recipients,
            template_id=int(TEMPLATE_NEW_ARTWORK),
            variables_generator=variables_generator,
            batch_size=50
        )
        
        # Mettre à jour les statistiques des abonnés
        for email in recipients[:stats["sent"]]:
            subscriber_repo.increment_email_stats(email, sent=True)
        
        logger.info(f"✅ Notification complete. Sent: {stats['sent']}, Failed: {stats['failed']}")
        return stats
        
    except Exception as e:
        logger.error(f"Error sending notifications: {str(e)}")
        return {"sent": 0, "failed": len(recipients), "errors": [str(e)]}


def notify_removed_artwork(artwork_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Notifie tous les abonnés actifs qu'une œuvre a été retirée.
    
    Note: Comme l'artwork est supprimé, on doit passer ses données en paramètre.
    
    Args:
        artwork_data: Données de l'œuvre supprimée (dict complet)
        
    Returns:
        Statistiques d'envoi {sent: int, failed: int, errors: List}
    """
    logger.info(f"📧 Starting notification for removed artwork: {artwork_data.get('title', 'Unknown')}")
    
    # Vérifier que le template est configuré
    if not TEMPLATE_REMOVED_ARTWORK:
        logger.warning("Removed artwork template not configured. Skipping notification.")
        return {"sent": 0, "failed": 0, "errors": ["Template not configured"]}
    
    # Récupérer les abonnés actifs
    subscribers = subscriber_repo.get_active_subscribers()
    
    if not subscribers:
        logger.info("No active subscribers to notify")
        return {"sent": 0, "failed": 0, "errors": []}
    
    logger.info(f"Notifying {len(subscribers)} subscribers about removed artwork")
    
    # Préparer la liste des emails
    recipients = [sub["email"] for sub in subscribers]
    
    # Fonction pour générer les variables
    def variables_generator(batch):
        sample_email = batch[0]
        unsubscribe_token = generate_unsubscribe_token(sample_email)
        
        return get_artwork_variables(artwork_data, unsubscribe_token, FRONTEND_URL)
    
    # Envoyer en batches
    try:
        stats = send_batch_emails(
            recipients=recipients,
            template_id=int(TEMPLATE_REMOVED_ARTWORK),
            variables_generator=variables_generator,
            batch_size=50
        )
        
        # Mettre à jour les statistiques des abonnés
        for email in recipients[:stats["sent"]]:
            subscriber_repo.increment_email_stats(email, sent=True)
        
        logger.info(f"✅ Notification complete. Sent: {stats['sent']}, Failed: {stats['failed']}")
        return stats
        
    except Exception as e:
        logger.error(f"Error sending notifications: {str(e)}")
        return {"sent": 0, "failed": len(recipients), "errors": [str(e)]}


def notify_artwork_update(artwork_id: str, changes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Notifie les abonnés d'une mise à jour importante d'une œuvre.
    (ex: changement de prix significatif, nouvelles images, etc.)
    
    Note: À implémenter selon les besoins.
    
    Args:
        artwork_id: ID de l'œuvre mise à jour
        changes: Dictionnaire des changements effectués
        
    Returns:
        Statistiques d'envoi
    """
    # À implémenter si besoin
    logger.info(f"Artwork update notification not yet implemented: {artwork_id}")
    return {"sent": 0, "failed": 0, "errors": ["Not implemented"]}


def send_bulk_announcement(
    subject: str,
    message: str,
    template_id: Optional[int] = None,
    variables: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Envoie une annonce groupée à tous les abonnés actifs.
    Utile pour les promotions, nouvelles collections, événements spéciaux.
    
    Args:
        subject: Sujet de l'email
        message: Contenu du message
        template_id: ID du template Mailjet (optionnel)
        variables: Variables pour le template (optionnel)
        
    Returns:
        Statistiques d'envoi
    """
    # À implémenter selon les besoins
    logger.info("Bulk announcement: feature not yet implemented")
    return {"sent": 0, "failed": 0, "errors": ["Not implemented"]}
