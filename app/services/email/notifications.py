"""
Notifications email pour les œuvres et événements via MailerLite.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from app.crud import artworks as artworks_crud
from app.crud import events as events_crud
from app.repositories.subscriber_repo import subscriber_repo
from app.services.email.mailerlite_client import render_template, send_to_newsletter

logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BASE_FRONTEND_URL = FRONTEND_URL.split(",")[0].strip() if FRONTEND_URL else "http://localhost:5173"
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def _format_price(price: Optional[float]) -> str:
    if price is None:
        return "Prix sur demande"
    return f"{price:.0f} €"


def _format_date(date_value: Any) -> str:
    try:
        if isinstance(date_value, datetime):
            parsed = date_value
        else:
            parsed = datetime.fromisoformat(str(date_value))
        months = [
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ]
        return f"{parsed.day} {months[parsed.month - 1]} {parsed.year}"
    except Exception:
        return str(date_value)


def _format_dimensions(width: Any, height: Any) -> str:
    if width and height:
        return f"{width} x {height} cm"
    if width or height:
        return f"{width or height} cm"
    return ""


def _update_stats_on_success(sent_count: int):
    if sent_count <= 0:
        return
    for subscriber in subscriber_repo.get_active_subscribers():
        subscriber_repo.increment_email_stats(subscriber.get("email"), sent=True)


def notify_new_artwork(artwork_id: str) -> Dict[str, Any]:
    logger.info("📧 Preparing newsletter for new artwork %s", artwork_id)

    artwork = artworks_crud.get_artwork_by_id(artwork_id)
    if not artwork:
        logger.error("Artwork not found: %s", artwork_id)
        return {"sent": 0, "failed": 1, "errors": ["Artwork not found"]}

    art_link = f"{BASE_FRONTEND_URL}/tableau/{artwork_id}"
    subject = f"Nouvelle œuvre : {artwork.get('title')}"

    # Récupérer tous les abonnés actifs pour générer les URLs de désinscription personnalisées
    subscribers = subscriber_repo.get_active_subscribers()
    if not subscribers:
        logger.warning("No active subscribers found")
        return {"sent": 0, "failed": 0, "errors": []}

    # Envoyer l'email à chaque subscriber individuellement avec son token unique
    sent_count = 0
    errors = []
    
    for subscriber in subscribers:
        unsubscribe_token = subscriber.get("unsubscribe_token")
        if not unsubscribe_token:
            logger.warning(f"No unsubscribe token for {subscriber.get('email')}")
            continue
            
        unsubscribe_url = f"{BACKEND_URL}/api/newsletter/unsubscribe?token={unsubscribe_token}"
        
        html = render_template(
            "new-artwork.html",
            {
                "title": artwork.get("title", "Nouvelle œuvre"),
                "description": (artwork.get("description") or "")[:320],
                "price": _format_price(artwork.get("price")),
                "image_url": artwork.get("main_image") or artwork.get("image_url") or "",
                "link": art_link,
                "dimensions": _format_dimensions(artwork.get("width"), artwork.get("height")),
                "unsubscribe_url": unsubscribe_url,
            },
        )

        if not html:
            errors.append(f"Template render failed for {subscriber.get('email')}")
            continue

        sent = send_to_newsletter(subject, html)
        if sent:
            sent_count += 1
        else:
            errors.append(f"Send failed for {subscriber.get('email')}")

    _update_stats_on_success(sent_count)
    return {"sent": sent_count, "failed": len(errors), "errors": errors}


def notify_removed_artwork(artwork_data: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("📧 Preparing newsletter for removed artwork %s", artwork_data.get("title"))

    art_link = BASE_FRONTEND_URL
    subject = f"Dernière chance : {artwork_data.get('title', 'Œuvre retirée')}"
    html = render_template(
        "removed-artwork.html",
        {
            "title": artwork_data.get("title", "Œuvre retirée"),
            "description": (artwork_data.get("description") or "")[:320],
            "image_url": artwork_data.get("main_image") or artwork_data.get("image_url") or "",
            "link": art_link,
        },
    )

    if not html:
        return {"sent": 0, "failed": 1, "errors": ["Template removed-artwork introuvable"]}

    sent = send_to_newsletter(subject, html)
    _update_stats_on_success(1 if sent else 0)
    return {"sent": 1 if sent else 0, "failed": 0 if sent else 1, "errors": [] if sent else ["MailerLite send failed"]}


def notify_new_event(event_id: str) -> Dict[str, Any]:
    logger.info("📧 Preparing newsletter for new event %s", event_id)
    event = events_crud.get_event_by_id(event_id)
    if not event:
        logger.error("Event not found: %s", event_id)
        return {"sent": 0, "failed": 1, "errors": ["Event not found"]}

    event_link = f"{BASE_FRONTEND_URL}/evenements"
    schedule = f"{_format_date(event.get('start_date'))} - {_format_date(event.get('end_date'))}"
    time_range = f"{event.get('start_time', '')} - {event.get('end_time', '')}"

    # Récupérer tous les abonnés actifs pour générer les URLs de désinscription personnalisées
    subscribers = subscriber_repo.get_active_subscribers()
    if not subscribers:
        logger.warning("No active subscribers found")
        return {"sent": 0, "failed": 0, "errors": []}

    # Envoyer l'email à chaque subscriber individuellement avec son token unique
    sent_count = 0
    errors = []
    
    for subscriber in subscribers:
        unsubscribe_token = subscriber.get("unsubscribe_token")
        if not unsubscribe_token:
            logger.warning(f"No unsubscribe token for {subscriber.get('email')}")
            continue
            
        unsubscribe_url = f"{BACKEND_URL}/api/newsletter/unsubscribe?token={unsubscribe_token}"
        
        html = render_template(
            "new-event.html",
            {
                "title": event.get("title", "Nouvel événement"),
                "description": (event.get("description") or "")[:320],
                "image_url": event.get("main_image") or "",
                "link": event_link,
                "location": event.get("location", ""),
                "schedule": schedule,
                "time_range": time_range,
                "unsubscribe_url": unsubscribe_url,
            },
        )

        if not html:
            errors.append(f"Template render failed for {subscriber.get('email')}")
            continue

        subject = f"Événement à venir : {event.get('title')}"
        sent = send_to_newsletter(subject, html)
        if sent:
            sent_count += 1
        else:
            errors.append(f"Send failed for {subscriber.get('email')}")

    _update_stats_on_success(sent_count)
    return {"sent": sent_count, "failed": len(errors), "errors": errors}
