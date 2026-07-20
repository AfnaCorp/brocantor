"""Point d'entrée FastAPI de Brocantor.

Une seule app : UI (HTMX) + API JSON + worker asyncio intégré (T03).
Seul ce fichier monte les routers et le layout — les autres tickets n'y touchent
pas (exception prévue : 3 lignes pour le worker en T03).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import db
from .routers import api, dashboard, depot, produits, publication

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage : schéma prêt avant toute requête.
    db.init_db()

    # --- # T03 : démarrage du worker d'analyse IA -------------------------
    # (le ticket T03 démarre ici sa boucle asyncio et l'arrête au shutdown)

    yield
    # Arrêt propre (rien à nettoyer pour le socle).


app = FastAPI(title="Brocantor", lifespan=lifespan)

# Statiques applicatifs (CSS, JS vendorisé, manifest).
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Photos servies depuis le filesystem (créé au premier init_db).
db._ensure_dirs()
app.mount("/photos", StaticFiles(directory=str(db.PHOTOS_DIR)), name="photos")

# Routers métier.
app.include_router(depot.router)
app.include_router(produits.router)
app.include_router(publication.router)
app.include_router(dashboard.router)
app.include_router(api.router)


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")
