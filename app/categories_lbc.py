"""Taxonomie Leboncoin statique pour un vide-maison.

# TODO utilisateur : affiner depuis le formulaire réel de dépôt LBC (les
# libellés exacts et sous-catégories doivent être copiés depuis leboncoin.fr).
"""
from __future__ import annotations

CATEGORIES: list[str] = [
    "Ameublement",
    "Électroménager",
    "Image & Son",
    "Informatique",
    "Téléphonie",
    "Vêtements",
    "Sport & Plein air",
    "Bricolage",
    "Jardin",
    "Puériculture",
    "Jeux & Jouets",
    "Livres / CD / DVD",
    "Décoration",
    "Vélos",
    "Collection",
    "Autres",
]

CATEGORIE_DEFAUT = "Autres"

# Index insensible à la casse/espaces pour tolérer les petites variations IA.
_INDEX = {c.lower().replace(" ", ""): c for c in CATEGORIES}


def valider_categorie(libelle: str | None) -> tuple[str, bool]:
    """Retourne (categorie_valide, etait_valide).

    Si le libellé rendu par l'IA appartient à la liste (à la casse/espaces près),
    on le normalise. Sinon on retombe sur « Autres » et `etait_valide=False`
    (l'appelant ajoute alors une hypothèse).
    """
    if not libelle:
        return CATEGORIE_DEFAUT, False
    cle = libelle.strip().lower().replace(" ", "")
    if cle in _INDEX:
        return _INDEX[cle], True
    return CATEGORIE_DEFAUT, False
