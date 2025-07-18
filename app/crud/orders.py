from typing import List, Optional
from datetime import datetime
from bson.objectid import ObjectId
from app.database import orders_collection

def create_order(order_data: dict) -> str:
    """
    Insère une nouvelle commande.
    Retourne l'_id de la nouvelle entrée sous forme de chaîne.
    """
    order_data = dict(order_data)
    order_data.pop("_id", None)
    result = orders_collection.insert_one(order_data)
    return str(result.inserted_id)

def get_order_by_id(order_id: str) -> Optional[dict]:
    """
    Renvoie une commande correspondant à l'_id MongoDB.
    """
    try:
        oid = ObjectId(order_id)
    except Exception:
        return None
    return orders_collection.find_one({"_id": oid})

def get_orders_by_email(email: str) -> List[dict]:
    """
    Renvoie toutes les commandes d'un email donné.
    """
    return list(orders_collection.find({"buyer_info.email": email}))

def update_order_status(order_id: str, status: str, stripe_payment_intent_id: str = None) -> int:
    """
    Met à jour le statut d'une commande et optionnellement l'ID de paiement Stripe.
    """
    try:
        oid = ObjectId(order_id)
    except Exception:
        return 0
    
    update_data = {"status": status, "updated_at": datetime.now()}
    if stripe_payment_intent_id:
        update_data["stripe_payment_intent_id"] = stripe_payment_intent_id
    
    result = orders_collection.update_one(
        {"_id": oid},
        {"$set": update_data}
    )
    return result.modified_count

def get_all_orders() -> List[dict]:
    """
    Renvoie toutes les commandes (pour l'admin).
    """
    return list(orders_collection.find().sort("created_at", -1))
