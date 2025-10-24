"""
Utilitaires JWT pour la génération de tokens sécurisés.
Tokens de confirmation et désinscription.
"""

import jwt
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Secret pour signer les JWT (doit être fort et secret)
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGORITHM = "HS256"

# Durées de validité
CONFIRMATION_TOKEN_EXPIRY_HOURS = 48  # 48h pour confirmer
UNSUBSCRIBE_TOKEN_EXPIRY_DAYS = 365  # 1 an pour se désabonner


def generate_confirmation_token(email: str) -> str:
    """
    Génère un token JWT de confirmation d'inscription.
    
    Args:
        email: Email de l'abonné
        
    Returns:
        Token JWT signé
    """
    payload = {
        "email": email.lower(),
        "type": "confirmation",
        "exp": datetime.utcnow() + timedelta(hours=CONFIRMATION_TOKEN_EXPIRY_HOURS),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def generate_unsubscribe_token(email: str) -> str:
    """
    Génère un token JWT de désinscription (longue durée).
    
    Args:
        email: Email de l'abonné
        
    Returns:
        Token JWT signé
    """
    payload = {
        "email": email.lower(),
        "type": "unsubscribe",
        "exp": datetime.utcnow() + timedelta(days=UNSUBSCRIBE_TOKEN_EXPIRY_DAYS),
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str, expected_type: str) -> Optional[Dict]:
    """
    Vérifie et décode un token JWT.
    
    Args:
        token: Token JWT à vérifier
        expected_type: Type de token attendu ('confirmation' ou 'unsubscribe')
        
    Returns:
        Payload décodé si valide, None sinon
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Vérifier le type de token
        if payload.get("type") != expected_type:
            logger.warning(f"Invalid token type: expected {expected_type}, got {payload.get('type')}")
            return None
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}")
        return None


def verify_confirmation_token(token: str) -> Optional[str]:
    """
    Vérifie un token de confirmation.
    
    Args:
        token: Token JWT de confirmation
        
    Returns:
        Email si valide, None sinon
    """
    payload = verify_token(token, "confirmation")
    if payload:
        return payload.get("email")
    return None


def verify_unsubscribe_token(token: str) -> Optional[str]:
    """
    Vérifie un token de désinscription.
    
    Args:
        token: Token JWT de désinscription
        
    Returns:
        Email si valide, None sinon
    """
    payload = verify_token(token, "unsubscribe")
    if payload:
        return payload.get("email")
    return None
