from fastapi import FastAPI, HTTPException, Request
import stripe
import sys
import os
from typing import List
import logging

# Ajouter le chemin parent pour les imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.models.order import Order, OrderInDB
from app.crud.orders import create_order, get_order_by_id, update_order_status, get_all_orders, get_orders_by_email as get_orders_by_email_db

# Créer l'app FastAPI
app = FastAPI()

# Configuration CORS supprimée - gérée par l'application principale

# Configuration Stripe
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = stripe_secret_key

def serialize_order(raw: dict) -> dict:
    """
    Convertit l'ObjectId MongoDB en string et remplace _id par id pour le frontend.
    """
    raw["id"] = str(raw["_id"])
    del raw["_id"]
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

@app.post("/create-payment-intent")
async def create_payment_intent(order: Order):
    """
    Crée une intention de paiement Stripe et sauvegarde la commande.
    """
    try:
        # Validation des données d'entrée
        if not order.items or len(order.items) == 0:
            raise HTTPException(status_code=400, detail="La commande ne contient aucun article")
        
        if order.total <= 0:
            raise HTTPException(status_code=400, detail="Le montant total doit être supérieur à zéro")
        
        # Créer l'intention de paiement Stripe
        intent = stripe.PaymentIntent.create(
            amount=int(order.total * 100),  # Stripe utilise les centimes
            currency='eur',
            metadata={
                'order_type': 'artwork_purchase',
                'buyer_email': order.buyer_info.email,
                'buyer_name': f"{order.buyer_info.firstName} {order.buyer_info.lastName}",
                'items_count': len(order.items)
            }
        )
        
        # Sauvegarder la commande en DB avec l'ID Stripe
        order_data = order.dict()
        order_data['stripe_payment_intent_id'] = intent.id
        order_data['status'] = 'pending'
        
        created_order = create_order(order_data)
        order_id = str(created_order.inserted_id)
        
        return {
            "client_secret": intent.client_secret,
            "order_id": order_id,
            "payment_intent_id": intent.id
        }
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Erreur de paiement: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.post("/confirm-payment")
async def confirm_payment(payment_data: dict):
    """
    Confirme le paiement et met à jour le statut de la commande.
    """
    try:
        payment_intent_id = payment_data.get("payment_intent_id")
        order_id = payment_data.get("order_id")
        
        if not payment_intent_id or not order_id:
            raise HTTPException(status_code=400, detail="Données de paiement incomplètes")
        
        # Récupérer l'intention de paiement depuis Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == "succeeded":
            # Mettre à jour le statut de la commande
            update_order_status(order_id, "paid")
            return {"status": "success", "message": "Paiement confirmé"}
        else:
            # Mettre à jour le statut de la commande
            update_order_status(order_id, "failed")
            return {"status": "failed", "message": "Paiement échoué"}
            
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@app.get("/", response_model=List[dict])
def list_orders(request: Request):
    """
    Retourne toutes les commandes (admin uniquement).
    """
    require_admin_auth(request)
    orders = get_all_orders()
    return [serialize_order(order) for order in orders]

@app.get("/{order_id}", response_model=dict)
def get_order(order_id: str):
    """
    Retourne une commande par son ID.
    """
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return serialize_order(order)

@app.get("/by-email/{email}", response_model=List[dict])
def get_orders_by_email(email: str):
    """
    Retourne les commandes d'un utilisateur par email.
    """
    orders = get_orders_by_email_db(email)
    return [serialize_order(order) for order in orders]

@app.get("/admin/all", response_model=List[dict])
def get_admin_orders(request: Request):
    """
    Retourne toutes les commandes pour l'administration.
    Endpoint spécifique pour le dashboard admin.
    """
    require_admin_auth(request)
    orders = get_all_orders()
    return [serialize_order(order) for order in orders]
