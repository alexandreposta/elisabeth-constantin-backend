from fastapi import APIRouter, HTTPException, Request, Depends
from typing import List
import stripe
import sys
import os
from app.models.order import Order
from app.crud.orders import create_order, get_order_by_id, update_order_status, get_all_orders, get_orders_by_email as get_orders_by_email_db
from api.auth_admin import require_admin_auth

router = APIRouter()

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

@router.post("/create-payment-intent")
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

@router.post("/confirm-payment")
async def confirm_payment(payment_data: dict):
    """
    Confirme le paiement et met à jour le statut de la commande.
    """
    try:
        payment_intent_id = payment_data.get("payment_intent_id")
        order_id = payment_data.get("order_id")
        
        if not payment_intent_id or not order_id:
            raise HTTPException(status_code=400, detail="Données de paiement incomplètes")
        
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == "succeeded":
            update_order_status(order_id, "paid")
            return {"status": "success", "message": "Paiement confirmé"}
        else:
            update_order_status(order_id, "failed")
            return {"status": "failed", "message": "Paiement échoué"}
            
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/", response_model=List[dict])
def list_orders(_: bool = Depends(require_admin_auth), request: Request = None):
    """
    Retourne toutes les commandes (admin uniquement).
    """
    orders = get_all_orders()
    return [serialize_order(order) for order in orders]

@router.get("/{order_id}", response_model=dict)
def get_order(order_id: str):
    """
    Retourne une commande par son ID.
    """
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return serialize_order(order)

@router.get("/by-email/{email}", response_model=List[dict])
def get_orders_by_email(email: str):
    """
    Retourne les commandes d'un utilisateur par email.
    """
    orders = get_orders_by_email_db(email)
    return [serialize_order(order) for order in orders]

@router.get("/admin/all", response_model=List[dict])
def get_admin_orders(_: bool = Depends(require_admin_auth), request: Request = None):
    """
    Retourne toutes les commandes pour l'administration.
    Endpoint spécifique pour le dashboard admin.
    """
    orders = get_all_orders()
    return [serialize_order(order) for order in orders]
