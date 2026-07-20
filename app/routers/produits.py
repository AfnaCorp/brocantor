"""Router Fiches produits (T04) : liste, détail (preview d'annonce), édition,
validation. Édition inline via HTMX. Toute transition passe par `changer_etat`.
"""
from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .. import db, models
from ..categories_lbc import CATEGORIES
from ..templating import render

router = APIRouter(prefix="/produits", tags=["produits"])

# Filtres (puces) de la liste : (clé, libellé, état ou None pour Tous).
FILTRES = [
    ("tous", "Tous", None),
    ("a_valider", "À valider", models.ETAT_A_VALIDER),
    ("prete", "Prêtes", models.ETAT_PRETE),
    ("publiee", "Publiées", models.ETAT_PUBLIEE),
    ("vendue", "Vendues", models.ETAT_VENDUE),
    ("erreur", "Erreur", models.ETAT_ERREUR),
]

# Champs éditables en inline. type pilote le rendu du fragment.
CHAMPS = {
    "titre": {"label": "Titre", "type": "text", "colonne": "titre"},
    "description": {"label": "Description", "type": "textarea", "colonne": "description"},
    "categorie_lbc": {"label": "Catégorie", "type": "select", "colonne": "categorie_lbc"},
    "prix_choisi": {"label": "Prix choisi", "type": "number", "colonne": "prix_choisi"},
    "notes": {"label": "Notes", "type": "textarea", "colonne": "notes"},
}


def _suggestion_prix(produit: models.Produit) -> int | None:
    """Valeur ronde proche de la fourchette haute pour pré-remplir le prix."""
    base = produit.prix_max_estime or produit.prix_min_estime
    if not base:
        return None
    pas = 5 if base < 100 else 10
    return int(round(base / pas) * pas)


def _lien_comparables(produit: models.Produit) -> str:
    texte = produit.titre or ""
    return "https://www.leboncoin.fr/recherche?text=" + urllib.parse.quote(texte)


# --- Liste -------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def liste(request: Request, etat: str | None = None):
    produits = models.lister_produits()
    if etat:
        produits = [p for p in produits if p.etat == etat]
    # a_valider en premier (c'est là qu'on attend l'humain), sinon récent d'abord.
    produits.sort(key=lambda p: (p.etat != models.ETAT_A_VALIDER, ), reverse=False)
    return render(
        request,
        "produits_liste.html",
        titre="Fiches",
        onglet="produits",
        produits=produits,
        filtres=FILTRES,
        filtre_actif=etat or "tous",
    )


# --- Détail ------------------------------------------------------------------


@router.get("/{produit_id}", response_class=HTMLResponse)
def detail(request: Request, produit_id: str):
    produit = models.get_produit(produit_id)
    if produit is None:
        return HTMLResponse("Produit introuvable", status_code=404)
    return render(
        request,
        "produits_detail.html",
        titre=produit.titre or "Fiche",
        onglet="produits",
        p=produit,
        categories=CATEGORIES,
        champs_meta=CHAMPS,
        suggestion_prix=_suggestion_prix(produit),
        lien_comparables=_lien_comparables(produit),
        evenements=models.get_evenements(produit_id),
        etat_labels=models.ETAT_LABELS,
    )


# --- Édition inline (HTMX) ---------------------------------------------------


def _fragment_champ(request: Request, produit: models.Produit, champ: str, mode: str):
    meta = CHAMPS[champ]
    return render(
        request,
        "produits_champ.html",
        p=produit,
        champ=champ,
        meta=meta,
        mode=mode,
        valeur=getattr(produit, meta["colonne"]),
        categories=CATEGORIES,
        suggestion_prix=_suggestion_prix(produit),
    )


@router.get("/{produit_id}/edit/{champ}", response_class=HTMLResponse)
def editer(request: Request, produit_id: str, champ: str):
    if champ not in CHAMPS:
        return HTMLResponse("Champ inconnu", status_code=404)
    produit = models.get_produit(produit_id)
    if produit is None:
        return HTMLResponse("Produit introuvable", status_code=404)
    return _fragment_champ(request, produit, champ, "edit")


@router.get("/{produit_id}/show/{champ}", response_class=HTMLResponse)
def afficher(request: Request, produit_id: str, champ: str):
    if champ not in CHAMPS:
        return HTMLResponse("Champ inconnu", status_code=404)
    produit = models.get_produit(produit_id)
    if produit is None:
        return HTMLResponse("Produit introuvable", status_code=404)
    return _fragment_champ(request, produit, champ, "show")


@router.post("/{produit_id}/save/{champ}", response_class=HTMLResponse)
def enregistrer(request: Request, produit_id: str, champ: str, valeur: str = Form("")):
    if champ not in CHAMPS:
        return HTMLResponse("Champ inconnu", status_code=404)
    produit = models.get_produit(produit_id)
    if produit is None:
        return HTMLResponse("Produit introuvable", status_code=404)

    colonne = CHAMPS[champ]["colonne"]
    valeur = valeur.strip()
    if CHAMPS[champ]["type"] == "number":
        val_db = None
        if valeur:
            try:
                val_db = int(round(float(valeur.replace(",", "."))))
            except ValueError:
                val_db = None
    else:
        val_db = valeur or None

    # Édition d'un champ = pas de changement d'état (une fiche `prete` le reste).
    db.execute(f"UPDATE produits SET {colonne} = ? WHERE id = ?", (val_db, produit_id))
    produit = models.get_produit(produit_id)
    return _fragment_champ(request, produit, champ, "show")


# --- Validation & actions d'état ---------------------------------------------


@router.post("/{produit_id}/valider")
def valider(produit_id: str):
    produit = models.get_produit(produit_id)
    if produit is None:
        return JSONResponse({"ok": False, "erreur": "Produit introuvable."}, status_code=404)
    if produit.etat != models.ETAT_A_VALIDER:
        return JSONResponse(
            {"ok": False, "erreur": f"État '{produit.etat}', validation impossible."},
            status_code=409,
        )
    manquants = []
    if not (produit.titre or "").strip():
        manquants.append("titre")
    if not (produit.description or "").strip():
        manquants.append("description")
    if not (produit.categorie_lbc or "").strip():
        manquants.append("catégorie")
    if produit.prix_choisi is None:
        manquants.append("prix choisi")
    if manquants:
        return HTMLResponse(
            f'<div class="msg-err">Champs manquants : {", ".join(manquants)}.</div>',
            status_code=200,
        )
    models.changer_etat(produit_id, models.ETAT_PRETE, "validation humaine")
    return HTMLResponse("", headers={"HX-Redirect": f"/produits/{produit_id}"})


@router.post("/{produit_id}/abandonner")
def abandonner(produit_id: str):
    produit = models.get_produit(produit_id)
    if produit is None:
        return JSONResponse({"ok": False, "erreur": "Produit introuvable."}, status_code=404)
    try:
        models.changer_etat(produit_id, models.ETAT_ABANDONNEE, "abandon manuel")
    except models.TransitionIllegale as exc:
        return HTMLResponse(f'<div class="msg-err">{exc}</div>', status_code=200)
    return HTMLResponse("", headers={"HX-Redirect": "/produits"})
