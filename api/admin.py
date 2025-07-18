from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import urlparse

# Ajouter le répertoire parent au path pour importer app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import auth_simple
from api.cors_utils import apply_cors_headers

def get_client_ip(handler_instance):
    """Récupère l'IP du client"""
    forwarded = handler_instance.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return handler_instance.headers.get('X-Real-IP', 'unknown')

def set_secure_cookie(handler_instance, name: str, value: str, max_age: int = 7200):
    """Configure un cookie sécurisé"""
    cookie_header = f"{name}={value}; Path=/; Max-Age={max_age}; HttpOnly; Secure; SameSite=Strict"
    handler_instance.send_header('Set-Cookie', cookie_header)

def get_cookie(handler_instance, name: str) -> str:
    """Récupère un cookie"""
    cookie_header = handler_instance.headers.get('Cookie', '')
    for cookie in cookie_header.split(';'):
        if '=' in cookie:
            key, val = cookie.strip().split('=', 1)
            if key == name:
                return val
    return None


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        url_parts = urlparse(self.path)
        path = url_parts.path
        
        try:
            if path == '/api/admin/login':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                login_data = json.loads(post_data.decode('utf-8'))
                
                # Authentification simple
                username = login_data.get('username')
                password = login_data.get('password')
                
                if auth_simple.authenticate_admin(username, password):
                    # Créer la session
                    ip_address = get_client_ip(self)
                    user_agent = self.headers.get('User-Agent', 'unknown')
                    session_id = auth_simple.create_session(ip_address, user_agent)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    apply_cors_headers(self, self.headers.get('Origin'))
                    
                    # Cookie sécurisé (2 heures = 7200 secondes)
                    set_secure_cookie(self, 'admin_session', session_id, 7200)
                    
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": True,
                        "message": "Connexion réussie"
                    }).encode())
                else:
                    # Log tentative échouée
                    ip_address = get_client_ip(self)
                    user_agent = self.headers.get('User-Agent', 'unknown')
                    auth_simple.log_admin_activity("FAILED_LOGIN", ip_address, user_agent, f"Invalid credentials for: {username}")
                    
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json')
                    apply_cors_headers(self, self.headers.get('Origin'))
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": False,
                        "message": "Identifiants invalides"
                    }).encode())
                    
            elif path == '/api/admin/logout':
                # Récupérer le session ID du cookie
                session_id = get_cookie(self, 'admin_session')
                
                if session_id:
                    auth_simple.invalidate_session(session_id)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                apply_cors_headers(self, self.headers.get('Origin'))
                
                # Supprimer le cookie
                set_secure_cookie(self, 'admin_session', '', 0)
                
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": True,
                    "message": "Déconnexion réussie"
                }).encode())
                
            else:
                self.send_error(404, "Not found")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_GET(self):
        url_parts = urlparse(self.path)
        path = url_parts.path
        
        try:
            if path == '/api/admin/verify':
                # Vérifier la session via le cookie
                session_id = get_cookie(self, 'admin_session')
                ip_address = get_client_ip(self)
                
                if auth_simple.verify_session(session_id, ip_address):
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    apply_cors_headers(self, self.headers.get('Origin'))
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "valid": True,
                        "username": auth_simple.ADMIN_USERNAME
                    }).encode())
                else:
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json')
                    apply_cors_headers(self, self.headers.get('Origin'))
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "valid": False,
                        "message": "Session invalide ou expirée"
                    }).encode())
            else:
                self.send_error(404, "Not found")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_OPTIONS(self):
        self.send_response(200)
        apply_cors_headers(self, self.headers.get('Origin'))
        self.end_headers()
