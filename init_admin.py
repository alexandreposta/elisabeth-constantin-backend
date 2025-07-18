#!/usr/bin/env python3
"""
Script d'initialisation pour créer le premier admin
"""
import sys
import os
import asyncio
from datetime import datetime

# Ajouter le répertoire racine au PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importer les modules nécessaires
from pymongo import MongoClient
from passlib.context import CryptContext
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
DB_NAME = os.getenv("MONGO_DB", "site_maman")

# Configuration du hashage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def init_admin():
    """Initialise le premier admin super utilisateur"""
    
    try:
        # Connexion à MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db["admins"]
        
        # Vérifier si un admin existe déjà
        existing_admin = collection.find_one({"username": "admin"})
        if existing_admin:
            print("✅ Un admin existe déjà dans la base de données.")
            print(f"   Nom d'utilisateur: {existing_admin['username']}")
            print(f"   Email: {existing_admin['email']}")
            print(f"   Rôle: {existing_admin['role']}")
            return True
        
        # Créer le premier admin
        hashed_password = get_password_hash("12345")
        
        admin_data = {
            "username": "admin",
            "email": "admin@example.com",
            "hashed_password": hashed_password,
            "role": "super_admin",
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": None
        }
        
        result = collection.insert_one(admin_data)
        
        print("🎉 Admin créé avec succès !")
        print(f"   ID: {result.inserted_id}")
        print(f"   Nom d'utilisateur: admin")
        print(f"   Email: admin@example.com")
        print(f"   Mot de passe: 12345")
        print(f"   Rôle: super_admin")
        print("\n🔗 Vous pouvez maintenant vous connecter sur:")
        print("   http://localhost:3000/admin/login")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de l'admin: {e}")
        return False

if __name__ == "__main__":
    success = init_admin()
    sys.exit(0 if success else 1)
