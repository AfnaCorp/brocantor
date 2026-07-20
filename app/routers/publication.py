"""Router Publication (T06). Placeholder T01.

Préfixe `/produits` (comme les fiches) mais routes distinctes `/{id}/publier`
pour ne pas entrer en collision avec le router produits (T04).
"""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..templating import render

router = APIRouter(prefix="/produits", tags=["publication"])


@router.get("/{produit_id}/publier")
def publier(request: Request, produit_id: str):
    return render(
        request,
        "placeholder.html",
        titre="Publier",
        onglet="produits",
        message=f"Pack de publication à venir (ticket T06). Produit {produit_id}.",
    )
