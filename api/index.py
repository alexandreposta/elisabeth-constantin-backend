from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Créer l'application FastAPI
app = FastAPI(
    title="Elisabeth Constantin API",
    description="API pour le site d'art d'Elisabeth Constantin",
    version="1.0.0"
)

# Configuration CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [
    frontend_url,
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # Si jamais vous utilisez un autre port
    "http://127.0.0.1:3000",
    "https://elisabeth-constantin.vercel.app",  # URL de production probable
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/")
async def health_check():
    return {
        "message": "Elisabeth Constantin API - FastAPI",
        "status": "healthy",
        "version": "1.0.0",
        "endpoints": {
            "artworks": "/api/artworks",
            "events": "/api/events", 
            "orders": "/api/orders",
            "admin": "/api/admin"
        }
    }

@app.get("/health")
async def health():
    return {"status": "ok", "message": "API is running"}
