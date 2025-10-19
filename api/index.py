from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
# FRONTEND_URL can be a single origin or a comma-separated list of origins.
# If not set, we fallback to a safe policy. Note: using "*" with allow_credentials=True
# is not allowed by browsers, so we dynamically set allow_credentials.
frontend_url = os.getenv("FRONTEND_URL", "")
if frontend_url:
    # Accept comma-separated origins (useful for staging + production)
    allowed_origins = [o.strip() for o in frontend_url.split(",") if o.strip()]
else:
    # TEMPORARY FIX: Allow production domain by default if FRONTEND_URL not set
    allowed_origins = ["https://elisabeth-constantin.fr", "http://localhost:5173"]

# If the list contains a wildcard, disable credentials (browsers block credentials with '*')
allow_credentials_flag = True
if "*" in allowed_origins:
    allow_credentials_flag = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials_flag,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

# Export pour Vercel
handler = app
