from typing import List, Optional
from bson.objectid import ObjectId
from app.database import artworks_collection

def get_all_artworks() -> List[dict]:
    """
    Renvoie la liste de toutes les œuvres.
    """
    return list(artworks_collection.find())

def get_artwork_by_id(artwork_id: str) -> Optional[dict]:
    """
    Renvoie une seule œuvre correspondant à l'_id MongoDB.
    """
    try:
        oid = ObjectId(artwork_id)
    except Exception:
        return None
    return artworks_collection.find_one({"_id": oid})

def create_artwork(data: dict) -> str:
    """
    Insère une nouvelle œuvre.
    Retourne l'_id de la nouvelle entrée sous forme de chaîne.
    """
    data = dict(data)
    data.pop("_id", None)
    result = artworks_collection.insert_one(data)
    return str(result.inserted_id)

def update_artwork(artwork_id: str, update_data: dict) -> int:
    """
    Met à jour l'œuvre au _id donné avec les champs de update_data.
    Retourne le nombre de documents modifiés (0 ou 1).
    """
    try:
        oid = ObjectId(artwork_id)
    except Exception as e:
        return 0
    
    update_data = dict(update_data)
    update_data.pop("_id", None)
    
    # Vérifier si l'artwork existe
    existing = artworks_collection.find_one({"_id": oid})
    if not existing:
        return 0
    
    # Comparer les données pour voir s'il y a vraiment des changements
    has_changes = False
    for key, new_value in update_data.items():
        existing_value = existing.get(key)
        if existing_value != new_value:
            has_changes = True
            break
    
    # Si aucun changement, retourner 0 sans faire de requête DB
    if not has_changes:
        return 0
    
    result = artworks_collection.update_one(
        {"_id": oid},
        {"$set": update_data}
    )
    return result.modified_count

def delete_artwork(artwork_id: str) -> int:
    """
    Supprime l'œuvre au _id donné.
    Retourne le nombre de documents supprimés (0 ou 1).
    """
    try:
        oid = ObjectId(artwork_id)
    except Exception:
        return 0
    result = artworks_collection.delete_one({"_id": oid})
    return result.deleted_count

def update_artwork_type(old_type: str, new_type: str) -> int:
    """
    Met à jour le type d'œuvre dans toutes les œuvres ayant l'ancien type.
    Retourne le nombre de documents modifiés.
    """
    
    try:
        # Vérifier d'abord combien d'œuvres ont ce type
        count_before = artworks_collection.count_documents({"type": old_type})
        
        if count_before == 0:
            return 0
        
        # Effectuer la mise à jour
        result = artworks_collection.update_many(
            {"type": old_type},
            {"$set": {"type": new_type}}
        )

        return result.modified_count
        
    except Exception as e:
        return 0
