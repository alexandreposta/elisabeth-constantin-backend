from http.server import BaseHTTPRequestHandler
import json
import os
import sys
from urllib.parse import urlparse, parse_qs

# Ajouter le répertoire parent au path pour importer app
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.crud import orders


def serialize_order(raw: dict) -> dict:
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
            if path == '/api/orders' or path == '/api/orders/':
                # Liste toutes les commandes
                raws = orders.get_all_orders()
                serialized = [serialize_order(o) for o in raws]
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(serialized).encode())
                
            elif path.startswith('/api/orders/'):
                # Commande par ID
                order_id = path.split('/')[-1]
                raw = orders.get_order(order_id)
                if raw:
                    serialized = serialize_order(raw)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(serialized).encode())
                else:
                    self.send_error(404, "Order not found")
            else:
                self.send_error(404, "Not found")
                
        except Exception as e:
            self.send_error(500, str(e))
    
    def do_POST(self):
        if self.path == '/api/orders' or self.path == '/api/orders/':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                order_data = json.loads(post_data.decode('utf-8'))
                
                # Créer la commande
                new_order = orders.create_order(order_data)
                serialized = serialize_order(new_order)
                
                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(serialized).encode())
                
            except Exception as e:
                self.send_error(500, str(e))
        elif self.path == '/api/orders/create-payment-intent':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                payment_data = json.loads(post_data.decode('utf-8'))
                
                # Créer l'intent de paiement Stripe
                payment_intent = orders.create_payment_intent(payment_data)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(payment_intent).encode())
                
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Not found")
    
    def do_PUT(self):
        url_parts = urlparse(self.path)
        path = url_parts.path
        
        if path.startswith('/api/orders/'):
            try:
                order_id = path.split('/')[-1]
                content_length = int(self.headers['Content-Length'])
                put_data = self.rfile.read(content_length)
                update_data = json.loads(put_data.decode('utf-8'))
                
                # Mettre à jour la commande
                updated = orders.update_order(order_id, update_data)
                if updated:
                    serialized = serialize_order(updated)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps(serialized).encode())
                else:
                    self.send_error(404, "Order not found")
                    
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
