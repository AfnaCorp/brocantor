"""Router Dashboard (T05). Placeholder T01."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..templating import render

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
@router.get("/")
def dashboard_index(request: Request):
    return render(
        request,
        "placeholder.html",
        titre="Dashboard",
        onglet="dashboard",
        message="Dashboard de suivi à venir (ticket T05).",
    )
