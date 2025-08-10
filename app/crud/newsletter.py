from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
import secrets
import hashlib
from typing import List, Optional

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["site_maman"]
newsletter_collection = db["newsletter_subscriptions"]

def generate_unsubscribe_token(email: str) -> str:
    """Génère un token unique pour le désabonnement"""
    secret = secrets.token_urlsafe(32)
    return hashlib.sha256(f"{email}_{secret}".encode()).hexdigest()

def subscribe_to_newsletter(email: str) -> str:
    """Ajoute un email à la newsletter"""
    # Vérifier si l'email existe déjà
    existing = newsletter_collection.find_one({"email": email})
    if existing:
        if existing.get("is_active", False):
            raise ValueError("Email déjà abonné")
        else:
            # Réactiver l'abonnement
            newsletter_collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "is_active": True,
                        "subscribed_at": datetime.utcnow(),
                        "unsubscribe_token": generate_unsubscribe_token(email)
                    }
                }
            )
            return str(existing["_id"])
    
    # Créer un nouvel abonnement
    subscription = {
        "email": email,
        "subscribed_at": datetime.utcnow(),
        "is_active": True,
        "unsubscribe_token": generate_unsubscribe_token(email)
    }
    result = newsletter_collection.insert_one(subscription)
    return str(result.inserted_id)

def unsubscribe_from_newsletter(token: str) -> bool:
    """Désabonne un email via son token"""
    result = newsletter_collection.update_one(
        {"unsubscribe_token": token, "is_active": True},
        {"$set": {"is_active": False}}
    )
    return result.modified_count > 0

def get_active_subscribers() -> List[dict]:
    """Récupère tous les abonnés actifs"""
    subscribers = list(newsletter_collection.find({"is_active": True}))
    for subscriber in subscribers:
        subscriber["id"] = str(subscriber["_id"])
        del subscriber["_id"]
    return subscribers

def is_email_subscribed(email: str) -> bool:
    """Vérifie si un email est abonné"""
    return newsletter_collection.find_one({"email": email, "is_active": True}) is not None

def get_newsletter_stats() -> dict:
    """Récupère les statistiques de la newsletter"""
    total_subscribers = newsletter_collection.count_documents({"is_active": True})
    total_unsubscribed = newsletter_collection.count_documents({"is_active": False})
    
    return {
        "total_subscribers": total_subscribers,
        "total_unsubscribed": total_unsubscribed,
        "total_emails": total_subscribers + total_unsubscribed
    }

def check_email_subscribed(email: str) -> bool:
    """Vérifie si un email est abonné à la newsletter"""
    subscriber = newsletter_collection.find_one({"email": email, "is_active": True})
    return subscriber is not None
