"""
Client MailerLite pour la gestion des abonnés et l'envoi des emails.
Utilise l'API HTTP v2 (https://connect.mailerlite.com/api).
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Configure logging pour ce module
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "https://connect.mailerlite.com/api"
API_KEY = os.getenv("MAILERLITE_PRIVATE_KEY")

SENDER_EMAIL = os.getenv("MAILERLITE_SENDER_EMAIL", "newsletter@elisabeth-constantin.fr")
SENDER_NAME = os.getenv("MAILERLITE_SENDER_NAME", "Elisabeth Constantin")
NEWSLETTER_GROUP_NAME = os.getenv("MAILERLITE_NEWSLETTER_GROUP", "newsletter_site")

TEMPLATE_DIR = Path(__file__).resolve().parent / "mail-templates"


class MailerLiteError(Exception):
    """Exception personnalisée pour les erreurs MailerLite."""


def _auth_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, endpoint: str, **kwargs) -> Optional[Dict]:
    """
    Effectue une requête HTTP vers MailerLite avec gestion des erreurs.
    """
    if not API_KEY:
        logger.warning("MailerLite API key missing. Skipping call to %s", endpoint)
        return None

    url = f"{BASE_URL}{endpoint}"
    headers = kwargs.pop("headers", {})
    headers.update(_auth_headers())

    try:
        response = requests.request(method, url, headers=headers, timeout=15, **kwargs)
    except requests.RequestException as exc:
        logger.error("MailerLite request failed: %s", exc)
        raise MailerLiteError(str(exc)) from exc

    if response.status_code == 404:
        logger.info("MailerLite resource not found for %s %s", method, endpoint)
        return None

    if not response.ok:
        body_preview = response.text[:400]
        logger.error("MailerLite API error %s: %s", response.status_code, body_preview)
        raise MailerLiteError(f"MailerLite API error {response.status_code}")

    try:
        return response.json()
    except ValueError:
        return {}


def list_groups(limit: int = 100) -> List[Dict]:
    data = _request("GET", "/groups", params={"limit": limit}) or {}
    return data.get("data", [])


def ensure_group(name: str) -> Optional[str]:
    """
    Retourne l'ID d'un groupe, le crée s'il n'existe pas.
    """
    groups = list_groups(limit=200)
    for group in groups:
        if group.get("name") == name:
            return group.get("id")

    created = _request("POST", "/groups", json={"name": name})
    if not created:
        return None
    return (created.get("data") or {}).get("id")


def get_subscriber(email: str) -> Optional[Dict]:
    data = _request("GET", f"/subscribers/{email}")
    if not data:
        return None
    return data.get("data") or data


def upsert_subscriber(
    email: str,
    status: Optional[str] = None,
    groups: Optional[List[str]] = None,
    fields: Optional[Dict] = None,
) -> Optional[Dict]:
    payload: Dict[str, object] = {"email": email}
    if status:
        payload["status"] = status
    if groups:
        payload["groups"] = groups
    if fields:
        payload["fields"] = fields

    data = _request("POST", "/subscribers", json=payload)
    if not data:
        return None
    return data.get("data") or data


def update_subscriber(
    subscriber_id: str,
    status: Optional[str] = None,
    groups: Optional[List[str]] = None,
    fields: Optional[Dict] = None,
) -> Optional[Dict]:
    payload: Dict[str, object] = {}
    if status:
        payload["status"] = status
    if groups is not None:
        payload["groups"] = groups
    if fields:
        payload["fields"] = fields

    if not payload:
        return None

    data = _request("PUT", f"/subscribers/{subscriber_id}", json=payload)
    if not data:
        return None
    return data.get("data") or data


def assign_subscriber_to_group(subscriber_id: str, group_id: str) -> bool:
    response = _request("POST", f"/subscribers/{subscriber_id}/groups/{group_id}")
    return response is not None


def remove_subscriber_from_group(subscriber_id: str, group_id: str) -> bool:
    response = _request("DELETE", f"/subscribers/{subscriber_id}/groups/{group_id}")
    return response is not None


def list_group_subscribers(group_id: str, limit: int = 200, status: Optional[str] = None) -> List[Dict]:
    """
    Liste les subscribers d'un groupe.
    
    Args:
        group_id: ID du groupe
        limit: Nombre max de résultats
        status: Filtre par statut (None=tous, 'active', 'unconfirmed', 'unsubscribed', 'bounced', 'junk')
    """
    params = {"limit": limit}
    if status:
        params["filter[status]"] = status
    
    data = _request("GET", f"/groups/{group_id}/subscribers", params=params) or {}
    return data.get("data", [])


def render_template(template_name: str, context: Dict[str, object]) -> str:
    """
    Remplace les placeholders {{key}} dans un template HTML stocké dans mail-templates/.
    """
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        logger.error("Template not found: %s", template_path)
        return ""

    content = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        content = content.replace(f"{{{{{key}}}}}", str(value or ""))
    return content


def ensure_newsletter_subscriber(
    email: str,
    fields: Optional[Dict] = None,
) -> Optional[Dict]:
    """
    Crée ou met à jour un abonné MailerLite dans le groupe newsletter_site.
    Utilise le double opt-in de MailerLite (status="unconfirmed").
    
    IMPORTANT: Le double opt-in pour API doit être activé dans MailerLite:
    Account Settings → Subscribe Settings → Toggle "Double opt-in for API and integrations" ON
    
    Sans cette activation, MailerLite ne enverra pas d'email de confirmation.
    
    Gestion des statuts existants:
    - active: Déjà confirmé, rien à faire
    - unconfirmed: Déjà en attente, rien à faire
    - unsubscribed: Réinscription → passer à unconfirmed pour déclencher double opt-in
    """
    group_id = ensure_group(NEWSLETTER_GROUP_NAME)
    if not group_id:
        logger.error(f"Could not ensure newsletter group: {NEWSLETTER_GROUP_NAME}")
        return None

    # Vérifier si l'abonné existe déjà
    existing = get_subscriber(email)
    if existing:
        subscriber_id = existing.get("id")
        if not subscriber_id:
            return existing
        
        current_status = existing.get("status")
        
        # Si unsubscribed ou unconfirmed, supprimer et recréer pour forcer le renvoi de l'email
        if current_status in ("unsubscribed", "unconfirmed"):
            logger.info(f"Subscriber {email} has status {current_status}, deleting and recreating to resend confirmation email")
            # Supprimer le subscriber existant
            _request("DELETE", f"/subscribers/{subscriber_id}")
            # Recréer avec status unconfirmed pour déclencher l'email de confirmation
            return upsert_subscriber(email=email, status="unconfirmed", groups=[group_id], fields=fields)
        
        # Si active, juste s'assurer qu'il est dans le groupe
        assign_subscriber_to_group(subscriber_id, group_id)
        logger.info(f"Subscriber {email} already active, no need to resend confirmation")
        return existing

    # Créer un nouvel abonné avec status="unconfirmed" pour déclencher le double opt-in
    # MailerLite enverra automatiquement l'email de confirmation si l'option est activée
    logger.info(f"Creating new subscriber in MailerLite with double opt-in: {email}")
    return upsert_subscriber(email=email, status="unconfirmed", groups=[group_id], fields=fields)


def mark_subscriber_confirmed(email: str) -> Optional[Dict]:
    """
    Passe un abonné en statut actif (appelé après confirmation du double opt-in).
    """
    existing = get_subscriber(email)
    if not existing:
        logger.warning(f"Cannot confirm non-existent subscriber: {email}")
        return None
    
    subscriber_id = existing.get("id")
    if not subscriber_id:
        return existing
    
    return update_subscriber(subscriber_id, status="active")


def mark_subscriber_unsubscribed(email: str) -> bool:
    existing = get_subscriber(email)
    if not existing:
        return False
    subscriber_id = existing.get("id")
    if not subscriber_id:
        return False
    update_subscriber(subscriber_id, status="unsubscribed", groups=[])
    return True


def _build_campaign_payload(subject: str, html_content: str, group_ids: List[str]) -> Dict:
    return {
        "name": subject or f"Campaign-{uuid.uuid4().hex[:6]}",
        "type": "regular",
        "emails": [
            {
                "subject": subject,
                "from": SENDER_EMAIL,
                "from_name": SENDER_NAME,
                "reply_to": SENDER_EMAIL,
                "content": html_content,
            }
        ],
        "groups": group_ids,
        "settings": {"track_opens": True, "use_google_analytics": False},
    }


def send_campaign(subject: str, html_content: str, group_ids: List[str]) -> bool:
    if not group_ids:
        logger.error("Cannot send campaign without target groups")
        return False

    payload = _build_campaign_payload(subject, html_content, group_ids)
    logger.info(f"Creating campaign with payload: {payload.get('name')}")
    created = _request("POST", "/campaigns", json=payload)
    campaign_id = (created or {}).get("data", {}).get("id")
    if not campaign_id:
        logger.error("Unable to create MailerLite campaign for subject '%s'", subject)
        return False

    logger.info(f"Campaign created with ID {campaign_id}, scheduling...")
    scheduled = _request(
        "POST",
        f"/campaigns/{campaign_id}/schedule",
        json={"delivery": "instant"},
    )
    if scheduled is None:
        logger.error("Failed to schedule campaign %s", campaign_id)
        return False

    logger.info("MailerLite campaign %s scheduled with subject '%s'", campaign_id, subject)
    return True


def send_to_newsletter(subject: str, html_content: str) -> bool:
    group_id = ensure_group(NEWSLETTER_GROUP_NAME)
    if not group_id:
        logger.error("Newsletter group not found or creatable")
        return False
    return send_campaign(subject, html_content, [group_id])


# Les emails de confirmation sont gérés automatiquement par MailerLite via le double opt-in
# Pas besoin de send_confirmation_email ni send_welcome_email


def send_new_artwork_newsletter(artwork_data: Dict) -> bool:
    """
    Envoie une campagne newsletter pour une nouvelle œuvre.
    
    Args:
        artwork_data: Dictionnaire contenant les données de l'œuvre
                      (title, description, image_url, price, etc.)
    
    Returns:
        True si la campagne a été envoyée, False sinon
    """
    html_content = render_template(
        "new-artwork.html",
        {
            "title": artwork_data.get("title", "Nouvelle œuvre"),
            "description": artwork_data.get("description", ""),
            "image_url": artwork_data.get("image_url", ""),
            "price": artwork_data.get("price", ""),
            "artwork_url": artwork_data.get("artwork_url", ""),
            "frontend_url": artwork_data.get("frontend_url", ""),
        },
    )
    subject = f"Nouvelle œuvre : {artwork_data.get('title', 'Découvrez notre dernière création')}"
    return send_to_newsletter(subject, html_content)


def send_new_event_newsletter(event_data: Dict) -> bool:
    """
    Envoie une campagne newsletter pour un nouvel événement.
    
    Args:
        event_data: Dictionnaire contenant les données de l'événement
                   (title, description, date, location, image_url, etc.)
    
    Returns:
        True si la campagne a été envoyée, False sinon
    """
    html_content = render_template(
        "new-event.html",
        {
            "title": event_data.get("title", "Nouvel événement"),
            "description": event_data.get("description", ""),
            "date": event_data.get("date", ""),
            "location": event_data.get("location", ""),
            "image_url": event_data.get("image_url", ""),
            "event_url": event_data.get("event_url", ""),
            "frontend_url": event_data.get("frontend_url", ""),
        },
    )
    subject = f"Nouvel événement : {event_data.get('title', 'Rejoignez-nous')}"
    return send_to_newsletter(subject, html_content)
