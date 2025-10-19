"""
Endpoint de santé minimal pour tester si Vercel fonctionne
"""
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Backend is alive!"}

@app.get("/api")
def api_root():
    return {"status": "ok", "message": "API endpoint working"}

# Handler pour Vercel
handler = Mangum(app)
