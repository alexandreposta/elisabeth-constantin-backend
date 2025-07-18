from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

# Ajouter le répertoire parent au path pour importer app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.crud import events


def serialize_event(raw: dict) -> dict:
    """Convertit le BSON ObjectId en str"""
    return {
        **raw,
        "_id": str(raw["_id"]),
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url_parts = urlparse(self.path)
        path = url_parts.path
        query_params = parse_qs(url_parts.query)
        
        try:
            if path == '/api/events' or path == '/api/events/':
                # Liste tous les événements
                raws = events.get_all_events()
                serialized = [serialize_event(e) for e in raws]
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(serialized).encode())
                
            elif path.startswith('/api/events/'):
                # Événement par ID
                event_id = path.split('/')[-1]
                raw = events.get_event(event_id)
                if raw:
                    serialized = serialize_event(raw)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(serialized).encode())
                else:
                    self.send_error(404, "Event not found")
            else:
                self.send_error(404, "Not found")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_POST(self):
        if self.path == '/api/events' or self.path == '/api/events/':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                event_data = json.loads(post_data.decode('utf-8'))
                
                # Créer l'événement
                new_event = events.create_event(event_data)
                serialized = serialize_event(new_event)
                
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
        if self.path.startswith('/api/events/'):
            try:
                event_id = self.path.split('/')[-1]
                content_length = int(self.headers['Content-Length'])
                put_data = self.rfile.read(content_length)
                update_data = json.loads(put_data.decode('utf-8'))
                
                # Mettre à jour l'événement
                updated = events.update_event(event_id, update_data)
                if updated:
                    serialized = serialize_event(updated)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(serialized).encode())
                else:
                    self.send_error(404, "Event not found")
                    
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not found")
    
    def do_DELETE(self):
        if self.path.startswith('/api/events/'):
            try:
                event_id = self.path.split('/')[-1]
                success = events.delete_event(event_id)
                
                if success:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({"message": "Deleted successfully"}).encode())
                else:
                    self.send_error(404, "Event not found")
                    
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not found")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
