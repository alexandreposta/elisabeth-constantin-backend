from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os

from .artworks import router as artworks_router
from .artwork_types import router as artwork_types_router
from .events import router as events_router
from .orders import router as orders_router
from .dashboard import router as dashboard_router
from .auth_admin import router as auth_router

app = FastAPI(
    title="Elisabeth Constantin API",
    description="API pour le site d'art d'Elisabeth Constantin",
    version="1.0.0"
)

# Configuration CORS
allowed_origins_str = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",")]

# Si on utilise "*" (wildcard), désactiver credentials
allow_credentials = "*" not in allowed_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth_router, prefix="/api/admin", tags=["admin-auth"])
app.include_router(dashboard_router, prefix="/api/admin", tags=["admin-dashboard"])
app.include_router(artworks_router, prefix="/api/artworks", tags=["artworks"])
app.include_router(artwork_types_router, prefix="/api/artwork-types", tags=["artwork-types"])
app.include_router(events_router, prefix="/api/events", tags=["events"])
app.include_router(orders_router, prefix="/api/orders", tags=["orders"])

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

# Export pour Vercel avec Mangum (adaptateur ASGI pour serverless)
handler = Mangum(app)
