from fastapi import APIRouter, HTTPException, Request
import stripe
import os
from app.models.order import Order, OrderInDB
from app.crud.orders import create_order, get_order_by_id, update_order_status, get_all_orders, get_orders_by_email as get_orders_by_email_db
from app.auth_simple import verify_session
from typing import List
import logging

router = APIRouter()

# Configuration Stripe
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = stripe_secret_key
logging.info(f"Initializing Stripe with key: {'sk_live_***' if stripe_secret_key and stripe_secret_key.startswith('sk_live_') else 'sk_test_***' if stripe_secret_key and stripe_secret_key.startswith('sk_test_') else 'Key not found or invalid format'}")

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
        
        # Vérifier les informations de l'acheteur
        required_fields = ['email', 'firstName', 'lastName', 'address', 'city', 'postalCode', 'country']
        missing_fields = []
        
        for field in required_fields:
            if not getattr(order.buyer_info, field, None):
                missing_fields.append(field)
        
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Informations d'acheteur incomplètes. Champs manquants: {', '.join(missing_fields)}"
            )
        
        # Créer l'intention de paiement Stripe
        try:
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
        except stripe.error.CardError as e:
            # Erreurs liées à la carte
            raise HTTPException(status_code=400, detail=f"Erreur de carte: {e.user_message}")
        except stripe.error.RateLimitError:
            # Trop de requêtes effectuées vers l'API Stripe
            raise HTTPException(status_code=429, detail="Trop de requêtes. Veuillez réessayer dans quelques instants.")
        except stripe.error.InvalidRequestError as e:
            # Erreurs de requête invalide
            raise HTTPException(status_code=400, detail=f"Requête invalide: {str(e)}")
        except stripe.error.AuthenticationError:
            # Erreur d'authentification (clé API incorrecte)
            raise HTTPException(status_code=500, detail="Erreur d'authentification avec le système de paiement")
        except stripe.error.APIConnectionError:
            # Erreur de connexion réseau avec Stripe
            raise HTTPException(status_code=503, detail="Impossible de se connecter au système de paiement. Veuillez réessayer plus tard.")
        except stripe.error.StripeError as e:
            # Autres erreurs Stripe
            raise HTTPException(status_code=400, detail=f"Erreur de paiement: {str(e)}")
        
        # Sauvegarder la commande en base
        order_dict = order.dict()
        order_dict['stripe_payment_intent_id'] = intent.id
        order_dict['status'] = 'pending'  # Status initial
        order_id = create_order(order_dict)
        
        return {
            "client_secret": intent.client_secret,
            "order_id": order_id
        }
        
    except HTTPException:
        # Relancer les HTTPExceptions déjà générées
        raise
    except Exception as e:
        # Logger l'erreur pour l'administrateur
        import traceback
        print(f"Erreur inattendue lors de la création du paiement: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Une erreur inattendue s'est produite. Veuillez réessayer.")

@router.post("/confirm-payment")
async def confirm_payment(order_id: str, payment_intent_id: str):
    """
    Confirme le paiement et met à jour le statut de la commande.
    """
    try:
        # Vérifier le paiement avec Stripe
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if intent.status == 'succeeded':
            # Mettre à jour le statut de la commande
            update_order_status(order_id, 'paid', payment_intent_id)
            
            # Récupérer la commande pour marquer les œuvres comme non disponibles
            order = get_order_by_id(order_id)
            if order:
                # Ici on pourrait ajouter la logique pour marquer les œuvres comme vendues
                # dans la collection artworks
                pass
            
            return {"message": "Paiement confirmé", "status": "paid"}
        else:
            return {"message": "Paiement non confirmé", "status": intent.status}
            
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")

@router.get("/{order_id}", response_model=dict)
def get_order(order_id: str):
    """
    Récupère une commande par son ID.
    """
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return serialize_order(order)

@router.get("/", response_model=List[dict])
def get_orders():
    """
    Récupère toutes les commandes (pour l'admin).
    """
    orders = get_all_orders()
    return [serialize_order(order) for order in orders]

@router.put("/{order_id}/status")
def update_order_status_endpoint(order_id: str, status: str):
    """
    Met à jour le statut d'une commande (pour l'admin).
    """
    modified_count = update_order_status(order_id, status)
    if modified_count == 0:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return {"message": "Statut mis à jour avec succès"}

@router.get("/user/{email}", response_model=List[dict])
async def get_orders_by_email(email: str):
    """
    Récupère toutes les commandes d'un utilisateur par son email.
    """
    orders = get_orders_by_email_db(email)
    return [serialize_order(order) for order in orders]

@router.get("/admin/all", response_model=List[dict])
async def get_all_orders_admin():
    """
    Récupère toutes les commandes pour l'administration.
    """
    orders = get_all_orders()
    return [serialize_order(order) for order in orders]

@router.put("/admin/{order_id}/status")
async def update_order_status_admin(order_id: str, status_data: dict):
    """
    Met à jour le statut d'une commande (pour l'admin).
    """
    status = status_data.get("status")
    if status not in ["pending", "paid", "shipped", "delivered", "cancelled"]:
        raise HTTPException(status_code=400, detail="Statut invalide")
    
    modified_count = update_order_status(order_id, status)
    if modified_count == 0:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return {"message": "Statut mis à jour avec succès"}

@router.get("/admin/{order_id}")
async def get_order_details_admin(order_id: str):
    """
    Récupère les détails d'une commande pour l'administration.
    """
    order = get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Commande non trouvée")
    return serialize_order(order)
