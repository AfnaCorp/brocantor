"""Génération des versions Leboncoin des photos (T03).

Pour chaque photo d'un produit : produire un JPEG côté max 1200 px, qualité 85,
poids < 500 Ko, dans `data/photos/<id>/lbc_<position>.jpg`, et renseigner
`chemin_lbc` en base.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from . import db

MAX_SIDE = 1200
QUALITE_INIT = 85
POIDS_MAX = 500 * 1024  # 500 Ko


def generer_version_lbc(chemin_original: Path, chemin_lbc: Path) -> None:
    """Écrit une version LBC redimensionnée/compressée de l'image d'origine."""
    with Image.open(chemin_original) as img:
        img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

        qualite = QUALITE_INIT
        chemin_lbc.parent.mkdir(parents=True, exist_ok=True)
        img.save(chemin_lbc, "JPEG", quality=qualite, optimize=True)
        # Réduire la qualité par paliers si l'image dépasse le poids cible.
        while chemin_lbc.stat().st_size > POIDS_MAX and qualite > 40:
            qualite -= 10
            img.save(chemin_lbc, "JPEG", quality=qualite, optimize=True)


def preparer_photos_lbc(produit_id: str) -> list[str]:
    """Génère les versions LBC manquantes pour un produit, met à jour la base.

    Retourne les chemins LBC (relatifs à DATA_DIR) dans l'ordre des positions.
    """
    photos = db.query_all(
        "SELECT id, chemin_original, chemin_lbc, position FROM photos "
        "WHERE produit_id = ? ORDER BY position ASC",
        (produit_id,),
    )
    chemins_lbc: list[str] = []
    conn = db.get_connection()
    try:
        for ph in photos:
            original = db.DATA_DIR / ph["chemin_original"]
            rel_lbc = f"photos/{produit_id}/lbc_{ph['position']}.jpg"
            abs_lbc = db.DATA_DIR / rel_lbc
            if not abs_lbc.exists():
                generer_version_lbc(original, abs_lbc)
            conn.execute(
                "UPDATE photos SET chemin_lbc = ? WHERE id = ?", (rel_lbc, ph["id"])
            )
            chemins_lbc.append(rel_lbc)
        conn.commit()
    finally:
        conn.close()
    return chemins_lbc
