from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import sys
import os

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.models.artwork import Artwork, ArtworkInDB, UpdateTypeRequest
from app.crud import artworks
from app.auth_simple import verify_session

# Créer l'app FastAPI
app = FastAPI()

# Configuration CORS
frontend_url = os.getenv("FRONTEND_URL")
allowed_origins = [
    frontend_url,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

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
    """Vérifier l'authentification admin"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentification requise")
    
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "unknown")
    
    if not verify_session(session_id, ip_address, user_agent):
        raise HTTPException(status_code=401, detail="Session invalide")
    
    return True

@app.get("/", response_model=List[ArtworkInDB])
def list_artworks():
    raws = artworks.get_all_artworks()
    # applique la sérialisation AVANT de passer au model
    serialized = [serialize_artwork(a) for a in raws]
    return serialized

@app.get("/gallery-types", response_model=List[str])
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

@app.get("/gallery-types/all", response_model=List[str])
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

@app.get("/{artwork_id}", response_model=ArtworkInDB)
def get_artwork(artwork_id: str):
    raw = artworks.get_artwork_by_id(artwork_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return serialize_artwork(raw)

@app.post("/", response_model=ArtworkInDB)
def create_artwork(request: Request, artwork: Artwork):
    require_admin_auth(request)
    created = artworks.create_artwork(artwork.dict())
    return serialize_artwork(created)

@app.put("/{artwork_id}", response_model=ArtworkInDB)
def update_artwork(request: Request, artwork_id: str, artwork: Artwork):
    require_admin_auth(request)
    updated = artworks.update_artwork(artwork_id, artwork.dict())
    if not updated:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return serialize_artwork(updated)

@app.delete("/{artwork_id}")
def delete_artwork(request: Request, artwork_id: str):
    require_admin_auth(request)
    deleted = artworks.delete_artwork(artwork_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artwork not found")
    return {"message": "Artwork deleted successfully"}

@app.put("/update-type")
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
