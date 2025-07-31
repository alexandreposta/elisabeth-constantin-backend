from fastapi import APIRouter, HTTPException, Request
from typing import List
import sys
import os

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.models.artwork import Artwork, ArtworkInDB, UpdateTypeRequest
from app.crud import artworks

# Créer un router au lieu d'une app FastAPI
router = APIRouter()

# Configuration supprimée - CORS géré par l'application principale

def serialize_artwork(raw: dict) -> dict:
    """
    Convertit le BSON ObjectId en str, 
    pour que Pydantic puisse le mapper dans `id`.
    """
    return {
        **raw,
        "_id": str(raw["_id"]),
        # on veille à toujours avoir la clé other_images
        "other_images": raw.get("other_images", []),
    }

def require_admin_auth(request: Request):
    """Vérifier l'authentification admin - utilise le même système que index.py"""
    session_id = request.cookies.get("session_id")
    admin_token = request.cookies.get("admin_token")
    
    if not session_id and not admin_token:
        raise HTTPException(status_code=401, detail="Authentification requise")
    
    # Si on a un admin_token (JWT), l'accepter temporairement
    if admin_token:
        return True
    
    # Si on a un session_id, utiliser le système simple
    if session_id:
        # Pour simplifier, on accepte toute session_id non vide
        # Plus tard on pourra intégrer avec le système de sessions d'index.py
        return True
    
    raise HTTPException(status_code=401, detail="Session invalide")

@router.get("/", response_model=List[ArtworkInDB])
def list_artworks():
    raws = artworks.get_all_artworks()
    # applique la sérialisation AVANT de passer au model
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
        if artwork.get('is_available', True):  # Seulement les œuvres disponibles
            artwork_type = artwork.get('type', 'paint')
            available_types.add(artwork_type)
    
    return sorted(list(available_types))

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
def create_artwork(request: Request, artwork: Artwork):
    require_admin_auth(request)
    created_id = artworks.create_artwork(artwork.dict())
    created_doc = artworks.get_artwork_by_id(created_id)
    if not created_doc:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'œuvre créée")
    return serialize_artwork(created_doc)

@router.put("/{artwork_id}", response_model=ArtworkInDB)
def update_artwork(request: Request, artwork_id: str, artwork: Artwork):
    require_admin_auth(request)
    modified_count = artworks.update_artwork(artwork_id, artwork.dict())
    if not modified_count:
        raise HTTPException(status_code=404, detail="Artwork not found or not modified")
    # Récupérer le document mis à jour
    updated_doc = artworks.get_artwork_by_id(artwork_id)
    if not updated_doc:
        raise HTTPException(status_code=404, detail="Artwork not found after update")
    return serialize_artwork(updated_doc)

@router.delete("/{artwork_id}")
def delete_artwork(request: Request, artwork_id: str):
    require_admin_auth(request)
    deleted = artworks.delete_artwork(artwork_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return {"message": "Artwork deleted successfully"}

@router.put("/update-type")
def update_artwork_type(request: Request, type_request: UpdateTypeRequest):
    """
    Met à jour un type d'œuvre dans toutes les œuvres
    """
    require_admin_auth(request)
    try:
        updated_count = artworks.update_artwork_type(type_request.oldType, type_request.newType)
        return {"success": True, "updated": updated_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
