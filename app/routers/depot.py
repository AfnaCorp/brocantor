"""Router Dépôt (T02). Placeholder T01 : à remplacer par la PWA de capture."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..templating import render

router = APIRouter(prefix="/depot", tags=["depot"])


@router.get("")
@router.get("/")
def depot_index(request: Request):
    return render(
        request,
        "placeholder.html",
        titre="Dépôt",
        onglet="depot",
        message="Écran de dépôt mobile à venir (ticket T02).",
    )
