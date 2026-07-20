"""Router Dépôt (T02) : PWA de capture photos + note.

Écran le plus utilisé en déstockage : capture rapide, enchaînement d'objets.
Le produit est créé directement à l'état `depose` (pas de transition à
journaliser pour la création) ; le worker IA (T03) consommera cet état.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from .. import db
from ..models import now_iso, nouvel_id
from ..templating import render

router = APIRouter(prefix="/depot", tags=["depot"])

MAX_PHOTOS = 5


@router.get("")
@router.get("/")
def depot_index(request: Request):
    return render(request, "depot.html", titre="Dépôt", onglet="depot")


@router.post("")
@router.post("/")
async def depot_upload(
    request: Request,
    note: str = Form(""),
    photos: list[UploadFile] = File(default=[]),
):
    """Crée un produit `depose` avec ses photos (multipart, une requête/produit)."""
    photos = [p for p in photos if p is not None and p.filename]
    if not photos:
        return JSONResponse(
            {"ok": False, "erreur": "Au moins une photo est requise."}, status_code=400
        )
    if len(photos) > MAX_PHOTOS:
        return JSONResponse(
            {"ok": False, "erreur": f"Maximum {MAX_PHOTOS} photos."}, status_code=400
        )

    produit_id = nouvel_id()
    dossier = db.PHOTOS_DIR / produit_id
    dossier.mkdir(parents=True, exist_ok=True)

    # L'ordre reçu = ordre de sélection côté client = position.
    lignes_photos = []
    for position, upload in enumerate(photos):
        data = await upload.read()
        chemin = dossier / f"photo_{position}.jpg"
        chemin.write_bytes(data)
        lignes_photos.append(
            (
                nouvel_id(),
                produit_id,
                str(chemin.relative_to(db.DATA_DIR)),
                None,
                position,
            )
        )

    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT INTO produits (id, cree_le, etat, note_utilisateur) "
            "VALUES (?, ?, 'depose', ?)",
            (produit_id, now_iso(), note.strip() or None),
        )
        conn.executemany(
            "INSERT INTO photos (id, produit_id, chemin_original, chemin_lbc, "
            "position) VALUES (?, ?, ?, ?, ?)",
            lignes_photos,
        )
        conn.commit()
    finally:
        conn.close()

    return JSONResponse(
        {"ok": True, "produit_id": produit_id, "nb_photos": len(lignes_photos)}
    )
