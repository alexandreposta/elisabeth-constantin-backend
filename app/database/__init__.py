from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
DB_NAME   = os.getenv("MONGO_DB", "site_maman")

client = MongoClient(MONGO_URI)
db     = client[DB_NAME]
artworks_collection = db["artworks"]
events_collection = db["events"]
orders_collection = db["orders"]
artwork_types_collection = db["artwork_types"]

def get_database():
    """Retourne l'instance de la base de données MongoDB"""
    return db
