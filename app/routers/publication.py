"""Router Publication (T06) : pack de publication copier-coller + clôture.

Filet de sécurité permanent (fallback du userscript T07). Aucune requête vers
leboncoin.fr côté serveur : le navigateur de l'utilisateur fait tout. Toute
transition passe par `changer_etat`.

Pas de préfixe : le router sert `/produits/{id}/publier` (page pack) ET `/publier`
(file de publication). Monté tel quel dans main.py (inchangé).
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from .. import db, models
from ..templating import render

router = APIRouter(tags=["publication"])

LIEN_DEPOT_LBC = "https://www.leboncoin.fr/deposer-une-annonce"


def _fiches_pretes() -> list[models.Produit]:
    """Fiches `prete`, plus ancienne d'abord (ordre de publication)."""
    produits = models.lister_produits(models.ETAT_PRETE)
    produits.sort(key=lambda p: p.cree_le)  # cree_le ASC
    return produits


def _prochaine_prete(sauf_id: str) -> models.Produit | None:
    for p in _fiches_pretes():
        if p.id != sauf_id:
            return p
    return None


def _photos_lbc(produit: models.Produit) -> list:
    """Photos avec chemin exploitable (LBC si dispo, sinon original), triées."""
    return sorted(produit.photos, key=lambda ph: ph.position)


# --- File de publication -----------------------------------------------------


@router.get("/publier", response_class=HTMLResponse)
def file_publication(request: Request):
    pretes = _fiches_pretes()
    return render(
        request, "publication_file.html",
        titre="Publier", onglet="produits", pretes=pretes,
    )


# --- Page pack de publication ------------------------------------------------


@router.get("/produits/{produit_id}/publier", response_class=HTMLResponse)
def publier(request: Request, produit_id: str):
    produit = models.get_produit(produit_id)
    if produit is None:
        return HTMLResponse("Produit introuvable", status_code=404)
    if produit.etat != models.ETAT_PRETE:
        # Accessible uniquement pour une fiche prête.
        return RedirectResponse(url=f"/produits/{produit_id}", status_code=303)
    return render(
        request, "publication_pack.html",
        titre="Publier", onglet="produits",
        p=produit,
        photos=_photos_lbc(produit),
        lien_depot=LIEN_DEPOT_LBC,
        suivante=_prochaine_prete(produit_id),
    )


# --- Téléchargement zip des photos -------------------------------------------


@router.get("/produits/{produit_id}/photos.zip")
def photos_zip(produit_id: str):
    produit = models.get_produit(produit_id)
    if produit is None:
        return HTMLResponse("Produit introuvable", status_code=404)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, ph in enumerate(_photos_lbc(produit), start=1):
            rel = ph.chemin_lbc or ph.chemin_original
            chemin = db.DATA_DIR / rel
            if chemin.exists():
                zf.write(chemin, arcname=f"{i}.jpg")
    buffer.seek(0)
    nom = f"brocantor_{produit_id[:8]}.zip"
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )


# --- Clôture : marquer publiée -----------------------------------------------


@router.post("/produits/{produit_id}/publiee")
def marquer_publiee(produit_id: str, url_annonce: str = Form("")):
    produit = models.get_produit(produit_id)
    if produit is None:
        return HTMLResponse("Produit introuvable", status_code=404)
    if produit.etat != models.ETAT_PRETE:
        return RedirectResponse(url=f"/produits/{produit_id}", status_code=303)

    suivante = _prochaine_prete(produit_id)
    models.changer_etat(produit_id, models.ETAT_PUBLIEE, "publiée (pack copier-coller)")
    url_annonce = url_annonce.strip()
    if url_annonce:
        db.execute(
            "UPDATE produits SET url_annonce=? WHERE id=?", (url_annonce, produit_id)
        )
    # Chaînage batch : fiche prête suivante, sinon dashboard.
    cible = f"/produits/{suivante.id}/publier" if suivante else "/dashboard"
    return RedirectResponse(url=cible, status_code=303)
