from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks, Query
from typing import List
from app.models.event import Event
from app.crud.events import get_all_events, get_event_by_id, create_event, update_event, delete_event
from api.auth_admin import require_admin_auth
from app.services.email.notifications import notify_new_event
from app.database import events_collection
from app.services.translation import apply_dynamic_translations

SUPPORTED_LANGUAGES = {"fr", "en"}
TRANSLATABLE_EVENT_FIELDS = ("title", "description", "location", "status")


def resolve_language(lang: str) -> str:
    if not lang:
        return "fr"
    normalized = lang.lower()
    return normalized if normalized in SUPPORTED_LANGUAGES else "fr"

router = APIRouter()

def serialize_event(raw: dict, lang: str = "fr") -> dict:
    """
    Convertit l'ObjectId MongoDB en string et remplace _id par id pour le frontend.
    """
    translated = apply_dynamic_translations(raw, TRANSLATABLE_EVENT_FIELDS, lang, events_collection)
    event_payload = dict(translated)
    event_payload["id"] = str(translated["_id"])
    event_payload.pop("_id", None)
    return event_payload

@router.get("/", response_model=List[dict])
def read_events(lang: str = Query("fr")):
    """
    Retourne la liste de tous les événements.
    """
    language = resolve_language(lang)
    events = get_all_events()
    return [serialize_event(event, language) for event in events]

@router.get("/{event_id}", response_model=dict)
def read_event(event_id: str, lang: str = Query("fr")):
    """
    Retourne un événement par son ID.
    """
    language = resolve_language(lang)
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return serialize_event(event, language)

@router.post("/", response_model=dict)
def create_event_endpoint(
    event: Event,
    background_tasks: BackgroundTasks,
    request: Request = None,
    _: bool = Depends(require_admin_auth)
):
    """
    Crée un nouvel événement.
    """
    event_dict = event.dict()
    event_id = create_event(event_dict)
    created_event = get_event_by_id(event_id)
    if not created_event:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'événement créé")
    background_tasks.add_task(notify_new_event, event_id)
    return serialize_event(created_event)

@router.put("/{event_id}", response_model=dict)
def update_event_endpoint(event_id: str, event: Event, request: Request = None, _: bool = Depends(require_admin_auth)):
    """
    Met à jour un événement existant.
    """
    # Vérifier d'abord que l'événement existe
    existing_event = get_event_by_id(event_id)
    if not existing_event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    event_dict = event.dict()
    modified_count = update_event(event_id, event_dict)
    
    # Si aucune modification n'a été faite, retourner un succès
    # (cela peut arriver si les données sont identiques)
    if modified_count == 0:
        return {"message": "Événement inchangé", "event": serialize_event(existing_event)}
    
    # Sinon, récupérer l'événement mis à jour et le retourner
    updated_event = get_event_by_id(event_id)
    if not updated_event:
        raise HTTPException(status_code=404, detail="Événement non trouvé après mise à jour")
    
    return {"message": "Événement mis à jour avec succès", "event": serialize_event(updated_event)}

@router.delete("/{event_id}", response_model=dict)
def delete_event_endpoint(event_id: str, request: Request = None, _: bool = Depends(require_admin_auth)):
    """
    Supprime un événement.
    """
    deleted_count = delete_event(event_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return {"message": "Événement supprimé avec succès"}
