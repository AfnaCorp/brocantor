"""Appel IA d'analyse produit (T03).

Un appel vision par produit via LiteLLM, sortie JSON forcée par json_schema. La
note utilisateur prime sur les suppositions visuelles. Retry ×3 avec backoff.

LiteLLM route vers le provider selon le préfixe du modèle (`AI_MODEL` dans
.env) : `openai/gpt-5`, `anthropic/claude-sonnet-5`… Changer de provider = une
variable d'environnement, pas une ligne de code.

Modes :
  - Clé du provider visé présente → appel réel.
  - Variable `BROCANTOR_FAKE_AI` vraie → fiche factice déterministe, AUCUN appel
    réseau (permet de tester tout le pipeline sans clé).
  - Ni l'un ni l'autre → `PasDeCleAPI` (le worker laisse le produit en `depose`).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from pathlib import Path

from . import db
from .categories_lbc import CATEGORIES, valider_categorie

logger = logging.getLogger("brocantor.analyse")

DEFAUT_MODELE = "openai/gpt-5"
# Sur les modèles à raisonnement (GPT-5…), ce budget couvre AUSSI les tokens de
# réflexion internes, pas seulement la réponse visible : à 1024 le raisonnement
# consommait tout et la fiche revenait vide (finish_reason=length).
MAX_TOKENS = 4096
BACKOFFS = (2, 8, 30)  # secondes entre les 3 tentatives

NOM_SCHEMA = "fiche_produit"

# Clé d'API attendue par provider. Sert uniquement à détecter si une analyse
# réelle est possible ; LiteLLM lit lui-même la variable au moment de l'appel.
CLES_PROVIDER = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
}

# `strict: True` exige additionalProperties=False et TOUS les champs dans
# required — sinon OpenAI rejette le schéma.
SCHEMA_FICHE = {
    "type": "object",
    "properties": {
        "titre": {"type": "string", "description": "≤ 50 caractères, style annonce Leboncoin"},
        "description": {
            "type": "string",
            "description": "3 à 6 phrases honnêtes : ce que c'est, état, défauts visibles, dimensions estimées si pertinent",
        },
        "categorie_lbc": {
            "type": "string",
            "enum": CATEGORIES,
            "description": "Un libellé EXACT de la liste fournie",
        },
        "prix_min": {"type": "integer"},
        "prix_max": {"type": "integer"},
        "confiance": {"type": "string", "enum": ["haute", "moyenne", "basse"]},
        "hypotheses": {"type": "array", "items": {"type": "string"}},
        "questions": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "titre",
        "description",
        "categorie_lbc",
        "prix_min",
        "prix_max",
        "confiance",
        "hypotheses",
        "questions",
    ],
    "additionalProperties": False,
}

FORMAT_REPONSE = {
    "type": "json_schema",
    "json_schema": {"name": NOM_SCHEMA, "schema": SCHEMA_FICHE, "strict": True},
}

SYSTEME = (
    "Tu es un expert de la vente d'occasion entre particuliers en France "
    "(Leboncoin). À partir de photos d'un objet et d'une note optionnelle du "
    "vendeur, tu produis une fiche d'annonce prête à publier, au format JSON "
    "imposé.\n\n"
    "Règles :\n"
    "- Sois HONNÊTE sur les défauts visibles : ça évite les litiges et rassure "
    "l'acheteur. Pas de superlatifs creux.\n"
    "- Le titre fait ≤ 50 caractères, concret (objet + marque/modèle si visible).\n"
    "- La description fait 3 à 6 phrases : ce que c'est, état réel, défauts, "
    "dimensions estimées si pertinent.\n"
    "- La catégorie DOIT être un libellé exact de la liste imposée.\n"
    "- Le prix est une FOURCHETTE pour de l'occasion entre particuliers en "
    "France (prix_min < prix_max), jamais un prix sec.\n"
    "- La note du vendeur PRIME sur tes suppositions visuelles : si elle dit "
    "« acheté 300 € en 2021 », sers-t'en pour calibrer la fourchette.\n"
    "- Liste tes hypothèses (ce que tu supposes sans certitude) et les "
    "questions dont la réponse améliorerait la fiche."
)


class PasDeCleAPI(RuntimeError):
    """Ni clé API ni mode factice : impossible d'analyser."""


class AnalyseInvalide(RuntimeError):
    """Réponse IA absente ou non conforme au schéma."""


def _modele() -> str:
    return os.getenv("AI_MODEL", DEFAUT_MODELE)


def _cle_attendue() -> str:
    """Nom de la variable d'env attendue pour le provider du modèle courant."""
    provider = _modele().split("/", 1)[0] if "/" in _modele() else "openai"
    return CLES_PROVIDER.get(provider, f"{provider.upper()}_API_KEY")


def _mode() -> str:
    if os.getenv("BROCANTOR_FAKE_AI"):
        return "fake"
    if os.getenv(_cle_attendue()):
        return "reel"
    return "aucun"


def cle_disponible() -> bool:
    """Vrai si une analyse est possible (clé réelle ou mode factice)."""
    return _mode() in ("reel", "fake")


