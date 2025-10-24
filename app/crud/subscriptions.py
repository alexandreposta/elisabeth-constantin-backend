from typing import Optional
from datetime import datetime
from app.database import subscribers_collection


def get_subscription_by_email(email: str) -> Optional[dict]:
    """Retourne l'abonnement correspondant à l'email (ou None)."""
    if subscribers_collection is None:
        return None
    return subscribers_collection.find_one({"email": email.lower()})


def create_subscription(email: str, promo_code: str) -> Optional[str]:
    """Insère un nouvel abonnement et retourne l'id inséré sous forme de string."""
    if subscribers_collection is None:
        return None
    payload = {
        "email": email.lower(),
        "promo_code": promo_code,
        "created_at": datetime.utcnow()
    }
    result = subscribers_collection.insert_one(payload)
    return str(result.inserted_id)


def list_subscriptions(limit: int = 100):
    if subscribers_collection is None:
        return []
    return list(subscribers_collection.find().limit(limit))
