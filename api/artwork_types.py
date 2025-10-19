from fastapi import APIRouter, HTTPException
from typing import List
from fastapi import Depends
from pydantic import BaseModel
from api.auth_admin import require_admin_auth
from app.crud import artworks as artworks_crud
from app.crud import artwork_types as types_crud

router = APIRouter()

class UpdateTypeRequest(BaseModel):
    newType: str

class CreateTypeRequest(BaseModel):
    name: str

@router.get("/", response_model=List[str])
def get_artwork_types():
    """
    Retourne tous les types d'œuvres (de la collection + des artworks)
    """
    return types_crud.get_artwork_types_for_api()

@router.post("/")
def create_artwork_type(request: CreateTypeRequest, _: bool = Depends(require_admin_auth)):
    """
    Crée un nouveau type d'œuvre dans la collection artwork_types
    """
    type_name = request.name.strip()
    
    if not type_name:
        raise HTTPException(status_code=400, detail="Le nom du type ne peut pas être vide")
    
    # Vérifier si le type existe déjà
    existing = types_crud.get_artwork_type_by_name(type_name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Le type '{type_name}' existe déjà"
        )
    
    # Créer le type
    type_data = {
        "name": type_name,
        "display_name": type_name.capitalize(),
        "is_active": True
    }
    types_crud.create_artwork_type(type_data)
    
    return {
        "message": f"Type '{type_name}' créé avec succès",
        "type": type_name
    }

@router.delete("/{type_name}")
def delete_artwork_type(type_name: str, _: bool = Depends(require_admin_auth)):
    """
    Supprime un type d'œuvre et met à null le type de tous les artworks concernés
    """
    # Vérifier si le type existe
    existing = types_crud.get_artwork_type_by_name(type_name)
    
    # Mettre à null le type de tous les artworks ayant ce type
    modified_count = artworks_crud.update_artwork_type(type_name, None)
    
    # Supprimer de la collection artwork_types si existe
    if existing:
        from bson.objectid import ObjectId
        types_crud.delete_artwork_type(str(existing["_id"]))
    
    return {
        "message": f"Type '{type_name}' supprimé avec succès",
        "artworks_updated": modified_count
    }

@router.put("/{type_name}")
def update_artwork_type_endpoint(type_name: str, request: UpdateTypeRequest, _: bool = Depends(require_admin_auth)):
    """
    Modifie un type d'œuvre et applique le changement à tous les artworks concernés
    """
    new_type = request.newType.strip()
    
    if not new_type:
        raise HTTPException(status_code=400, detail="Le nouveau nom de type ne peut pas être vide")
    
    if type_name == new_type:
        raise HTTPException(status_code=400, detail="Le nouveau type doit être différent de l'ancien")
    
    # Vérifier si le nouveau type existe déjà
    existing_new = types_crud.get_artwork_type_by_name(new_type)
    if existing_new:
        raise HTTPException(
            status_code=400,
            detail=f"Le type '{new_type}' existe déjà. Utilisez un nom différent."
        )
    
    # Mettre à jour dans la collection artwork_types
    existing_old = types_crud.get_artwork_type_by_name(type_name)
    if existing_old:
        from bson.objectid import ObjectId
        types_crud.update_artwork_type(str(existing_old["_id"]), {"name": new_type})
    else:
        # Créer le nouveau type s'il n'existe pas
        types_crud.create_artwork_type({
            "name": new_type,
            "display_name": new_type.capitalize(),
            "is_active": True
        })
    
    # Mettre à jour le type de tous les artworks
    modified_count = artworks_crud.update_artwork_type(type_name, new_type)
    
    return {
        "message": f"Type '{type_name}' modifié en '{new_type}' avec succès",
        "artworks_updated": modified_count
    }
