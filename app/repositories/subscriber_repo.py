"""
Repository pour la gestion des abonnés à la newsletter.
CRUD complet avec gestion RGPD et statistiques.
"""

from typing import Optional, List, Dict
from datetime import datetime
from bson import ObjectId
from app.database import subscribers_collection
from app.models.subscriber import SubscriberStatus, SubscriberSource
import logging

logger = logging.getLogger(__name__)


class SubscriberRepository:
    """Repository pour les abonnés newsletter"""
    
    def __init__(self):
        self.collection = subscribers_collection
    
    def get_by_email(self, email: str) -> Optional[Dict]:
        """Récupère un abonné par son email"""
        if self.collection is None:
            return None
        return self.collection.find_one({"email": email.lower()})
    
    def get_by_id(self, subscriber_id: str) -> Optional[Dict]:
        """Récupère un abonné par son ID"""
        if self.collection is None:
            return None
        try:
            return self.collection.find_one({"_id": ObjectId(subscriber_id)})
        except Exception as e:
            logger.error(f"Error getting subscriber by ID: {e}")
            return None
    
    def create(self, subscriber_data: Dict) -> Optional[str]:
        """
        Crée un nouvel abonné.
        
        Args:
            subscriber_data: Données de l'abonné
            
        Returns:
            ID de l'abonné créé ou None si erreur
        """
        if self.collection is None:
            return None
        
        try:
            # Normaliser l'email
            subscriber_data["email"] = subscriber_data["email"].lower()
            
            # Vérifier que l'email n'existe pas déjà
            existing = self.get_by_email(subscriber_data["email"])
            if existing:
                logger.warning(f"Subscriber already exists: {subscriber_data['email']}")
                return None
            
            # Ajouter timestamp
            subscriber_data["created_at"] = datetime.utcnow()
            
            result = self.collection.insert_one(subscriber_data)
            logger.info(f"✅ Subscriber created: {subscriber_data['email']}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating subscriber: {e}")
            return None
    
    def update(self, email: str, update_data: Dict) -> bool:
        """
        Met à jour un abonné.
        
        Args:
            email: Email de l'abonné
            update_data: Données à mettre à jour
            
        Returns:
            True si mise à jour réussie, False sinon
        """
        if self.collection is None:
            return False
        
        try:
            result = self.collection.update_one(
                {"email": email.lower()},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating subscriber: {e}")
            return False
    
    def confirm(self, email: str, promo_code: str) -> bool:
        """
        Confirme un abonné (double opt-in validé).
        
        Args:
            email: Email de l'abonné
            promo_code: Code promo à attribuer
            
        Returns:
            True si confirmation réussie, False sinon
        """
        update_data = {
            "status": SubscriberStatus.CONFIRMED.value,
            "confirmed_at": datetime.utcnow(),
            "promo_code": promo_code
        }
        
        success = self.update(email, update_data)
        if success:
            logger.info(f"✅ Subscriber confirmed: {email}")
        return success
    
    def unsubscribe(self, email: str, reason: Optional[str] = None) -> bool:
        """
        Désinscrit un abonné.
        
        Args:
            email: Email de l'abonné
            reason: Raison de la désinscription (optionnel)
            
        Returns:
            True si désinscription réussie, False sinon
        """
        update_data = {
            "status": SubscriberStatus.UNSUBSCRIBED.value,
            "unsubscribed_at": datetime.utcnow()
        }
        
        if reason:
            update_data["unsubscribe_reason"] = reason
        
        success = self.update(email, update_data)
        if success:
            logger.info(f"📭 Subscriber unsubscribed: {email}")
        return success
    
    def mark_bounced(self, email: str) -> bool:
        """Marque un abonné comme bounced (email invalide)"""
        update_data = {
            "status": SubscriberStatus.BOUNCED.value
        }
        return self.update(email, update_data)
    
    def mark_complained(self, email: str) -> bool:
        """Marque un abonné comme ayant signalé du spam"""
        update_data = {
            "status": SubscriberStatus.COMPLAINED.value
        }
        return self.update(email, update_data)
    
    def increment_email_stats(
        self,
        email: str,
        sent: bool = False,
        opened: bool = False,
        clicked: bool = False
    ) -> bool:
        """
        Incrémente les statistiques d'emails.
        
        Args:
            email: Email de l'abonné
            sent: Email envoyé
            opened: Email ouvert
            clicked: Lien cliqué
            
        Returns:
            True si mise à jour réussie, False sinon
        """
        if self.collection is None:
            return False
        
        try:
            update = {}
            if sent:
                update["$inc"] = {"emails_sent": 1}
                update["$set"] = {"last_email_sent_at": datetime.utcnow()}
            if opened:
                update["$inc"] = update.get("$inc", {})
                update["$inc"]["emails_opened"] = 1
            if clicked:
                update["$inc"] = update.get("$inc", {})
                update["$inc"]["emails_clicked"] = 1
            
            if update:
                result = self.collection.update_one(
                    {"email": email.lower()},
                    update
                )
                return result.modified_count > 0
            return False
            
        except Exception as e:
            logger.error(f"Error updating email stats: {e}")
            return False
    
    def get_active_subscribers(self) -> List[Dict]:
        """
        Récupère tous les abonnés actifs (confirmés et non désinscrits).
        
        Returns:
            Liste des abonnés actifs
        """
        if self.collection is None:
            return []
        
        try:
            subscribers = list(self.collection.find({
                "status": SubscriberStatus.CONFIRMED.value
            }))
            return subscribers
        except Exception as e:
            logger.error(f"Error getting active subscribers: {e}")
            return []
    
    def get_all(self, limit: int = 1000, skip: int = 0) -> List[Dict]:
        """Récupère tous les abonnés avec pagination"""
        if self.collection is None:
            return []
        
        try:
            return list(self.collection.find().skip(skip).limit(limit))
        except Exception as e:
            logger.error(f"Error getting all subscribers: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """
        Récupère les statistiques des abonnés.
        
        Returns:
            Dictionnaire avec les statistiques
        """
        if self.collection is None:
            return {
                "total": 0,
                "confirmed": 0,
                "pending": 0,
                "unsubscribed": 0,
                "bounced": 0,
                "complained": 0
            }
        
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            stats = {
                "total": sum(r["count"] for r in results),
                "confirmed": 0,
                "pending": 0,
                "unsubscribed": 0,
                "bounced": 0,
                "complained": 0
            }
            
            for result in results:
                status = result["_id"]
                count = result["count"]
                
                if status == SubscriberStatus.CONFIRMED.value:
                    stats["confirmed"] = count
                elif status == SubscriberStatus.PENDING.value:
                    stats["pending"] = count
                elif status == SubscriberStatus.UNSUBSCRIBED.value:
                    stats["unsubscribed"] = count
                elif status == SubscriberStatus.BOUNCED.value:
                    stats["bounced"] = count
                elif status == SubscriberStatus.COMPLAINED.value:
                    stats["complained"] = count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting subscriber stats: {e}")
            return {
                "total": 0,
                "confirmed": 0,
                "pending": 0,
                "unsubscribed": 0,
                "bounced": 0,
                "complained": 0
            }
    
    def delete(self, email: str) -> bool:
        """
        Supprime définitivement un abonné (RGPD - droit à l'oubli).
        
        Args:
            email: Email de l'abonné
            
        Returns:
            True si suppression réussie, False sinon
        """
        if self.collection is None:
            return False
        
        try:
            result = self.collection.delete_one({"email": email.lower()})
            if result.deleted_count > 0:
                logger.info(f"🗑️ Subscriber deleted (RGPD): {email}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting subscriber: {e}")
            return False


# Instance globale du repository
subscriber_repo = SubscriberRepository()
