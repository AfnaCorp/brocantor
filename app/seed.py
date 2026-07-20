"""Données de démo : `python -m app.seed`.

Crée 6 produits factices couvrant tous les états du pipeline, chacun avec 2
images JPEG générées par Pillow (rectangle coloré + texte). Idempotent : purge
la base et les photos puis recrée tout.
"""
from __future__ import annotations

import json
import shutil

from PIL import Image, ImageDraw

from . import db
from .models import now_iso, nouvel_id

# (etat, titre, description, categorie, prix_min, prix_max, prix_choisi,
#  confiance, hypotheses, questions, note, couleur, extras)
_PRODUITS = [
    {
        "etat": "depose",
        "note_utilisateur": "Vélo Décathlon acheté 300 € en 2021, pneu avant à changer.",
        "couleur": (70, 110, 160),
        "label": "Vélo",
    },
    {
        "etat": "a_valider",
        "titre": "Table basse chêne massif style scandinave",
        "description": (
            "Table basse en chêne massif, plateau rectangulaire 110×55 cm. "
            "Bon état général, quelques légères marques d'usage sur le dessus. "
            "Pieds fuselés stables. Idéale salon."
        ),
        "categorie_lbc": "Ameublement",
        "prix_min_estime": 40,
        "prix_max_estime": 70,
        "confiance_estimation": "moyenne",
        "hypotheses_ia": ["Bois supposé chêne d'après le veinage", "Fabrication années 2010"],
        "questions_ia": ["Dimensions exactes ?", "Marque/fabricant ?"],
        "note_utilisateur": "Achetée chez un brocanteur.",
        "couleur": (150, 110, 60),
        "label": "Table basse",
    },
    {
        "etat": "prete",
        "titre": "Perceuse-visseuse Bosch 18V sans fil",
        "description": (
            "Perceuse-visseuse Bosch 18V livrée avec 2 batteries et chargeur. "
            "Fonctionne parfaitement, mandrin en bon état. Coffret inclus."
        ),
        "categorie_lbc": "Bricolage",
        "prix_min_estime": 45,
        "prix_max_estime": 80,
        "prix_choisi": 75,
        "confiance_estimation": "haute",
        "hypotheses_ia": ["Modèle GSR supposé d'après le boîtier"],
        "questions_ia": [],
        "note_utilisateur": "2 batteries fournies, tout fonctionne.",
        "couleur": (60, 140, 90),
        "label": "Perceuse",
    },
    {
        "etat": "publiee",
        "titre": "iPhone 11 64 Go noir débloqué",
        "description": (
            "iPhone 11 64 Go noir, débloqué tous opérateurs. Écran sans rayure, "
            "batterie à 84 %. Vendu avec coque. Quelques micro-marques au dos."
        ),
        "categorie_lbc": "Téléphonie",
        "prix_min_estime": 150,
        "prix_max_estime": 220,
        "prix_choisi": 199,
        "confiance_estimation": "haute",
        "hypotheses_ia": ["Capacité 64 Go supposée"],
        "questions_ia": ["État de la batterie ?"],
        "url_annonce": "https://www.leboncoin.fr/ventes_immobilieres/exemple",
        "note_utilisateur": "Batterie 84 %, coque fournie.",
        "couleur": (40, 40, 48),
        "label": "iPhone 11",
    },
    {
        "etat": "vendue",
        "titre": "Canapé 3 places tissu gris",
        "description": (
            "Canapé 3 places en tissu gris, structure solide, assises fermes. "
            "Traces d'usure normales. À venir chercher sur place."
        ),
        "categorie_lbc": "Ameublement",
        "prix_min_estime": 80,
        "prix_max_estime": 150,
        "prix_choisi": 120,
        "prix_vente_reel": 110,
        "confiance_estimation": "moyenne",
        "hypotheses_ia": ["Dimensions estimées ~200 cm de large"],
        "questions_ia": ["Déhoussable ?"],
        "note_utilisateur": "Vendu à un voisin, négocié 110 €.",
        "couleur": (120, 120, 130),
        "label": "Canapé",
    },
    {
        "etat": "erreur",
        "note_utilisateur": "Lot de vaisselle ancienne, photos un peu floues.",
        "erreur_derniere": "Réponse IA invalide après 3 tentatives (JSON non conforme).",
        "tentatives": 3,
        "couleur": (160, 70, 70),
        "label": "Vaisselle",
    },
]


