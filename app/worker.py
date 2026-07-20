"""Worker d'analyse IA (T03) : file asyncio intégrée au process FastAPI.

Boucle toutes les 3 s : prend les produits `depose`, les passe en `en_traitement`
(max 2 en parallèle), génère les images LBC, appelle l'IA, puis `a_valider` ou
`erreur`. Au démarrage, les produits coincés en `en_traitement` (crash) repassent
en `depose`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from . import analyse, db, images, models

logger = logging.getLogger("brocantor.worker")

INTERVALLE = 3       # secondes entre deux scans
CONCURRENCE = 2      # analyses simultanées max

_task: asyncio.Task | None = None
_stop: asyncio.Event | None = None


# --- Reprise après crash -----------------------------------------------------


def _reprendre_bloques() -> int:
    """Remet en `depose` les produits coincés en `en_traitement` (crash).

    Réparation au boot : contournement volontaire de `changer_etat`
    (`en_traitement → depose` n'est pas une transition métier), avec
    journalisation manuelle dans `evenements`.
    """
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT id FROM produits WHERE etat = 'en_traitement'"
        ).fetchall()
        for r in rows:
            conn.execute("UPDATE produits SET etat = 'depose' WHERE id = ?", (r["id"],))
            conn.execute(
                "INSERT INTO evenements (id, produit_id, horodatage, ancien_etat, "
                "nouvel_etat, commentaire) VALUES (?,?,?,?,?,?)",
                (
                    models.nouvel_id(),
                    r["id"],
                    models.now_iso(),
                    "en_traitement",
                    "depose",
                    "worker: reprise après redémarrage",
                ),
            )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


# --- Traitement d'un produit (bloquant, exécuté en thread) -------------------


def _ids_depose() -> list[str]:
    rows = db.query_all(
        "SELECT id FROM produits WHERE etat = 'depose' ORDER BY cree_le ASC"
    )
    return [r["id"] for r in rows]


def _enregistrer_fiche(produit_id: str, fiche: dict) -> None:
    db.execute(
        "UPDATE produits SET titre=?, description=?, categorie_lbc=?, "
        "prix_min_estime=?, prix_max_estime=?, confiance_estimation=?, "
        "hypotheses_ia=?, questions_ia=?, erreur_derniere=NULL WHERE id=?",
        (
            fiche["titre"],
            fiche["description"],
            fiche["categorie_lbc"],
            fiche["prix_min"],
            fiche["prix_max"],
            fiche["confiance"],
            json.dumps(fiche["hypotheses"], ensure_ascii=False),
            json.dumps(fiche["questions"], ensure_ascii=False),
            produit_id,
        ),
    )


def _marquer_erreur(produit_id: str, message: str) -> None:
    db.execute(
        "UPDATE produits SET erreur_derniere=?, tentatives=tentatives+1 WHERE id=?",
        (message[:500], produit_id),
    )


def _traiter_bloquant(produit_id: str) -> None:
    produit = models.get_produit(produit_id)
    # Ne jamais re-analyser un produit déjà avancé (a_valider ou plus loin).
    if produit is None or produit.etat != models.ETAT_DEPOSE:
        return

    t0 = time.monotonic()
    models.changer_etat(produit_id, models.ETAT_EN_TRAITEMENT, "worker: début analyse")
    try:
        chemins_lbc = images.preparer_photos_lbc(produit_id)
        fiche = analyse.analyser(produit.note_utilisateur, chemins_lbc)
        _enregistrer_fiche(produit_id, fiche)
        models.changer_etat(produit_id, models.ETAT_A_VALIDER, "worker: analyse OK")
        logger.info(
            "produit %s → a_valider (%.1fs, %d photos)",
            produit_id[:8], time.monotonic() - t0, len(chemins_lbc),
        )
    except Exception as exc:  # noqa: BLE001 — on veut capturer toute erreur d'analyse
        _marquer_erreur(produit_id, str(exc))
        models.changer_etat(produit_id, models.ETAT_ERREUR, f"worker: {exc}")
        logger.warning("produit %s → erreur : %s", produit_id[:8], exc)


# --- Boucle asyncio ----------------------------------------------------------


async def _boucle() -> None:
    assert _stop is not None
    sem = asyncio.Semaphore(CONCURRENCE)
    inflight: set[str] = set()

    async def _traiter(produit_id: str) -> None:
        async with sem:  # borne le nombre d'analyses (donc d'appels API) simultanées
            try:
                await asyncio.to_thread(_traiter_bloquant, produit_id)
            finally:
                inflight.discard(produit_id)

    while not _stop.is_set():
        if analyse.cle_disponible():
            try:
                ids = await asyncio.to_thread(_ids_depose)
                for pid in ids:
                    if pid not in inflight:
                        inflight.add(pid)
                        asyncio.create_task(_traiter(pid))
            except Exception:  # noqa: BLE001
                logger.exception("worker: erreur de scan")
        try:
            await asyncio.wait_for(_stop.wait(), timeout=INTERVALLE)
        except asyncio.TimeoutError:
            pass


# --- Cycle de vie (appelé par le lifespan de main.py) ------------------------


async def start() -> None:
    global _task, _stop
    n = await asyncio.to_thread(_reprendre_bloques)
    if n:
        logger.info("worker: %d produit(s) repris de en_traitement → depose", n)
    if not analyse.cle_disponible():
        logger.warning(
            "worker: ANTHROPIC_API_KEY absente et BROCANTOR_FAKE_AI non défini — "
            "les produits déposés resteront en 'depose' (pas d'analyse)."
        )
    _stop = asyncio.Event()
    _task = asyncio.create_task(_boucle())
    logger.info("worker: démarré (intervalle=%ds, concurrence=%d)", INTERVALLE, CONCURRENCE)


async def stop() -> None:
    if _stop is not None:
        _stop.set()
    if _task is not None:
        try:
            await asyncio.wait_for(_task, timeout=10)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            _task.cancel()
    logger.info("worker: arrêté")
