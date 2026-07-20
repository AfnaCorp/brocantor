"""Entités et machine à états produit.

`changer_etat` est LA porte d'entrée unique des changements d'état : tous les
tickets (worker, fiches, dashboard, publication) doivent passer par elle. Elle
valide la transition contre la machine à états de CLAUDE.md et journalise dans
la table `evenements`.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from . import db

# --- États (valeurs canoniques stockées en base, sans accents) ---------------

ETAT_DEPOSE = "depose"
ETAT_EN_TRAITEMENT = "en_traitement"
ETAT_A_VALIDER = "a_valider"
ETAT_PRETE = "prete"
ETAT_PUBLIEE = "publiee"
ETAT_VENDUE = "vendue"
ETAT_ERREUR = "erreur"
ETAT_ABANDONNEE = "abandonnee"

ETATS = (
    ETAT_DEPOSE,
    ETAT_EN_TRAITEMENT,
    ETAT_A_VALIDER,
    ETAT_PRETE,
    ETAT_PUBLIEE,
    ETAT_VENDUE,
    ETAT_ERREUR,
    ETAT_ABANDONNEE,
)

# Libellés FR pour l'affichage.
ETAT_LABELS = {
    ETAT_DEPOSE: "Déposé",
    ETAT_EN_TRAITEMENT: "En traitement",
    ETAT_A_VALIDER: "À valider",
    ETAT_PRETE: "Prête",
    ETAT_PUBLIEE: "Publiée",
    ETAT_VENDUE: "Vendue",
    ETAT_ERREUR: "Erreur",
    ETAT_ABANDONNEE: "Abandonnée",
}

# Machine à états (CLAUDE.md) :
#   depose → en_traitement → a_valider → prete → publiee → vendue
#                 ↓                                  ↓
#              erreur (relançable → depose)      abandonnee
# Transitions automatiques : depose→en_traitement→a_valider (worker).
# Tout le reste est manuel. `erreur → depose` = relance (T03).
TRANSITIONS: dict[str, set[str]] = {
    ETAT_DEPOSE: {ETAT_EN_TRAITEMENT},
    ETAT_EN_TRAITEMENT: {ETAT_A_VALIDER, ETAT_ERREUR},
    ETAT_A_VALIDER: {ETAT_PRETE, ETAT_ABANDONNEE},
    ETAT_PRETE: {ETAT_PUBLIEE, ETAT_ABANDONNEE},
    ETAT_PUBLIEE: {ETAT_VENDUE, ETAT_ABANDONNEE},
    ETAT_VENDUE: set(),
    ETAT_ERREUR: {ETAT_DEPOSE},
    ETAT_ABANDONNEE: set(),
}


class TransitionIllegale(ValueError):
    """Levée quand une transition d'état n'est pas autorisée."""


# --- Entités -----------------------------------------------------------------


@dataclass
class Photo:
    id: str
    produit_id: str
    chemin_original: str
    chemin_lbc: str | None
    position: int


@dataclass
class Produit:
    id: str
    cree_le: str
    etat: str
    note_utilisateur: str | None = None
    titre: str | None = None
    description: str | None = None
    categorie_lbc: str | None = None
    prix_min_estime: int | None = None
    prix_max_estime: int | None = None
    prix_choisi: int | None = None
    confiance_estimation: str | None = None
    hypotheses_ia: list[str] = field(default_factory=list)
    questions_ia: list[str] = field(default_factory=list)
    url_annonce: str | None = None
    prix_vente_reel: int | None = None
    vendu_le: str | None = None
    notes: str | None = None
    erreur_derniere: str | None = None
    tentatives: int = 0
    photos: list[Photo] = field(default_factory=list)

    @property
    def etat_label(self) -> str:
        return ETAT_LABELS.get(self.etat, self.etat)


# --- Helpers de (dé)sérialisation --------------------------------------------


def _loads_liste(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        data = json.loads(value)
        return list(data) if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def produit_from_row(row) -> Produit:
    return Produit(
        id=row["id"],
        cree_le=row["cree_le"],
        etat=row["etat"],
        note_utilisateur=row["note_utilisateur"],
        titre=row["titre"],
        description=row["description"],
        categorie_lbc=row["categorie_lbc"],
        prix_min_estime=row["prix_min_estime"],
        prix_max_estime=row["prix_max_estime"],
        prix_choisi=row["prix_choisi"],
        confiance_estimation=row["confiance_estimation"],
        hypotheses_ia=_loads_liste(row["hypotheses_ia"]),
        questions_ia=_loads_liste(row["questions_ia"]),
        url_annonce=row["url_annonce"],
        prix_vente_reel=row["prix_vente_reel"],
        vendu_le=row["vendu_le"],
        notes=row["notes"],
        erreur_derniere=row["erreur_derniere"],
        tentatives=row["tentatives"],
    )


def photo_from_row(row) -> Photo:
    return Photo(
        id=row["id"],
        produit_id=row["produit_id"],
        chemin_original=row["chemin_original"],
        chemin_lbc=row["chemin_lbc"],
        position=row["position"],
    )


# --- Accès produits ----------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def nouvel_id() -> str:
    return uuid.uuid4().hex


def get_produit(produit_id: str) -> Produit | None:
    row = db.query_one("SELECT * FROM produits WHERE id = ?", (produit_id,))
    if row is None:
        return None
    produit = produit_from_row(row)
    produit.photos = get_photos(produit_id)
    return produit


def get_photos(produit_id: str) -> list[Photo]:
    rows = db.query_all(
        "SELECT * FROM photos WHERE produit_id = ? ORDER BY position ASC",
        (produit_id,),
    )
    return [photo_from_row(r) for r in rows]


def lister_produits(etat: str | None = None) -> list[Produit]:
    if etat:
        rows = db.query_all(
            "SELECT * FROM produits WHERE etat = ? ORDER BY cree_le DESC", (etat,)
        )
    else:
        rows = db.query_all("SELECT * FROM produits ORDER BY cree_le DESC")
    produits = [produit_from_row(r) for r in rows]
    for p in produits:
        p.photos = get_photos(p.id)
    return produits


def get_evenements(produit_id: str) -> list[dict]:
    rows = db.query_all(
        "SELECT * FROM evenements WHERE produit_id = ? ORDER BY horodatage ASC",
        (produit_id,),
    )
    return [dict(r) for r in rows]


# --- Changement d'état (porte unique) ----------------------------------------


def changer_etat(produit_id: str, nouvel_etat: str, commentaire: str | None = None) -> None:
    """Valide la transition, l'applique et la journalise dans `evenements`.

    Lève `TransitionIllegale` si la transition n'est pas autorisée par la
    machine à états, `ValueError` si le produit ou l'état cible est inconnu.
    """
    if nouvel_etat not in ETATS:
        raise ValueError(f"État inconnu : {nouvel_etat!r}")

    row = db.query_one("SELECT etat FROM produits WHERE id = ?", (produit_id,))
    if row is None:
        raise ValueError(f"Produit introuvable : {produit_id!r}")

    ancien_etat = row["etat"]
    autorisees = TRANSITIONS.get(ancien_etat, set())
    if nouvel_etat not in autorisees:
        raise TransitionIllegale(
            f"Transition illégale {ancien_etat!r} → {nouvel_etat!r} "
            f"(autorisées : {sorted(autorisees) or 'aucune'})"
        )

    conn = db.get_connection()
    try:
        horodatage = now_iso()
        conn.execute(
            "UPDATE produits SET etat = ? WHERE id = ?", (nouvel_etat, produit_id)
        )
        # Champs dérivés utiles pour certains états.
        if nouvel_etat == ETAT_VENDUE:
            conn.execute(
                "UPDATE produits SET vendu_le = ? WHERE id = ? AND vendu_le IS NULL",
                (horodatage, produit_id),
            )
        conn.execute(
            "INSERT INTO evenements (id, produit_id, horodatage, ancien_etat, "
            "nouvel_etat, commentaire) VALUES (?, ?, ?, ?, ?, ?)",
            (nouvel_id(), produit_id, horodatage, ancien_etat, nouvel_etat, commentaire),
        )
        conn.commit()
    finally:
        conn.close()
