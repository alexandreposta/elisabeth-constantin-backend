from typing import List, Optional
from bson.objectid import ObjectId
from app.database import get_database

def get_database_collection():
    """Récupère la collection artwork_types"""
    database = get_database()
    return database.artwork_types

def get_all_artwork_types() -> List[dict]:
    """
    Renvoie la liste de tous les types d'œuvres actifs.
    """
    collection = get_database_collection()
    types = list(collection.find({"is_active": True}))
    return types

def get_artwork_type_by_name(name: str) -> Optional[dict]:
    """
    Renvoie un type d'œuvre par son nom.
    """
    collection = get_database_collection()
    return collection.find_one({"name": name})

def create_artwork_type(data: dict) -> str:
    """
    Insère un nouveau type d'œuvre.
    Retourne l'_id de la nouvelle entrée sous forme de chaîne.
    """
    collection = get_database_collection()
    
    # Vérifier si le type existe déjà
    existing = collection.find_one({"name": data["name"]})
    if existing:
        return str(existing["_id"])
    
    # Créer le nouveau type
    data = dict(data)
    data.pop("_id", None)
    
    # Valeurs par défaut
    if "display_name" not in data or not data["display_name"]:
        data["display_name"] = data["name"].capitalize()
    if "is_active" not in data:
        data["is_active"] = True
    
    result = collection.insert_one(data)
    return str(result.inserted_id)

def update_artwork_type(type_id: str, update_data: dict) -> int:
    """
    Met à jour un type d'œuvre.
    Retourne le nombre de documents modifiés (0 ou 1).
    """
    try:
        oid = ObjectId(type_id)
    except Exception:
        return 0
    
    collection = get_database_collection()
    update_data = dict(update_data)
    update_data.pop("_id", None)
    
    result = collection.update_one(
        {"_id": oid},
        {"$set": update_data}
    )
    return result.modified_count

def delete_artwork_type(type_id: str) -> int:
    """
    Désactive un type d'œuvre (soft delete).
    Retourne le nombre de documents modifiés (0 ou 1).
    """
    try:
        oid = ObjectId(type_id)
    except Exception:
        return 0
    
    collection = get_database_collection()
    result = collection.update_one(
        {"_id": oid},
        {"$set": {"is_active": False}}
    )
    return result.modified_count

def get_artwork_types_for_api() -> List[str]:
    """
    Retourne une liste simple des noms des types d'œuvres pour l'API.
    Combine les types en base + les types des œuvres existantes pour la compatibilité.
    """
    # Récupérer les types de la collection dédiée
    types_from_db = set()
    try:
        collection = get_database_collection()
        types_docs = list(collection.find({"is_active": True}))
        for type_doc in types_docs:
            types_from_db.add(type_doc["name"])
    except Exception as e:
        pass
    
    # Récupérer aussi les types des œuvres existantes pour la compatibilité
    types_from_artworks = set()
    try:
        from app.crud import artworks
        artworks_data = artworks.get_all_artworks()
        for artwork in artworks_data:
            artwork_type = artwork.get('type', 'peinture')
            types_from_artworks.add(artwork_type)
    except Exception as e:
        pass
    
    # Combiner les deux sources
    all_types = types_from_db.union(types_from_artworks)
    result = sorted(list(all_types))
    
    return result
