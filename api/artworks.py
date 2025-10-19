from fastapi import APIRouter, HTTPException, Request
from typing import List
from app.models.artwork import Artwork, ArtworkInDB, UpdateTypeRequest
from app.crud import artworks
from fastapi import Depends
from api.auth_admin import require_admin_auth

router = APIRouter()

def serialize_artwork(raw: dict) -> dict:
    """
    Convertit le BSON ObjectId en str pour la sérialisation JSON.
    """
    result = {
        **raw,
        "_id": str(raw["_id"]),
        "other_images": raw.get("other_images", []),
        "status": raw.get("status", "Disponible")
    }
    return result

@router.get("/", response_model=List[ArtworkInDB])
def list_artworks():
    raws = artworks.get_all_artworks()
    serialized = [serialize_artwork(a) for a in raws]
    return serialized

@router.get("/gallery-types", response_model=List[str])
def get_gallery_types():
    """
    Retourne tous les types d'œuvres (pour le menu de navigation)
    """
    # Utiliser la nouvelle logique des types d'œuvres pour le menu
    try:
        from app.crud import artwork_types
        result = artwork_types.get_artwork_types_for_api()
        return result
    except Exception as e:
        # Fallback vers l'ancienne logique - afficher tous les types (pas seulement disponibles)
        artworks_data = artworks.get_all_artworks()
        all_types = set()
        
        for artwork in artworks_data:
            artwork_type = artwork.get('type', 'paint')
            all_types.add(artwork_type)
    
        return sorted(list(all_types))

@router.get("/by-gallery/{gallery_type}", response_model=List[ArtworkInDB])
def get_artworks_by_gallery(gallery_type: str):
    """
    Retourne les œuvres d'un type de galerie spécifique
    """
    artworks_data = artworks.get_all_artworks()
    filtered_artworks = []
    
    # Debug: Logger ce qui est reçu et les types disponibles
    print(f"🔍 DEBUG - Gallery type reçu: '{gallery_type}'")
    all_types = set(a.get('type', 'N/A') for a in artworks_data)
    print(f"🔍 DEBUG - Types disponibles dans DB: {all_types}")
    
    # Normaliser le type de galerie pour la comparaison (insensible à la casse et aux espaces)
    normalized_gallery_type = gallery_type.lower().replace(" ", "").replace("-", "").replace("_", "")
    print(f"🔍 DEBUG - Gallery type normalisé: '{normalized_gallery_type}'")
    
    for artwork in artworks_data:
        # Normaliser le type de l'artwork de la même manière
        artwork_type = artwork.get('type', 'paint')
        normalized_artwork_type = artwork_type.lower().replace(" ", "").replace("-", "").replace("_", "")
        
        # Filtrer seulement par type, pas par statut (afficher toutes les œuvres)
        if normalized_artwork_type == normalized_gallery_type:
            filtered_artworks.append(serialize_artwork(artwork))
    
    print(f"🔍 DEBUG - Nombre d'artworks trouvés: {len(filtered_artworks)}")
    return filtered_artworks

@router.get("/gallery-types/all", response_model=List[str])
def get_all_gallery_types():
    """
    Retourne tous les types d'œuvres existants (pour l'admin)
    """
    # Utiliser la nouvelle logique des types d'œuvres
    try:
        from app.crud import artwork_types
        result = artwork_types.get_artwork_types_for_api()
        return result
    except Exception as e:
        # Fallback vers l'ancienne logique
        artworks_data = artworks.get_all_artworks()
        all_types = set()
        
        for artwork in artworks_data:
            artwork_type = artwork.get('type', 'paint')
            all_types.add(artwork_type)
        
        result = sorted(list(all_types))
        return result

@router.get("/{artwork_id}", response_model=ArtworkInDB)
def get_artwork(artwork_id: str):
    raw = artworks.get_artwork_by_id(artwork_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return serialize_artwork(raw)

@router.post("/", response_model=ArtworkInDB)
def create_artwork(artwork: Artwork, _: bool = Depends(require_admin_auth), request: Request = None):
    created_id = artworks.create_artwork(artwork.dict())
    created_doc = artworks.get_artwork_by_id(created_id)
    if not created_doc:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'œuvre créée")
    return serialize_artwork(created_doc)

@router.put("/{artwork_id}", response_model=ArtworkInDB)
def update_artwork(artwork_id: str, artwork: Artwork, _: bool = Depends(require_admin_auth), request: Request = None):
    # Vérifier d'abord que l'artwork existe
    existing_doc = artworks.get_artwork_by_id(artwork_id)
    if not existing_doc:
        raise HTTPException(status_code=404, detail="Artwork not found")
    
    modified_count = artworks.update_artwork(artwork_id, artwork.dict())
    
    # Si aucune modification n'a été faite, retourner l'artwork existant
    # (cela peut arriver si les données sont identiques)
    if modified_count == 0:
        return serialize_artwork(existing_doc)
    
    # Sinon, récupérer l'artwork mis à jour
    updated_doc = artworks.get_artwork_by_id(artwork_id)
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Artwork not found after update")
    return serialize_artwork(updated_doc)

@router.delete("/{artwork_id}")
def delete_artwork(artwork_id: str, _: bool = Depends(require_admin_auth), request: Request = None):
    deleted = artworks.delete_artwork(artwork_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return {"message": "Artwork deleted successfully"}

@router.put("/update-type")
def update_artwork_type(type_request: UpdateTypeRequest, _: bool = Depends(require_admin_auth), request: Request = None):
    """
    Met à jour un type d'œuvre dans toutes les œuvres
    """
    try:
        updated_count = artworks.update_artwork_type(type_request.oldType, type_request.newType)
        return {"success": True, "updated": updated_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
