from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List
from app.models.event import Event
from app.crud.events import get_all_events, get_event_by_id, create_event, update_event, delete_event
from api.auth_admin import require_admin_auth

router = APIRouter()

def serialize_event(raw: dict) -> dict:
    """
    Convertit l'ObjectId MongoDB en string et remplace _id par id pour le frontend.
    """
    raw["id"] = str(raw["_id"])  # Le frontend attend 'id'
    del raw["_id"]  # Supprimer _id car on a maintenant 'id'
    return raw

@router.get("/", response_model=List[dict])
def read_events():
    """
    Retourne la liste de tous les événements.
    """
    events = get_all_events()
    return [serialize_event(event) for event in events]

@router.get("/{event_id}", response_model=dict)
def read_event(event_id: str):
    """
    Retourne un événement par son ID.
    """
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return serialize_event(event)

@router.post("/", response_model=dict)
def create_event_endpoint(event: Event, request: Request = None, _: bool = Depends(require_admin_auth)):
    """
    Crée un nouvel événement.
    """
    event_dict = event.dict()
    event_id = create_event(event_dict)
    created_event = get_event_by_id(event_id)
    if not created_event:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'événement créé")
    return serialize_event(created_event)

@router.put("/{event_id}", response_model=dict)
def update_event_endpoint(event_id: str, event: Event, request: Request = None, _: bool = Depends(require_admin_auth)):
    """
    Met à jour un événement existant.
    """
    event_dict = event.dict()
    modified_count = update_event(event_id, event_dict)
    if modified_count == 0:
        raise HTTPException(status_code=404, detail="Événement non trouvé ou non modifié")
    return {"message": "Événement mis à jour avec succès"}

@router.delete("/{event_id}", response_model=dict)
def delete_event_endpoint(event_id: str, request: Request = None, _: bool = Depends(require_admin_auth)):
    """
    Supprime un événement.
    """
    deleted_count = delete_event(event_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return {"message": "Événement supprimé avec succès"}
