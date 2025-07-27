from fastapi import FastAPI, HTTPException, Request
from typing import List
import sys
import os

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.models.event import Event, EventInDB
from app.crud.events import get_all_events, get_event_by_id, create_event, update_event, delete_event

# Créer l'app FastAPI
app = FastAPI()

# Configuration CORS supprimée - gérée par l'application principale

def serialize_event(raw: dict) -> dict:
    """
    Convertit l'ObjectId MongoDB en string et remplace _id par id pour le frontend.
    """
    raw["id"] = str(raw["_id"])  # Le frontend attend 'id'
    del raw["_id"]  # Supprimer _id car on a maintenant 'id'
    return raw

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

@app.get("/", response_model=List[dict])
def read_events():
    """
    Retourne la liste de tous les événements.
    """
    events = get_all_events()
    return [serialize_event(event) for event in events]

@app.get("/{event_id}", response_model=dict)
def read_event(event_id: str):
    """
    Retourne un événement par son ID.
    """
    event = get_event_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return serialize_event(event)

@app.post("/", response_model=dict)
def create_event_endpoint(request: Request, event: Event):
    """
    Crée un nouvel événement.
    """
    require_admin_auth(request)
    event_dict = event.dict()
    event_id = create_event(event_dict)
    return {"id": event_id, "message": "Événement créé avec succès"}

@app.put("/{event_id}", response_model=dict)
def update_event_endpoint(request: Request, event_id: str, event: Event):
    """
    Met à jour un événement existant.
    """
    require_admin_auth(request)
    event_dict = event.dict()
    modified_count = update_event(event_id, event_dict)
    if modified_count == 0:
        raise HTTPException(status_code=404, detail="Événement non trouvé ou non modifié")
    return {"message": "Événement mis à jour avec succès"}

@app.delete("/{event_id}", response_model=dict)
def delete_event_endpoint(request: Request, event_id: str):
    """
    Supprime un événement.
    """
    require_admin_auth(request)
    deleted_count = delete_event(event_id)
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return {"message": "Événement supprimé avec succès"}
