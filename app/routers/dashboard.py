"""Router Dashboard (T05) : compteurs, tuiles argent, liste d'action.

Tour de contrôle du déstockage. Toute transition passe par `changer_etat`
(models). Les sommes sont calculées en SQL dans ce router.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from .. import db, models
from ..templating import render

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Ordre d'affichage des tuiles de compteur.
ETATS_TUILES = [
    (models.ETAT_EN_TRAITEMENT, "En traitement"),
    (models.ETAT_A_VALIDER, "À valider"),
    (models.ETAT_PRETE, "Prêtes"),
    (models.ETAT_PUBLIEE, "Publiées"),
    (models.ETAT_VENDUE, "Vendues"),
    (models.ETAT_ERREUR, "Erreur"),
]

SEUIL_VIEUX_JOURS = 10


# --- Données -----------------------------------------------------------------


def _compteurs() -> dict[str, int]:
    rows = db.query_all("SELECT etat, COUNT(*) AS n FROM produits GROUP BY etat")
    compte = {r["etat"]: r["n"] for r in rows}
    return {etat: compte.get(etat, 0) for etat, _ in ETATS_TUILES}


def _sommes() -> dict[str, int]:
    val = db.query_one(
        "SELECT COALESCE(SUM(prix_choisi),0) AS s FROM produits "
        "WHERE etat IN ('prete','publiee')"
    )["s"]
    vendu = db.query_one(
        "SELECT COALESCE(SUM(prix_vente_reel),0) AS s FROM produits WHERE etat='vendue'"
    )["s"]
    return {"valeur_estimee": val, "total_vendu": vendu}


def _jours_depuis_publication(produit_id: str) -> int | None:
    """Nombre de jours depuis le passage à `publiee` (via evenements)."""
    row = db.query_one(
        "SELECT MAX(horodatage) AS h FROM evenements "
        "WHERE produit_id=? AND nouvel_etat='publiee'",
        (produit_id,),
    )
    horo = row["h"] if row else None
    if not horo:
        # Repli : date de création (utile pour le seed sans événement de publication).
        p = db.query_one("SELECT cree_le FROM produits WHERE id=?", (produit_id,))
        horo = p["cree_le"] if p else None
    if not horo:
        return None
    try:
        dt = datetime.fromisoformat(horo)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).days
    except ValueError:
        return None


def _produits_liste(etat: str | None):
    if etat and etat in models.ETATS:
        produits = models.lister_produits(etat)
    else:
        produits = [
            p for p in models.lister_produits()
            if p.etat not in (models.ETAT_VENDUE, models.ETAT_ABANDONNEE)
        ]
    # a_valider et erreur en tête (action humaine attendue), puis récent d'abord.
    prio = {models.ETAT_A_VALIDER: 0, models.ETAT_ERREUR: 1}
    produits.sort(key=lambda p: (prio.get(p.etat, 2), ))
    enrichis = []
    for p in produits:
        jours = _jours_depuis_publication(p.id) if p.etat == models.ETAT_PUBLIEE else None
        enrichis.append({"p": p, "jours": jours, "vieux": jours is not None and jours > SEUIL_VIEUX_JOURS})
    return enrichis


# --- Pages / fragments -------------------------------------------------------


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard_index(request: Request, etat: str | None = None):
    return render(
        request, "dashboard.html",
        titre="Dashboard", onglet="dashboard",
        compteurs=_compteurs(), sommes=_sommes(),
        etats_tuiles=ETATS_TUILES, filtre=etat,
        produits=_produits_liste(etat),
    )


@router.get("/compteurs", response_class=HTMLResponse)
def fragment_compteurs(request: Request):
    return render(
        request, "dashboard_compteurs.html",
        compteurs=_compteurs(), sommes=_sommes(), etats_tuiles=ETATS_TUILES,
    )


@router.get("/liste", response_class=HTMLResponse)
def fragment_liste(request: Request, etat: str | None = None):
    return render(
        request, "dashboard_liste.html",
        produits=_produits_liste(etat), filtre=etat,
    )


@router.get("/{produit_id}/actions", response_class=HTMLResponse)
def fragment_actions(request: Request, produit_id: str):
    p = models.get_produit(produit_id)
    if p is None:
        return HTMLResponse("", status_code=404)
    jours = _jours_depuis_publication(p.id) if p.etat == models.ETAT_PUBLIEE else None
    return render(request, "dashboard_actions.html", p=p, jours=jours)


@router.get("/{produit_id}/vendu-form", response_class=HTMLResponse)
def fragment_vendu_form(request: Request, produit_id: str):
    p = models.get_produit(produit_id)
    if p is None:
        return HTMLResponse("", status_code=404)
    return render(request, "dashboard_vendu_form.html", p=p)


# --- Actions d'état ----------------------------------------------------------

_MAJ = {"HX-Trigger": "dashboard-maj"}  # recharge compteurs + liste côté client


@router.post("/{produit_id}/vendu", response_class=HTMLResponse)
def marquer_vendu(produit_id: str, prix: str = Form("")):
    p = models.get_produit(produit_id)
    if p is None:
        return HTMLResponse("Introuvable", status_code=404)
    prix_reel = None
    prix = prix.strip()
    if prix:
        try:
            prix_reel = int(round(float(prix.replace(",", "."))))
        except ValueError:
            prix_reel = None
    if prix_reel is None:
        prix_reel = p.prix_choisi
    try:
        models.changer_etat(produit_id, models.ETAT_VENDUE, f"vendu {prix_reel} €")
    except models.TransitionIllegale as exc:
        return HTMLResponse(f'<span class="msg-err">{exc}</span>', status_code=200)
    db.execute("UPDATE produits SET prix_vente_reel=? WHERE id=?", (prix_reel, produit_id))
    return HTMLResponse("", headers=_MAJ)


@router.post("/{produit_id}/retirer", response_class=HTMLResponse)
def retirer(produit_id: str):
    p = models.get_produit(produit_id)
    if p is None:
        return HTMLResponse("Introuvable", status_code=404)
    try:
        models.changer_etat(produit_id, models.ETAT_ABANDONNEE, "retiré depuis le dashboard")
    except models.TransitionIllegale as exc:
        return HTMLResponse(f'<span class="msg-err">{exc}</span>', status_code=200)
    return HTMLResponse("", headers=_MAJ)
