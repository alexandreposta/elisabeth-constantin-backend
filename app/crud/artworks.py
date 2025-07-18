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
    print(f"DEBUG: Tentative de mise à jour de l'œuvre avec ID: {artwork_id}")
    try:
        oid = ObjectId(artwork_id)
        print(f"DEBUG: ObjectId créé avec succès: {oid}")
    except Exception as e:
        print(f"DEBUG: Erreur lors de la création de l'ObjectId: {e}")
        return 0
    
    update_data = dict(update_data)
    update_data.pop("_id", None)
    print(f"DEBUG: Données à mettre à jour: {update_data}")
    
    # Vérifier si l'artwork existe
    existing = artworks_collection.find_one({"_id": oid})
    if not existing:
        print(f"DEBUG: Aucune œuvre trouvée avec l'ID {oid}")
        return 0
    
    print(f"DEBUG: Œuvre trouvée: {existing['title']}")
    
    result = artworks_collection.update_one(
        {"_id": oid},
        {"$set": update_data}
    )
    print(f"DEBUG: Résultat de la mise à jour: matched={result.matched_count}, modified={result.modified_count}")
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
    print("=== DEBUT update_artwork_type (CRUD) ===")
    print(f"old_type: '{old_type}' (type: {type(old_type)})")
    print(f"new_type: '{new_type}' (type: {type(new_type)})")
    
    try:
        # Vérifier d'abord combien d'œuvres ont ce type
        count_before = artworks_collection.count_documents({"type": old_type})
        print(f"Nombre d'œuvres avec le type '{old_type}': {count_before}")
        
        if count_before == 0:
            print("Aucune œuvre trouvée avec ce type, pas de mise à jour nécessaire")
            return 0
        
        # Afficher quelques exemples d'œuvres qui vont être mises à jour
        examples = list(artworks_collection.find({"type": old_type}).limit(3))
        print(f"Exemples d'œuvres à mettre à jour:")
        for example in examples:
            print(f"  - {example.get('title', 'Sans titre')} (ID: {example['_id']})")
        
        # Effectuer la mise à jour
        print("Exécution de la mise à jour...")
        result = artworks_collection.update_many(
            {"type": old_type},
            {"$set": {"type": new_type}}
        )
        
        print(f"Résultat MongoDB:")
        print(f"  - matched_count: {result.matched_count}")
        print(f"  - modified_count: {result.modified_count}")
        
        # Vérifier le résultat
        count_after_old = artworks_collection.count_documents({"type": old_type})
        count_after_new = artworks_collection.count_documents({"type": new_type})
        print(f"Après mise à jour:")
        print(f"  - Œuvres avec ancien type '{old_type}': {count_after_old}")
        print(f"  - Œuvres avec nouveau type '{new_type}': {count_after_new}")
        
        print("=== FIN update_artwork_type (CRUD) succès ===")
        return result.modified_count
        
    except Exception as e:
        print("=== ERREUR update_artwork_type (CRUD) ===")
        print(f"Exception: {e}")
        print(f"Type d'exception: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        print("=== FIN ERREUR update_artwork_type (CRUD) ===")
        return 0
