import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import os
from typing import List
from app.crud.newsletter import get_active_subscribers

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    def send_email(self, to_emails: List[str], subject: str, html_content: str):
        """Envoie un email à une liste de destinataires"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            
            for email in to_emails:
                msg = MIMEMultipart()
                msg['From'] = self.email_user
                msg['To'] = email
                msg['Subject'] = subject
                
                msg.attach(MIMEText(html_content, 'html'))
                
                server.send_message(msg)
            
            server.quit()
            return True
        except Exception as e:
            print(f"Erreur envoi email: {e}")
            return False
    
    def generate_artwork_email(self, artwork: dict, unsubscribe_token: str) -> str:
        """Génère le contenu HTML pour un email de nouvelle œuvre"""
        unsubscribe_url = f"{self.frontend_url}/unsubscribe?token={unsubscribe_token}"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Nouvelle œuvre - Elisabeth Constantin</title>
            <style>
                body {{ 
                    font-family: 'Arial', sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    background-color: #f8f9fa; 
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background-color: white; 
                    border-radius: 10px; 
                    overflow: hidden; 
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 30px; 
                    text-align: center; 
                }}
                .header h1 {{ 
                    margin: 0; 
                    font-family: 'Dancing Script', cursive; 
                    font-size: 2.5rem; 
                }}
                .content {{ 
                    padding: 30px; 
                }}
                .artwork-image {{ 
                    width: 100%; 
                    height: 300px; 
                    object-fit: cover; 
                    border-radius: 8px; 
                    margin-bottom: 20px; 
                }}
                .artwork-title {{ 
                    font-size: 1.8rem; 
                    color: #2c3e50; 
                    margin-bottom: 10px; 
                }}
                .artwork-details {{ 
                    color: #5a6c7d; 
                    margin-bottom: 20px; 
                }}
                .cta-button {{ 
                    display: inline-block; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 15px 30px; 
                    text-decoration: none; 
                    border-radius: 25px; 
                    margin: 20px 0; 
                }}
                .discount-banner {{ 
                    background: #e8f5e8; 
                    border: 2px solid #28a745; 
                    padding: 15px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                    text-align: center; 
                    color: #155724; 
                }}
                .footer {{ 
                    background-color: #f8f9fa; 
                    padding: 20px; 
                    text-align: center; 
                    color: #6c757d; 
                    font-size: 0.9rem; 
                }}
                .unsubscribe {{ 
                    margin-top: 20px; 
                    font-size: 0.8rem; 
                }}
                .unsubscribe a {{ 
                    color: #6c757d; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Elisabeth Constantin</h1>
                    <p>Nouvelle œuvre disponible</p>
                </div>
                
                <div class="content">
                    <img src="{artwork.get('main_image', '')}" alt="{artwork.get('title', '')}" class="artwork-image">
                    
                    <h2 class="artwork-title">{artwork.get('title', '')}</h2>
                    
                    <div class="artwork-details">
                        <p><strong>Dimensions:</strong> {artwork.get('width', '')} × {artwork.get('height', '')} cm</p>
                        <p><strong>Type:</strong> {artwork.get('type', '')}</p>
                        <p><strong>Prix:</strong> {artwork.get('price', '')}€</p>
                    </div>
                    
                    <div class="discount-banner">
                        <h3>🎉 Offre spéciale abonnés !</h3>
                        <p>Bénéficiez de <strong>5% de réduction</strong> sur votre première commande</p>
                    </div>
                    
                    <p>{artwork.get('description', '')}</p>
                    
                    <div style="text-align: center;">
                        <a href="{self.frontend_url}/tableau/{artwork.get('_id', '')}" class="cta-button">
                            Voir l'œuvre
                        </a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Merci de votre abonnement à la newsletter d'Elisabeth Constantin</p>
                    <div class="unsubscribe">
                        <a href="{unsubscribe_url}">Se désabonner</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def generate_event_email(self, event: dict, unsubscribe_token: str) -> str:
        """Génère le contenu HTML pour un email de nouvel événement"""
        unsubscribe_url = f"{self.frontend_url}/unsubscribe?token={unsubscribe_token}"
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Nouvel événement - Elisabeth Constantin</title>
            <style>
                body {{ 
                    font-family: 'Arial', sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    background-color: #f8f9fa; 
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background-color: white; 
                    border-radius: 10px; 
                    overflow: hidden; 
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1); 
                }}
                .header {{ 
                    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); 
                    color: white; 
                    padding: 30px; 
                    text-align: center; 
                }}
                .header h1 {{ 
                    margin: 0; 
                    font-family: 'Dancing Script', cursive; 
                    font-size: 2.5rem; 
                }}
                .content {{ 
                    padding: 30px; 
                }}
                .event-image {{ 
                    width: 100%; 
                    height: 250px; 
                    object-fit: cover; 
                    border-radius: 8px; 
                    margin-bottom: 20px; 
                }}
                .event-title {{ 
                    font-size: 1.8rem; 
                    color: #2c3e50; 
                    margin-bottom: 10px; 
                }}
                .event-details {{ 
                    background-color: #f8f9fa; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                }}
                .cta-button {{ 
                    display: inline-block; 
                    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); 
                    color: white; 
                    padding: 15px 30px; 
                    text-decoration: none; 
                    border-radius: 25px; 
                    margin: 20px 0; 
                }}
                .footer {{ 
                    background-color: #f8f9fa; 
                    padding: 20px; 
                    text-align: center; 
                    color: #6c757d; 
                    font-size: 0.9rem; 
                }}
                .unsubscribe {{ 
                    margin-top: 20px; 
                    font-size: 0.8rem; 
                }}
                .unsubscribe a {{ 
                    color: #6c757d; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Elisabeth Constantin</h1>
                    <p>📅 Nouvel événement</p>
                </div>
                
                <div class="content">
                    <img src="{event.get('main_image', '')}" alt="{event.get('title', '')}" class="event-image">
                    
                    <h2 class="event-title">{event.get('title', '')}</h2>
                    
                    <div class="event-details">
                        <p><strong>📍 Lieu:</strong> {event.get('location', '')}</p>
                        <p><strong>📅 Date:</strong> {event.get('start_date', '')} - {event.get('end_date', '')}</p>
                        <p><strong>🕐 Horaires:</strong> {event.get('start_time', '')} - {event.get('end_time', '')}</p>
                    </div>
                    
                    <p>{event.get('description', '')}</p>
                    
                    <div style="text-align: center;">
                        <a href="{self.frontend_url}/evenements" class="cta-button">
                            Voir l'événement
                        </a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Merci de votre abonnement à la newsletter d'Elisabeth Constantin</p>
                    <div class="unsubscribe">
                        <a href="{unsubscribe_url}">Se désabonner</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def notify_new_artwork(self, artwork: dict):
        """Notifie tous les abonnés d'une nouvelle œuvre"""
        try:
            subscribers = get_active_subscribers()
            if not subscribers:
                return True
            
            emails = []
            for subscriber in subscribers:
                emails.append(subscriber['email'])
                # Pour l'instant, on utilise le même token pour tous (à améliorer)
                html_content = self.generate_artwork_email(artwork, subscriber.get('unsubscribe_token', ''))
            
            subject = f"Nouvelle œuvre disponible : {artwork.get('title', '')}"
            return self.send_email(emails, subject, html_content)
        except Exception as e:
            print(f"Erreur notification artwork: {e}")
            return False
    
    def notify_new_event(self, event: dict):
        """Notifie tous les abonnés d'un nouvel événement"""
        try:
            subscribers = get_active_subscribers()
            if not subscribers:
                return True
            
            emails = []
            for subscriber in subscribers:
                emails.append(subscriber['email'])
                # Pour l'instant, on utilise le même token pour tous (à améliorer)
                html_content = self.generate_event_email(event, subscriber.get('unsubscribe_token', ''))
            
            subject = f"Nouvel événement : {event.get('title', '')}"
            return self.send_email(emails, subject, html_content)
        except Exception as e:
            print(f"Erreur notification event: {e}")
            return False

# Instance globale
email_service = EmailService()
