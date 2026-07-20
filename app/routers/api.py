"""Router API JSON (/api).

Territoire partagé, délimité par sections commentées pour éviter les collisions
entre tickets :
  # T03 : POST /api/produits/{id}/relancer (worker — relance un produit erreur)
  # T07 : GET /api/publication/next, POST /api/publication/{id}/publiee (userscript)
  # T08 : endpoints de déploiement / santé si besoin

Chaque ticket n'écrit QUE dans sa section.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

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

# CORS ciblé (pas de middleware global) : seule l'origine du dépôt Leboncoin est
# autorisée sur ces deux routes. Sécurité réelle = Tailscale (app non exposée).
ORIGINE_LBC = "https://www.leboncoin.fr"


def _cors(response: Response, request: Request) -> Response:
    if request.headers.get("origin") == ORIGINE_LBC:
        response.headers["Access-Control-Allow-Origin"] = ORIGINE_LBC
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Vary"] = "Origin"
    return response


@router.options("/publication/next")
@router.options("/publication/{produit_id}/publiee")
def publication_preflight(request: Request, produit_id: str | None = None):
    return _cors(Response(status_code=204), request)


@router.get("/publication/next")
def publication_next(request: Request):
    """Fiche `prete` la plus ancienne pour le userscript, ou 204 si aucune."""
    pretes = sorted(models.lister_produits(models.ETAT_PRETE), key=lambda p: p.cree_le)
    if not pretes:
        return _cors(Response(status_code=204), request)
    p = pretes[0]
    data = {
        "id": p.id,
        "titre": p.titre,
        "description": p.description,
        "categorie_lbc": p.categorie_lbc,
        "prix_choisi": p.prix_choisi,
        "photos_zip_url": f"/produits/{p.id}/photos.zip",
        "restantes": len(pretes),
    }
    return _cors(JSONResponse(data), request)


@router.post("/publication/{produit_id}/publiee")
async def publication_publiee(produit_id: str, request: Request):
    """Marque une fiche `prete` comme `publiee` (appelé par le userscript)."""
    produit = models.get_produit(produit_id)
    if produit is None:
        return _cors(JSONResponse({"ok": False, "erreur": "Introuvable."}, status_code=404), request)
    if produit.etat != models.ETAT_PRETE:
        return _cors(
            JSONResponse(
                {"ok": False, "erreur": f"État '{produit.etat}', pas 'prete'."},
                status_code=409,
            ),
            request,
        )
    url_annonce = ""
    try:
        body = await request.json()
        if isinstance(body, dict):
            url_annonce = (body.get("url_annonce") or "").strip()
    except Exception:  # noqa: BLE001 — body vide ou non-JSON : toléré
        url_annonce = ""
    models.changer_etat(produit_id, models.ETAT_PUBLIEE, "publiée via userscript")
    if url_annonce:
        from .. import db
        db.execute("UPDATE produits SET url_annonce=? WHERE id=?", (url_annonce, produit_id))
    return _cors(JSONResponse({"ok": True, "produit_id": produit_id, "etat": "publiee"}), request)


# --- # T08 : déploiement ----------------------------------------------------
# (ajoutés par le ticket T08)
