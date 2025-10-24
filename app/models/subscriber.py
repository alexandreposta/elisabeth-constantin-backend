"""
Modèle de données pour les abonnés à la newsletter.
Conforme RGPD avec tracking du consentement.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class SubscriberStatus(str, Enum):
    """Statuts possibles d'un abonné"""
    PENDING = "pending"  # En attente de confirmation (double opt-in)
    CONFIRMED = "confirmed"  # Confirmé et actif
    UNSUBSCRIBED = "unsubscribed"  # Désinscrit
    BOUNCED = "bounced"  # Email invalide (bounce)
    COMPLAINED = "complained"  # Marqué comme spam


class SubscriberSource(str, Enum):
    """Source d'inscription"""
    FRONT_FORM = "front_form"  # Formulaire du site
    ADMIN_IMPORT = "admin_import"  # Import manuel admin
    API = "api"  # API externe


class Subscriber(BaseModel):
    """Modèle d'abonné newsletter"""
    email: EmailStr = Field(..., description="Email de l'abonné (unique)")
    status: SubscriberStatus = Field(default=SubscriberStatus.PENDING, description="Statut de l'abonnement")
    
    # Dates
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Date d'inscription")
    confirmed_at: Optional[datetime] = Field(None, description="Date de confirmation du double opt-in")
    unsubscribed_at: Optional[datetime] = Field(None, description="Date de désinscription")
    
    # Consentement RGPD
    consent_ip: Optional[str] = Field(None, description="Adresse IP lors du consentement")
    consent_user_agent: Optional[str] = Field(None, description="User agent lors du consentement")
    consent_accepted: bool = Field(default=False, description="Consentement explicite accepté")
    
    # Source et métadonnées
    source: SubscriberSource = Field(default=SubscriberSource.FRONT_FORM, description="Source d'inscription")
    promo_code: Optional[str] = Field(None, description="Code promo généré après confirmation")
    
    # Tokens
    confirmation_token: Optional[str] = Field(None, description="Token de confirmation (JWT)")
    unsubscribe_token: Optional[str] = Field(None, description="Token de désinscription (JWT)")
    
    # Statistiques
    emails_sent: int = Field(default=0, description="Nombre d'emails envoyés")
    emails_opened: int = Field(default=0, description="Nombre d'emails ouverts")
    emails_clicked: int = Field(default=0, description="Nombre de clics")
    last_email_sent_at: Optional[datetime] = Field(None, description="Date du dernier email envoyé")
    
    # Raison de désinscription (optionnel)
    unsubscribe_reason: Optional[str] = Field(None, description="Raison de la désinscription")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "client@example.com",
                "status": "confirmed",
                "consent_accepted": True,
                "consent_ip": "192.168.1.1",
                "source": "front_form",
                "promo_code": "EC10-ABC123"
            }
        }


class SubscriberInDB(Subscriber):
    """Modèle d'abonné avec ID MongoDB"""
    id: str = Field(alias="_id")
    
    class Config:
        populate_by_name = True


class SubscribeRequest(BaseModel):
    """Requête d'inscription à la newsletter"""
    email: EmailStr
    consent_accepted: bool = Field(..., description="Consentement RGPD explicite")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "client@example.com",
                "consent_accepted": True
            }
        }


class UnsubscribeRequest(BaseModel):
    """Requête de désinscription"""
    token: str = Field(..., description="Token de désinscription JWT")
    reason: Optional[str] = Field(None, description="Raison de la désinscription")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "reason": "Je ne souhaite plus recevoir d'emails"
            }
        }


class SubscriberStats(BaseModel):
    """Statistiques des abonnés"""
    total: int
    confirmed: int
    pending: int
    unsubscribed: int
    bounced: int
    complained: int
