"""Router API JSON (/api).

Territoire partagé, délimité par sections commentées pour éviter les collisions
entre tickets :
  # T03 : POST /api/produits/{id}/relancer (worker — relance un produit erreur)
  # T07 : GET /api/publication/next, POST /api/publication/{id}/publiee (userscript)
  # T08 : endpoints de déploiement / santé si besoin

Chaque ticket n'écrit QUE dans sa section.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def health():
    """Sonde de vie basique (utile au déploiement / launchd)."""
    return {"status": "ok"}


# --- # T03 : relance worker -------------------------------------------------
# (ajouté par le ticket T03)


# --- # T07 : endpoints userscript -------------------------------------------
# (ajoutés par le ticket T07)


# --- # T08 : déploiement ----------------------------------------------------
# (ajoutés par le ticket T08)
