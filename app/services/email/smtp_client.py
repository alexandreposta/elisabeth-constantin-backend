"""
Client SMTP pour l'envoi d'emails transactionnels.
Utilise smtplib pour envoyer des emails de confirmation, bienvenue, etc.
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration SMTP depuis .env
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@elisabeth-constantin.fr")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Elisabeth Constantin")


def send_email_smtp(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None
) -> bool:
    """
    Envoie un email via SMTP.
    
    Args:
        to_email: Adresse email du destinataire
        subject: Sujet de l'email
        html_content: Contenu HTML de l'email
        from_email: Adresse d'expédition (optionnel)
        from_name: Nom de l'expéditeur (optionnel)
        
    Returns:
        True si envoyé avec succès, False sinon
    """
    # Vérifier la configuration SMTP
    if not SMTP_HOST or not SMTP_USERNAME or not SMTP_PASSWORD:
        logger.warning(
            "SMTP not configured. Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD in .env"
        )
        logger.info(f"Email NOT sent to {to_email}: {subject}")
        return False
    
    from_email = from_email or SMTP_FROM_EMAIL
    from_name = from_name or SMTP_FROM_NAME
    
    try:
        # Créer le message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = to_email
        
        # Ajouter le contenu HTML
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Envoyer via SMTP
        logger.info(f"Sending email via SMTP to {to_email}: {subject}")
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Email sent successfully to {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error(f"SMTP authentication failed. Check SMTP_USERNAME and SMTP_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email to {to_email}: {e}")
        return False
