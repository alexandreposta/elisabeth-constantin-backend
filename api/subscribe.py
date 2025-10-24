from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.crud.subscriptions import get_subscription_by_email, create_subscription
import secrets

router = APIRouter()


class SubscribeRequest(BaseModel):
    email: EmailStr


@router.post("/", response_model=dict)
def subscribe(request: SubscribeRequest):
    email = request.email.strip().lower()

    # Vérifier doublon
    existing = get_subscription_by_email(email)
    if existing:
        # Ne pas créer de doublon, retourner code 409
        raise HTTPException(status_code=409, detail="Email déjà abonné")

    # Générer un code promo simple (ex: EC10-AB12C)
    promo_code = f"EC10-{secrets.token_hex(3).upper()}"

    inserted_id = create_subscription(email, promo_code)
    if not inserted_id:
        raise HTTPException(status_code=500, detail="Erreur lors de l'enregistrement de l'abonnement")

    return {"message": "Inscription réussie", "promo_code": promo_code}