def _fiche_factice(note: str | None) -> dict:
    """Fiche déterministe pour tester le pipeline sans réseau."""
    note = (note or "").strip()
    titre = "Objet d'occasion à vendre"
    prix_min, prix_max = 10, 30
    hypotheses = ["Fiche générée en mode factice (aucune clé API) — à revoir."]
    if note:
        titre = ("À vendre — " + note)[:50]
        hypotheses.append(f"Basé sur la note : « {note[:80]} »")
    return {
        "titre": titre,
        "description": (
            "Objet d'occasion en état correct. "
            + (f"Contexte fourni par le vendeur : {note}. " if note else "")
            + "Défauts éventuels visibles sur les photos. "
            "Fiche à valider et à ajuster avant publication."
        ),
        "categorie_lbc": "Autres",
        "prix_min": prix_min,
        "prix_max": prix_max,
        "confiance": "basse",
        "hypotheses": hypotheses,
        "questions": ["Marque/modèle exact ?", "État de fonctionnement ?"],
    }


def _bloc_image(chemin_lbc_rel: str) -> dict:
    """Format OpenAI (data-URI). LiteLLM le retraduit pour les autres providers."""
    data = (db.DATA_DIR / chemin_lbc_rel).read_bytes()
    b64 = base64.standard_b64encode(data).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def _appel_reel(note: str | None, chemins_lbc: list[str]) -> dict:
    from litellm import completion  # import tardif : évite la dépendance au boot

    modele = _modele()

    texte = "Note du vendeur : " + (note.strip() if note else "(aucune)")
    texte += (
        "\n\nAnalyse ces photos et produis la fiche au format JSON imposé. "
        "Catégories autorisées : " + ", ".join(CATEGORIES) + "."
    )
    contenu: list[dict] = [_bloc_image(c) for c in chemins_lbc]
    contenu.append({"type": "text", "text": texte})

    messages = [
        {"role": "system", "content": SYSTEME},
        {"role": "user", "content": contenu},
    ]

    derniere_err: Exception | None = None
    for tentative, pause in enumerate(BACKOFFS, start=1):
        try:
            reponse = completion(
                model=modele,
                messages=messages,
                max_tokens=MAX_TOKENS,
                response_format=FORMAT_REPONSE,
            )
            brut = reponse.choices[0].message.content
            if not brut:
                raise AnalyseInvalide("Réponse vide du modèle.")
            usage = getattr(reponse, "usage", None)
            logger.info(
                "analyse OK (modèle=%s, in=%s, out=%s)",
                modele,
                getattr(usage, "prompt_tokens", "?"),
                getattr(usage, "completion_tokens", "?"),
            )
            try:
                return json.loads(brut)
            except json.JSONDecodeError as exc:
                raise AnalyseInvalide(f"Réponse non-JSON : {exc}") from exc
        except AnalyseInvalide:
            raise  # réponse non conforme : ne pas réessayer aveuglément
        except Exception as exc:  # erreurs API/réseau : retry avec backoff
            derniere_err = exc
            logger.warning("analyse tentative %d échouée : %s", tentative, exc)
            if tentative < len(BACKOFFS):
                time.sleep(pause)
    raise AnalyseInvalide(f"Échec API après {len(BACKOFFS)} tentatives : {derniere_err}")


def _normaliser(brut: dict) -> dict:
    """Valide/complète la sortie IA (catégorie, fourchette, types)."""
    cat, ok = valider_categorie(brut.get("categorie_lbc"))
    hypotheses = list(brut.get("hypotheses") or [])
    if not ok:
        hypotheses.append(
            f"Catégorie IA « {brut.get('categorie_lbc')} » hors liste → « {cat} »."
        )
    try:
        pmin = int(brut.get("prix_min") or 0)
        pmax = int(brut.get("prix_max") or 0)
    except (TypeError, ValueError):
        pmin, pmax = 0, 0
    if pmax < pmin:
        pmin, pmax = pmax, pmin
    confiance = brut.get("confiance")
    if confiance not in ("haute", "moyenne", "basse"):
        confiance = "basse"
    titre = (brut.get("titre") or "Objet à vendre").strip()[:50]
    description = (brut.get("description") or "").strip()
    if not description:
        raise AnalyseInvalide("Description vide.")
    return {
        "titre": titre,
        "description": description,
        "categorie_lbc": cat,
        "prix_min": pmin,
        "prix_max": pmax,
        "confiance": confiance,
        "hypotheses": hypotheses,
        "questions": list(brut.get("questions") or []),
    }


def analyser(note: str | None, chemins_lbc: list[str]) -> dict:
    """Analyse un produit et retourne une fiche normalisée (dict).

    Lève `PasDeCleAPI` si aucune analyse n'est possible, `AnalyseInvalide` si la
    réponse est absente/non conforme malgré les tentatives.
    """
    mode = _mode()
    if mode == "aucun":
        raise PasDeCleAPI(f"{_cle_attendue()} absente (et pas de mode factice).")
    if not chemins_lbc:
        raise AnalyseInvalide("Aucune image LBC à analyser.")
    brut = _fiche_factice(note) if mode == "fake" else _appel_reel(note, chemins_lbc)
    return _normaliser(brut)
