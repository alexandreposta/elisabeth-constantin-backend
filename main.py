from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.artworks import router as artworks_router
from app.routes.events import router as events_router
from app.routes.orders import router as orders_router
from app.routes.admin import router as admin_router
import os

# Créer l'application FastAPI
app = FastAPI(
    title="Elisabeth Constantin API",
    description="API pour le site d'art d'Elisabeth Constantin",
    version="1.0.0"
)

# Configuration CORS
frontend_url = os.getenv("FRONTEND_URL")
allowed_origins = [
    frontend_url,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Routes
app.include_router(artworks_router, prefix="/api/artworks", tags=["artworks"])
app.include_router(events_router, prefix="/api/events", tags=["events"])
app.include_router(orders_router, prefix="/api/orders", tags=["orders"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])

@app.get("/")
async def root():
    return {
        "message": "Elisabeth Constantin API - FastAPI",
        "status": "healthy",
        "endpoints": {
            "artworks": "/api/artworks",
            "events": "/api/events", 
            "orders": "/api/orders",
            "admin": "/api/admin"
        }
    }

@app.get("/api")
async def api_root():
    return {
        "message": "Elisabeth Constantin API - FastAPI",
        "status": "healthy",
        "endpoints": {
            "artworks": "/api/artworks",
            "events": "/api/events", 
            "orders": "/api/orders",
            "admin": "/api/admin"
        }
    }