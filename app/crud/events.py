from typing import List, Optional
from bson.objectid import ObjectId
from app.database import events_collection

TRANSLATABLE_FIELDS = {"title", "description", "location", "status"}

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
    
    # Vérifier si l'événement existe
    existing = events_collection.find_one({"_id": oid})
    if not existing:
        return 0
    
    # Comparer les données pour voir s'il y a vraiment des changements
    has_changes = False
    changed_fields = []
    for key, new_value in update_data.items():
        existing_value = existing.get(key)
        if existing_value != new_value:
            has_changes = True
            changed_fields.append(key)
    
    # Si aucun changement, retourner 0 sans faire de requête DB
    if not has_changes:
        return 0
    
    update_payload = {"$set": update_data}
    translations = existing.get("translations", {})
    unset_fields = {}
    if translations.get("en"):
        for field in changed_fields:
            if field in TRANSLATABLE_FIELDS:
                unset_fields[f"translations.en.{field}"] = ""
    if unset_fields:
        update_payload["$unset"] = unset_fields

    result = events_collection.update_one(
        {"_id": oid},
        update_payload
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