def _fake_jpeg(path, couleur, label, index) -> None:
    """Génère un JPEG factice : fond coloré + texte."""
    img = Image.new("RGB", (800, 600), couleur)
    draw = ImageDraw.Draw(img)
    # Cadre + texte (police par défaut Pillow, pas de dépendance externe).
    draw.rectangle([20, 20, 780, 580], outline=(255, 255, 255), width=4)
    draw.text((40, 40), f"{label}", fill=(255, 255, 255))
    draw.text((40, 70), f"photo {index}", fill=(230, 230, 230))
    img.save(path, "JPEG", quality=85)


def purger() -> None:
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM evenements")
        conn.execute("DELETE FROM photos")
        conn.execute("DELETE FROM produits")
        conn.commit()
    finally:
        conn.close()
    if db.PHOTOS_DIR.exists():
        shutil.rmtree(db.PHOTOS_DIR)
    db.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def creer_produit(spec: dict) -> str:
    pid = nouvel_id()
    dossier = db.PHOTOS_DIR / pid
    dossier.mkdir(parents=True, exist_ok=True)

    conn = db.get_connection()
    try:
        conn.execute(
            "INSERT INTO produits (id, cree_le, etat, note_utilisateur, titre, "
            "description, categorie_lbc, prix_min_estime, prix_max_estime, "
            "prix_choisi, confiance_estimation, hypotheses_ia, questions_ia, "
            "url_annonce, prix_vente_reel, vendu_le, notes, erreur_derniere, "
            "tentatives) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                pid,
                now_iso(),
                spec["etat"],
                spec.get("note_utilisateur"),
                spec.get("titre"),
                spec.get("description"),
                spec.get("categorie_lbc"),
                spec.get("prix_min_estime"),
                spec.get("prix_max_estime"),
                spec.get("prix_choisi"),
                spec.get("confiance_estimation"),
                json.dumps(spec.get("hypotheses_ia", []), ensure_ascii=False),
                json.dumps(spec.get("questions_ia", []), ensure_ascii=False),
                spec.get("url_annonce"),
                spec.get("prix_vente_reel"),
                now_iso() if spec["etat"] == "vendue" else None,
                spec.get("notes"),
                spec.get("erreur_derniere"),
                spec.get("tentatives", 0),
            ),
        )
        # 2 photos par produit.
        for i in range(2):
            chemin = dossier / f"photo_{i}.jpg"
            _fake_jpeg(chemin, spec["couleur"], spec["label"], i + 1)
            chemin_lbc = None
            # Pour les états avancés, simuler la version LBC déjà générée.
            if spec["etat"] in ("a_valider", "prete", "publiee", "vendue"):
                chemin_lbc_path = dossier / f"lbc_{i}.jpg"
                _fake_jpeg(chemin_lbc_path, spec["couleur"], spec["label"], i + 1)
                chemin_lbc = str(chemin_lbc_path.relative_to(db.DATA_DIR))
            conn.execute(
                "INSERT INTO photos (id, produit_id, chemin_original, chemin_lbc, "
                "position) VALUES (?,?,?,?,?)",
                (
                    nouvel_id(),
                    pid,
                    str(chemin.relative_to(db.DATA_DIR)),
                    chemin_lbc,
                    i,
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return pid


def main() -> None:
    db.init_db()
    purger()
    ids = [creer_produit(spec) for spec in _PRODUITS]
    print(f"Seed OK : {len(ids)} produits créés.")
    for spec, pid in zip(_PRODUITS, ids):
        print(f"  - {spec['etat']:14s} {spec.get('titre', spec['label'])}  ({pid[:8]})")


if __name__ == "__main__":
    main()
