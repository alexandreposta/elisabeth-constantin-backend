# app/routes/artworks.py
from fastapi import APIRouter, HTTPException
from typing import List
from app.models.artwork import Artwork, ArtworkInDB, UpdateTypeRequest
from app.crud import artworks

router = APIRouter(prefix="/artworks")


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


@router.get("/by-gallery/{gallery_type}", response_model=List[ArtworkInDB])
def get_artworks_by_gallery(gallery_type: str):
    """
    Retourne les œuvres d'un type spécifique
    """
    artworks_data = artworks.get_all_artworks()
    filtered_artworks = []
    
    for artwork in artworks_data:
        if artwork.get('type', 'paint') == gallery_type and artwork.get('is_available', True):
            filtered_artworks.append(serialize_artwork(artwork))
    
    return filtered_artworks


@router.put("/update-type", response_model=dict)
def update_artwork_type(request: UpdateTypeRequest):
    """
    Met à jour un type d'œuvre dans toutes les œuvres
    """
    print("=== DEBUT update_artwork_type ===")
    print(f"Request reçu: {request}")
    print(f"Type du request: {type(request)}")
    print(f"oldType: {request.oldType} (type: {type(request.oldType)})")
    print(f"newType: {request.newType} (type: {type(request.newType)})")
    
    try:
        # Mettre à jour toutes les œuvres ayant l'ancien type
        print("Appel de artworks.update_artwork_type...")
        updated_count = artworks.update_artwork_type(request.oldType, request.newType)
        print(f"Nombre d'œuvres mises à jour: {updated_count}")
        
        result = {"success": True, "updated": updated_count}
        print(f"Résultat à retourner: {result}")
        print("=== FIN update_artwork_type (succès) ===")
        return result
    
    except Exception as e:
        print("=== ERREUR update_artwork_type ===")
        print(f"Exception: {e}")
        print(f"Type d'exception: {type(e)}")
        print(f"Args: {e.args}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        print("=== FIN ERREUR update_artwork_type ===")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la mise à jour: {str(e)}")


@router.get("/{artwork_id}", response_model=ArtworkInDB)
def get_artwork(artwork_id: str):
    raw = artworks.get_artwork_by_id(artwork_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_artwork(raw)


@router.post("/", response_model=dict)
def create_artwork(art: Artwork):
    # art.id sera ignoré ici, on utilise art.dict(by_alias=True)
    payload = art.dict()
    new_id = artworks.create_artwork(payload)
    return {"id": str(new_id)}


@router.put("/{artwork_id}", response_model=dict)
def update_artwork(artwork_id: str, art: Artwork):
    print(f"Tentative de mise à jour de l'œuvre {artwork_id}")
    print(f"Données reçues: {art.dict()}")
    
    payload = art.dict()
    updated = artworks.update_artwork(artwork_id, payload)
    
    print(f"Résultat de la mise à jour: {updated}")
    
    if updated == 0:
        print(f"Aucune œuvre trouvée avec l'ID {artwork_id}")
        raise HTTPException(status_code=404, detail="Not updated")
    return {"updated": True}


@router.delete("/{artwork_id}", response_model=dict)
def delete_artwork(artwork_id: str):
    deleted = artworks.delete_artwork(artwork_id)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Not deleted")
    return {"deleted": True}
