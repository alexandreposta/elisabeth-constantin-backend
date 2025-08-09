from fastapi import APIRouter, HTTPException, Request
from typing import List
from app.models.artwork import Artwork, ArtworkInDB, UpdateTypeRequest
from app.crud import artworks
from fastapi import Depends
from api.auth_admin import require_admin_auth

router = APIRouter()

def serialize_artwork(raw: dict) -> dict:
    """
    Convertit le BSON ObjectId en str, 
    pour que Pydantic puisse le mapper dans `id`.
    """
    return {
        **raw,
        "_id": str(raw["_id"]),
        "other_images": raw.get("other_images", []),
    }

@router.get("/", response_model=List[ArtworkInDB])
def list_artworks():
    raws = artworks.get_all_artworks()
    serialized = [serialize_artwork(a) for a in raws]
    return serialized

@router.get("/gallery-types", response_model=List[str])
def get_gallery_types():
    """
    Retourne les types d'œuvres qui ont au moins une œuvre disponible
    """
    artworks_data = artworks.get_all_artworks()
    available_types = set()
    
    for artwork in artworks_data:
        if artwork.get('is_available', True):
            artwork_type = artwork.get('type', 'paint')
            available_types.add(artwork_type)
    
    return sorted(list(available_types))

@router.get("/by-gallery/{gallery_type}", response_model=List[ArtworkInDB])
def get_artworks_by_gallery(gallery_type: str):
    """
    Retourne les œuvres d'un type de galerie spécifique
    """
    artworks_data = artworks.get_all_artworks()
    filtered_artworks = []
    
    for artwork in artworks_data:
        if artwork.get('is_available', True) and artwork.get('type', 'paint') == gallery_type:
            filtered_artworks.append(serialize_artwork(artwork))
    
    return filtered_artworks

@router.get("/gallery-types/all", response_model=List[str])
def get_all_gallery_types():
    """
    Retourne tous les types d'œuvres existants (pour l'admin)
    """
    artworks_data = artworks.get_all_artworks()
    all_types = set()
    
    for artwork in artworks_data:
        artwork_type = artwork.get('type', 'paint')
        all_types.add(artwork_type)
    
    return sorted(list(all_types))

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
    modified_count = artworks.update_artwork(artwork_id, artwork.dict())
    if not modified_count:
        raise HTTPException(status_code=404, detail="Artwork not found or not modified")
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
