from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import artworks, events, orders, admin
import logging
import os
from dotenv import load_dotenv

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Chargement explicite des variables d'environnement
load_dotenv()
stripe_key = os.getenv("STRIPE_SECRET_KEY")
logger.info(f"STRIPE_SECRET_KEY loaded: {'Yes (Production Mode)' if stripe_key and stripe_key.startswith('sk_live_') else 'Yes (Test Mode)' if stripe_key and stripe_key.startswith('sk_test_') else 'No or invalid format'}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(artworks.router, tags=["artworks"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
