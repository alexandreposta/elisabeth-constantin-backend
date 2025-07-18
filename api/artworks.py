from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

# Ajouter le répertoire parent au path pour importer app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.crud import artworks
from app.models.artwork import Artwork
from api.cors_utils import apply_cors_headers


def serialize_artwork(raw: dict) -> dict:
    """Convertit le BSON ObjectId en str"""
    return {
        **raw,
        "_id": str(raw["_id"]),
        "other_images": raw.get("other_images", []),
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url_parts = urlparse(self.path)
        path = url_parts.path
        query_params = parse_qs(url_parts.query)
        
        try:
            if path == '/api/artworks' or path == '/api/artworks/':
                # Liste toutes les œuvres
                raws = artworks.get_all_artworks()
                serialized = [serialize_artwork(a) for a in raws]
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                apply_cors_headers(self, self.headers.get('Origin'))
                self.end_headers()
                self.wfile.write(json.dumps(serialized).encode())
                
            elif path == '/api/artworks/gallery-types':
                # Types de galerie
                types = artworks.get_gallery_types()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(types).encode())
                
            elif path.startswith('/api/artworks/'):
                # Œuvre par ID
                artwork_id = path.split('/')[-1]
                raw = artworks.get_artwork(artwork_id)
                if raw:
                    serialized = serialize_artwork(raw)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(serialized).encode())
                else:
                    self.send_error(404, "Artwork not found")
            else:
                self.send_error(404, "Not found")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_POST(self):
        if self.path == '/api/artworks' or self.path == '/api/artworks/':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                artwork_data = json.loads(post_data.decode('utf-8'))
                
                # Créer l'œuvre
                new_artwork = artworks.create_artwork(artwork_data)
                serialized = serialize_artwork(new_artwork)
                
                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(serialized).encode())
                
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not found")
    
    def do_PUT(self):
        if self.path.startswith('/api/artworks/'):
            try:
                artwork_id = self.path.split('/')[-1]
                content_length = int(self.headers['Content-Length'])
                put_data = self.rfile.read(content_length)
                update_data = json.loads(put_data.decode('utf-8'))
                
                # Mettre à jour l'œuvre
                updated = artworks.update_artwork(artwork_id, update_data)
                if updated:
                    serialized = serialize_artwork(updated)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(serialized).encode())
                else:
                    self.send_error(404, "Artwork not found")
                    
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not found")
    
    def do_DELETE(self):
        if self.path.startswith('/api/artworks/'):
            try:
                artwork_id = self.path.split('/')[-1]
                success = artworks.delete_artwork(artwork_id)
                
                if success:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"message": "Deleted successfully"}).encode())
                else:
                    self.send_error(404, "Artwork not found")
                    
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not found")
    
    def do_OPTIONS(self):
        self.send_response(200)
        # CORS sécurisé - seulement votre domaine frontend
        origin = self.headers.get('Origin')
        allowed_origins = [
            'https://elisabeth-constantin-frontend.vercel.app',
            'https://site-maman-frontend.vercel.app',
        ]
        
        if origin in allowed_origins:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', 'https://elisabeth-constantin-frontend.vercel.app')
            
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()
