from dotenv import load_dotenv
import os
from pymongo import MongoClient
import sys

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME   = os.getenv("MONGO_DB", "site_maman")

if not MONGO_URI:
    print("⚠️ ERROR: MONGO_URI environment variable not set!", file=sys.stderr)
    print("⚠️ Backend will not work without MongoDB connection.", file=sys.stderr)
    # Pour éviter le crash complet, on met une URI dummy (mais ça ne fonctionnera pas)
    MONGO_URI = "mongodb://localhost:27017/"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    # Test de connexion
    client.server_info()
    db = client[DB_NAME]
    artworks_collection = db["artworks"]
    events_collection = db["events"]
    orders_collection = db["orders"]
    artwork_types_collection = db["artwork_types"]
    print("✅ MongoDB connected successfully")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}", file=sys.stderr)
    # Créer des collections dummy pour éviter le crash
    db = None
    artworks_collection = None
    events_collection = None
    orders_collection = None
    artwork_types_collection = None

def get_database():
    """Retourne l'instance de la base de données MongoDB"""
    if db is None:
        raise Exception("Database not connected. Check MONGO_URI environment variable.")
    return db
