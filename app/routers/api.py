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
from fastapi.responses import JSONResponse

from .. import models

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health")
def health():
    """Sonde de vie basique (utile au déploiement / launchd)."""
    return {"status": "ok"}


# --- # T03 : relance worker -------------------------------------------------


@router.post("/produits/{produit_id}/relancer")
def relancer(produit_id: str):
    """Repasse un produit en état `erreur` vers `depose` (le worker le reprendra)."""
    produit = models.get_produit(produit_id)
    if produit is None:
        return JSONResponse({"ok": False, "erreur": "Produit introuvable."}, status_code=404)
    if produit.etat != models.ETAT_ERREUR:
        return JSONResponse(
            {"ok": False, "erreur": f"Produit en état '{produit.etat}', pas 'erreur'."},
            status_code=409,
        )
    models.changer_etat(produit_id, models.ETAT_DEPOSE, "relance manuelle depuis l'API")
    return {"ok": True, "produit_id": produit_id, "etat": models.ETAT_DEPOSE}


# --- # T07 : endpoints userscript -------------------------------------------
# (ajoutés par le ticket T07)


# --- # T08 : déploiement ----------------------------------------------------
# (ajoutés par le ticket T08)
