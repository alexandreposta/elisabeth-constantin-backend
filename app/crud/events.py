from typing import List, Optional
from bson.objectid import ObjectId
from app.database import events_collection

def get_all_events() -> List[dict]:
    """
    Renvoie la liste de tous les événements.
    """
    return list(events_collection.find())

def get_event_by_id(event_id: str) -> Optional[dict]:
    """
    Renvoie un seul événement correspondant à l'_id MongoDB.
    """
    try:
        oid = ObjectId(event_id)
    except Exception:
        return None
    return events_collection.find_one({"_id": oid})

def create_event(data: dict) -> str:
    """
    Insère un nouvel événement.
    Retourne l'_id de la nouvelle entrée sous forme de chaîne.
    """
    data = dict(data)
    data.pop("_id", None)
    result = events_collection.insert_one(data)
    return str(result.inserted_id)

def update_event(event_id: str, update_data: dict) -> int:
    """
    Met à jour l'événement au _id donné avec les champs de update_data.
    Retourne le nombre de documents modifiés (0 ou 1).
    """
    try:
        oid = ObjectId(event_id)
    except Exception:
        return 0
    update_data = dict(update_data)
    update_data.pop("_id", None)
    result = events_collection.update_one(
        {"_id": oid},
        {"$set": update_data}
    )
    return result.modified_count

def delete_event(event_id: str) -> int:
    """
    Supprime l'événement au _id donné.
    Retourne le nombre de documents supprimés (0 ou 1).
    """
    try:
        oid = ObjectId(event_id)
    except Exception:
        return 0
    result = events_collection.delete_one({"_id": oid})
    return result.deleted_count
