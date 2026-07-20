"""Instance Jinja2 partagée par tous les routers.

Centralise la config des templates et injecte le contexte commun (onglet actif,
libellés d'état) pour le layout `base.html`.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from .models import ETAT_LABELS

TEMPLATES_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["ETAT_LABELS"] = ETAT_LABELS


def render(request: Request, template: str, context: dict | None = None, **kwargs):
    """Rend un template avec le contexte commun pré-rempli."""
    ctx: dict = {}
    if context:
        ctx.update(context)
    ctx.update(kwargs)
    # Signature Starlette actuelle : (request, name, context).
    return templates.TemplateResponse(request, template, ctx)
