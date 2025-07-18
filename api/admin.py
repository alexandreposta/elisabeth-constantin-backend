from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

# Ajouter le répertoire parent au path pour importer app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.crud import admin


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        url_parts = urlparse(self.path)
        path = url_parts.path
        
        try:
            if path == '/api/admin/login':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                login_data = json.loads(post_data.decode('utf-8'))
                
                # Authentifier l'admin
                token = admin.authenticate_admin(login_data.get('username'), login_data.get('password'))
                
                if token:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"access_token": token, "token_type": "bearer"}).encode())
                else:
                    self.send_error(401, "Invalid credentials")
                    
            else:
                self.send_error(404, "Not found")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_GET(self):
        url_parts = urlparse(self.path)
        path = url_parts.path
        
        try:
            if path == '/api/admin/verify':
                # Vérifier le token d'authentification
                auth_header = self.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                    is_valid = admin.verify_token(token)
                    
                    if is_valid:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        self.wfile.write(json.dumps({"valid": True}).encode())
                    else:
                        self.send_error(401, "Invalid token")
                else:
                    self.send_error(401, "Missing token")
            else:
                self.send_error(404, "Not found")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
