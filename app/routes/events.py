from fastapi import APIRouter, HTTPException, Request
from app.models.event import Event, EventInDB
from app.crud.events import get_all_events, get_event_by_id, create_event, update_event, delete_event
from app.auth_simple import verify_session
from typing import List

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
def create_event_endpoint(event: Event):
    """
    Crée un nouvel événement.
    """
    event_dict = event.dict()
    event_id = create_event(event_dict)
    return {"id": event_id, "message": "Événement créé avec succès"}

@router.put("/{event_id}", response_model=dict)
def update_event_endpoint(event_id: str, event: Event):
    """
    Met à jour un événement existant.
    """
    event_dict = event.dict()
    modified_count = update_event(event_id, event_dict)
    if modified_count == 0:
        raise HTTPException(status_code=404, detail="Événement non trouvé ou non modifié")
    return {"message": "Événement mis à jour avec succès"}

@router.delete("/{event_id}", response_model=dict)
def delete_event_endpoint(event_id: str):
    """
    Supprime un événement.
    """
    deleted_count = delete_event(event_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return {"message": "Événement supprimé avec succès"}
