from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from typing import List
from app.models.artwork import Artwork, ArtworkInDB, UpdateTypeRequest
from app.crud import artworks
from app.utils.string_utils import normalize_string
from fastapi import Depends
from api.auth_admin import require_admin_auth
from app.services.email.notifications import notify_new_artwork, notify_removed_artwork
import logging

logger = logging.getLogger(__name__)
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
    Retourne tous les types d'œuvres uniques depuis les artworks
    """
    artworks_data = artworks.get_all_artworks()
    all_types = set()
    
    for artwork in artworks_data:
        artwork_type = artwork.get('type', 'peinture')
        all_types.add(artwork_type)

    return sorted(list(all_types))

@router.get("/by-gallery/{gallery_type}", response_model=List[ArtworkInDB])
def get_artworks_by_gallery(gallery_type: str):
    """
    Retourne les œuvres d'un type de galerie spécifique
    """
    artworks_data = artworks.get_all_artworks()
    filtered_artworks = []
    
    # Normaliser le type de galerie pour la comparaison (insensible à la casse, accents, espaces et caractères spéciaux)
    normalized_gallery_type = normalize_string(gallery_type)
    
    for artwork in artworks_data:
        # Normaliser le type de l'artwork de la même manière
        artwork_type = artwork.get('type', '') or ''
        normalized_artwork_type = normalize_string(artwork_type)
        
        # Filtrer seulement par type, pas par statut (afficher toutes les œuvres)
        if normalized_artwork_type == normalized_gallery_type:
            filtered_artworks.append(serialize_artwork(artwork))
    
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
def create_artwork(
    artwork: Artwork,
    background_tasks: BackgroundTasks,
    _: bool = Depends(require_admin_auth),
    request: Request = None
):
    """
    Crée une nouvelle œuvre et notifie les abonnés à la newsletter.
    """
    created_id = artworks.create_artwork(artwork.dict())
    created_doc = artworks.get_artwork_by_id(created_id)
    if not created_doc:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'œuvre créée")
    
    # Ajouter la tâche de notification en arrière-plan
    background_tasks.add_task(notify_new_artwork, created_id)
    logger.info(f"📧 Scheduled newsletter notification for new artwork: {created_id}")
    
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
def delete_artwork(
    artwork_id: str,
    background_tasks: BackgroundTasks,
    _: bool = Depends(require_admin_auth),
    request: Request = None
):
    """
    Supprime une œuvre et notifie les abonnés à la newsletter.
    """
    # Récupérer l'artwork AVANT de le supprimer (pour l'email)
    artwork_data = artworks.get_artwork_by_id(artwork_id)
    if not artwork_data:
        raise HTTPException(status_code=404, detail="Artwork not found")
    
    # Supprimer l'artwork
    deleted = artworks.delete_artwork(artwork_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artwork not found")
    
    # Ajouter la tâche de notification en arrière-plan
    # Passer les données de l'artwork (car il est supprimé)
    background_tasks.add_task(notify_removed_artwork, serialize_artwork(artwork_data))
    logger.info(f"📧 Scheduled newsletter notification for removed artwork: {artwork_id}")
    
    return {"message": "Artwork deleted successfully"}

@router.put("/type/update")
def update_artwork_type(type_request: UpdateTypeRequest, _: bool = Depends(require_admin_auth), request: Request = None):
    """
    Met à jour un type d'œuvre dans toutes les œuvres
    """
    try:
        updated_count = artworks.update_artwork_type(type_request.oldType, type_request.newType)
        return {"success": True, "updated": updated_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
