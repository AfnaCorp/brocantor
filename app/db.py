"""Accès SQLite bas niveau : connexion, initialisation du schéma, helpers.

SQL brut paramétré uniquement — pas d'ORM (SQLAlchemy interdit, cf. CLAUDE.md).
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Répertoire de données (base + photos). Défaut ./data relatif à la racine projet.
DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
PHOTOS_DIR = DATA_DIR / "photos"
DB_PATH = DATA_DIR / "app.db"

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Nouvelle connexion SQLite. `row_factory` = accès par nom de colonne.

    check_same_thread=False : la connexion peut être créée dans un thread et
    utilisée ailleurs (FastAPI + worker asyncio). Chaque appelant ouvre et
    ferme sa propre connexion — pas de partage d'objet Connection.
    """
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Crée le schéma si absent (idempotent)."""
    _ensure_dirs()
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_connection()
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()


def query_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> None:
    conn = get_connection()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()
