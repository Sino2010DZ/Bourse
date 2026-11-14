"""Mémoire locale de Sentinelle : une base SQLite (data/sentinelle.db).

Phase 2 : historique des cours de bourse et alertes déjà envoyées.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS cours (
    ticker      TEXT NOT NULL,
    horodatage  TEXT NOT NULL,      -- heure de Zurich, ISO 8601
    prix        REAL NOT NULL,
    variation   REAL,               -- variation du jour en %
    PRIMARY KEY (ticker, horodatage)
);
CREATE TABLE IF NOT EXISTS alertes (
    cle         TEXT PRIMARY KEY,   -- ex. « radar:AMD:2026-11-14 » : une seule alerte par jour et par action
    horodatage  TEXT NOT NULL,
    message     TEXT NOT NULL
);
"""


class BaseDeDonnees:
    def __init__(self, dossier_donnees: Path) -> None:
        dossier_donnees.mkdir(parents=True, exist_ok=True)
        self.chemin = dossier_donnees / "sentinelle.db"
        with closing(self._connexion()) as c, c:
            c.executescript(SCHEMA)

    def _connexion(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.chemin)
        c.row_factory = sqlite3.Row
        return c

    def noter_cours(self, ticker: str, horodatage: str, prix: float, variation: float | None) -> None:
        with closing(self._connexion()) as c, c:
            c.execute(
                "INSERT OR REPLACE INTO cours (ticker, horodatage, prix, variation) VALUES (?, ?, ?, ?)",
                (ticker, horodatage, prix, variation),
            )

    def derniers_cours(self, ticker: str, limite: int = 50) -> list[dict]:
        with closing(self._connexion()) as c:
            lignes = c.execute(
                "SELECT ticker, horodatage, prix, variation FROM cours WHERE ticker = ? ORDER BY horodatage DESC LIMIT ?",
                (ticker, limite),
            ).fetchall()
        return [dict(l) for l in lignes]

    def alerte_deja_envoyee(self, cle: str) -> bool:
        with closing(self._connexion()) as c:
            return c.execute("SELECT 1 FROM alertes WHERE cle = ?", (cle,)).fetchone() is not None

    def noter_alerte(self, cle: str, horodatage: str, message: str) -> None:
        with closing(self._connexion()) as c, c:
            c.execute("INSERT OR IGNORE INTO alertes (cle, horodatage, message) VALUES (?, ?, ?)", (cle, horodatage, message))

    def dernieres_alertes(self, limite: int = 5) -> list[dict]:
        with closing(self._connexion()) as c:
            lignes = c.execute("SELECT * FROM alertes ORDER BY horodatage DESC LIMIT ?", (limite,)).fetchall()
        return [dict(l) for l in lignes]
