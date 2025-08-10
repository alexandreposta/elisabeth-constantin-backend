from fastapi import APIRouter, HTTPException, Request
from typing import List
from app.models.artwork_type import ArtworkType, ArtworkTypeInDB, CreateArtworkTypeRequest
from app.crud import artwork_types
from fastapi import Depends
from api.auth_admin import require_admin_auth

router = APIRouter()

def serialize_artwork_type(raw: dict) -> dict:
    """
    Convertit le BSON ObjectId en str, 
    pour que Pydantic puisse le mapper dans `id`.
    """
    return {
        **raw,
        "_id": str(raw["_id"]),
    }

@router.get("/", response_model=List[str])
def get_artwork_types():
    """
    Retourne tous les types d'œuvres actifs (noms uniquement)
    """
    return artwork_types.get_artwork_types_for_api()

@router.get("/detailed", response_model=List[ArtworkTypeInDB])
def get_artwork_types_detailed():
    """
    Retourne tous les types d'œuvres avec détails complets
    """
    raws = artwork_types.get_all_artwork_types()
    serialized = [serialize_artwork_type(a) for a in raws]
    return serialized

@router.post("/", response_model=ArtworkTypeInDB)
def create_artwork_type(type_request: CreateArtworkTypeRequest, _: bool = Depends(require_admin_auth)):
    """
    Crée un nouveau type d'œuvre
    """
    # Vérifier si le type existe déjà
    existing = artwork_types.get_artwork_type_by_name(type_request.name)
    if existing:
        return serialize_artwork_type(existing)
    
    created_id = artwork_types.create_artwork_type(type_request.dict())
    created_doc = artwork_types.get_artwork_type_by_name(type_request.name)
    
    if not created_doc:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération du type créé")
    
    return serialize_artwork_type(created_doc)

@router.delete("/{type_name}")
def delete_artwork_type(type_name: str, _: bool = Depends(require_admin_auth)):
    """
    Désactive un type d'œuvre
    """
    # Trouver le type par nom
    type_doc = artwork_types.get_artwork_type_by_name(type_name)
    if not type_doc:
        raise HTTPException(status_code=404, detail="Type d'œuvre introuvable")
    
    # Soft delete
    deleted = artwork_types.delete_artwork_type(str(type_doc["_id"]))
    if not deleted:
        raise HTTPException(status_code=404, detail="Type d'œuvre introuvable")
    
    return {"message": "Type d'œuvre supprimé avec succès"}

@router.post("/ensure-defaults")
def ensure_default_types(_: bool = Depends(require_admin_auth)):
    """
    S'assure que les types par défaut existent
    """
    artwork_types.ensure_default_artwork_types()
    return {"message": "Types par défaut initialisés"}
