# index.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from .artworks import router as artworks_router
from .events import router as events_router
from .orders import router as orders_router
from .dashboard import router as dashboard_router
from .auth_admin import router as auth_router


app = FastAPI(
    title="Elisabeth Constantin API",
    description="API du site d'art d'Elisabeth Constantin",
    version="1.0.0"
)

# CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:5173", "http://127.0.0.1:5173",
        "https://elisabeth-constantin.fr", "https://www.elisabeth-constantin.fr",
        "https://elisabeth-constantin.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/admin", tags=["admin"])
app.include_router(artworks_router, prefix="/api/artworks", tags=["artworks"])
app.include_router(events_router, prefix="/api/events", tags=["events"])
app.include_router(orders_router, prefix="/api/orders", tags=["orders"])
app.include_router(dashboard_router, prefix="/api/admin")


@app.get("/")
def root():
    return {
        "message": "Elisabeth Constantin API - FastAPI",
        "status": "healthy",
        "version": "1.0.0"
    }
