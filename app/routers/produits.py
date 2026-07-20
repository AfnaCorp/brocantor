"""Router Fiches produits (T04). Placeholder T01."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..templating import render

router = APIRouter(prefix="/produits", tags=["produits"])


@router.get("")
@router.get("/")
def produits_index(request: Request):
    return render(
        request,
        "placeholder.html",
        titre="Fiches",
        onglet="produits",
        message="Liste et fiches produits à venir (ticket T04).",
    )
