"""
Client Mailjet centralisé pour l'envoi d'emails transactionnels.
Gère l'envoi de templates avec retry et logging.
"""

import os
import time
from typing import List, Dict, Optional
from mailjet_rest import Client
import logging

logger = logging.getLogger(__name__)

# Configuration depuis les variables d'environnement
MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
# Accept either MAILJET_API_SECRET or MAILJET_PRIVATE_KEY (some deploys name it PRIVATE_KEY)
MAILJET_API_SECRET = os.getenv("MAILJET_API_SECRET") or os.getenv("MAILJET_PRIVATE_KEY")
MAILJET_SENDER_EMAIL = os.getenv("MAILJET_SENDER", "newsletter@elisabeth-constantin.fr")
MAILJET_SENDER_NAME = os.getenv("MAILJET_SENDER_NAME", "Élisabeth Constantin")

# IDs des templates Mailjet
TEMPLATE_NEW_ARTWORK = os.getenv("MAILJET_TEMPLATE_NEW_ART")
TEMPLATE_REMOVED_ARTWORK = os.getenv("MAILJET_TEMPLATE_REMOVED_ART")
TEMPLATE_CONFIRMATION = os.getenv("MAILJET_TEMPLATE_CONFIRMATION")
TEMPLATE_WELCOME = os.getenv("MAILJET_TEMPLATE_WELCOME")

# Initialisation du client Mailjet
mailjet_client = None
if MAILJET_API_KEY and MAILJET_API_SECRET:
    mailjet_client = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3.1')
    logger.info("✅ Mailjet client initialized successfully")
else:
    logger.warning("⚠️ Mailjet credentials not set. Email sending will be disabled.")


def send_template_email(
    to_list: List[Dict[str, str]],
    template_id: int,
    variables: Dict[str, any],
    subject: Optional[str] = None,
    custom_id: Optional[str] = None,
    max_retries: int = 3
) -> Dict[str, any]:
    """
    Envoie un email basé sur un template Mailjet.
    
    Args:
        to_list: Liste de destinataires [{"Email": "user@example.com", "Name": "User"}]
        template_id: ID du template Mailjet
        variables: Variables à injecter dans le template
        subject: Sujet de l'email (optionnel, peut être défini dans le template)
        custom_id: ID personnalisé pour tracking
        max_retries: Nombre maximum de tentatives
        
    Returns:
        Réponse de l'API Mailjet
        
    Raises:
        Exception: Si l'envoi échoue après tous les retries
    """
    if not mailjet_client:
        logger.error("Mailjet client not initialized. Cannot send email.")
        raise Exception("Mailjet not configured")
    
    if not template_id:
        logger.error("Template ID not provided")
        raise Exception("Template ID required")
    
    # Construction du message
    message = {
        "From": {
            "Email": MAILJET_SENDER_EMAIL,
            "Name": MAILJET_SENDER_NAME
        },
        "To": to_list,
        "TemplateID": int(template_id),
        "TemplateLanguage": True,
        "Variables": variables
    }
    
    if subject:
        message["Subject"] = subject
    
    if custom_id:
        message["CustomID"] = custom_id
    
    data = {"Messages": [message]}
    
    # Retry logic avec backoff exponentiel
    for attempt in range(max_retries):
        try:
            result = mailjet_client.send.create(data=data)
            
            if result.status_code == 200:
                logger.info(f"✅ Email sent successfully to {len(to_list)} recipient(s)")
                return result.json()
            elif result.status_code == 429:
                # Rate limit - attendre avant de réessayer
                wait_time = 2 ** attempt
                logger.warning(f"Rate limit hit (429). Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"Mailjet API error: {result.status_code} - {result.json()}")
                if attempt == max_retries - 1:
                    raise Exception(f"Mailjet API error: {result.status_code}")
                time.sleep(2 ** attempt)
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    
    raise Exception("Failed to send email after all retries")


def send_batch_emails(
    recipients: List[str],
    template_id: int,
    variables_generator: callable,
    batch_size: int = 50
) -> Dict[str, any]:
    """
    Envoie des emails en batch pour éviter les limites de Mailjet.
    
    Args:
        recipients: Liste d'emails destinataires
        template_id: ID du template Mailjet
        variables_generator: Fonction qui génère les variables pour chaque email
        batch_size: Nombre d'emails par batch (max 50 recommandé)
        
    Returns:
        Statistiques d'envoi {sent: int, failed: int, errors: List}
    """
    stats = {"sent": 0, "failed": 0, "errors": []}
    
    # Découper en batches
    for i in range(0, len(recipients), batch_size):
        batch = recipients[i:i + batch_size]
        to_list = [{"Email": email} for email in batch]
        
        try:
            # Générer les variables (peut être identique pour tous ou personnalisé)
            variables = variables_generator(batch)
            
            send_template_email(
                to_list=to_list,
                template_id=template_id,
                variables=variables
            )
            
            stats["sent"] += len(batch)
            logger.info(f"Batch {i // batch_size + 1}: {len(batch)} emails sent")
            
        except Exception as e:
            stats["failed"] += len(batch)
            stats["errors"].append({
                "batch": i // batch_size + 1,
                "recipients": batch,
                "error": str(e)
            })
            logger.error(f"Batch {i // batch_size + 1} failed: {str(e)}")
    
    return stats


def send_confirmation_email(email: str, confirmation_token: str, base_url: str) -> bool:
    """
    Envoie un email de confirmation d'inscription (double opt-in).
    
    Args:
        email: Email du destinataire
        confirmation_token: Token de confirmation JWT
        base_url: URL de base du site (ex: https://elisabeth-constantin.fr)
        
    Returns:
        True si envoyé avec succès, False sinon
    """
    if not TEMPLATE_CONFIRMATION:
        logger.warning("Confirmation template not configured")
        return False
    
    confirmation_url = f"{base_url}/newsletter/confirm?token={confirmation_token}"
    
    try:
        send_template_email(
            to_list=[{"Email": email}],
            template_id=int(TEMPLATE_CONFIRMATION),
            variables={
                "confirmation_url": confirmation_url,
                "email": email
            },
            custom_id=f"confirm_{email}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send confirmation email to {email}: {str(e)}")
        return False


def send_welcome_email(email: str, promo_code: str) -> bool:
    """
    Envoie un email de bienvenue avec code promo après confirmation.
    
    Args:
        email: Email du destinataire
        promo_code: Code promo généré
        
    Returns:
        True si envoyé avec succès, False sinon
    """
    if not TEMPLATE_WELCOME:
        logger.warning("Welcome template not configured")
        return False
    
    try:
        send_template_email(
            to_list=[{"Email": email}],
            template_id=int(TEMPLATE_WELCOME),
            variables={
                "email": email,
                "promo_code": promo_code
            },
            custom_id=f"welcome_{email}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {str(e)}")
        return False


# Templates d'artwork
def get_artwork_variables(artwork: Dict, unsubscribe_token: str, base_url: str) -> Dict:
    """
    Génère les variables pour les templates d'artwork.
    """
    return {
        "art_title": artwork.get("title", "Nouvelle œuvre"),
        "art_price": f"{artwork.get('price', 0)}€",
        "art_image_url": artwork.get("image_url", ""),
        "art_link": f"{base_url}/artworks/{artwork.get('_id')}",
        "art_description": artwork.get("description", "")[:200],
        "unsubscribe_url": f"{base_url}/newsletter/unsubscribe?token={unsubscribe_token}"
    }
