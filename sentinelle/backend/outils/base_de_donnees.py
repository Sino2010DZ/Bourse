"""Mémoire locale de Sentinelle : une base SQLite (data/sentinelle.db).

Phase 2 : historique des cours de bourse et alertes déjà envoyées.
"""

from __future__ import annotations

import json
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
CREATE TABLE IF NOT EXISTS discussions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    titre       TEXT NOT NULL,
    creee       TEXT NOT NULL,
    modifiee    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    discussion_id INTEGER NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
    role          TEXT NOT NULL,      -- « moi » ou « chef »
    texte         TEXT NOT NULL,
    agents        TEXT NOT NULL DEFAULT '[]',   -- agents consultés (JSON)
    meta          TEXT NOT NULL DEFAULT '{}',   -- durée, tokens, coût, erreur (JSON)
    horodatage    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS messages_discussion ON messages(discussion_id, id);
CREATE TABLE IF NOT EXISTS produits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    galaxus_id  TEXT NOT NULL UNIQUE,
    url         TEXT NOT NULL,
    nom         TEXT NOT NULL,
    ajoute      TEXT NOT NULL,
    statut      TEXT NOT NULL DEFAULT 'ok',   -- ok, refuse, introuvable, prix_absent, reseau
    message     TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS prix (
    produit_id  INTEGER NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
    horodatage  TEXT NOT NULL,
    prix        REAL NOT NULL,      -- CHF
    source      TEXT NOT NULL,      -- « auto » (lu sur Galaxus) ou « manuel » (saisi par Monsieur)
    PRIMARY KEY (produit_id, horodatage)
);
CREATE TABLE IF NOT EXISTS archives (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    horodatage  TEXT NOT NULL,
    sujet       TEXT NOT NULL,
    contenu     TEXT NOT NULL
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
        c.execute("PRAGMA foreign_keys = ON")
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

    def supprimer_alertes(self, prefixe: str) -> None:
        with closing(self._connexion()) as c, c:
            c.execute("DELETE FROM alertes WHERE cle LIKE ? ESCAPE '\\'", (prefixe.replace("%", "\\%").replace("_", "\\_") + "%",))

    def dernieres_alertes(self, limite: int = 5) -> list[dict]:
        with closing(self._connexion()) as c:
            lignes = c.execute("SELECT * FROM alertes ORDER BY horodatage DESC LIMIT ?", (limite,)).fetchall()
        return [dict(l) for l in lignes]

    # ------------------------------------------------------------ discussions

    def creer_discussion(self, titre: str, horodatage: str) -> int:
        with closing(self._connexion()) as c, c:
            cur = c.execute(
                "INSERT INTO discussions (titre, creee, modifiee) VALUES (?, ?, ?)", (titre[:80], horodatage, horodatage)
            )
            return int(cur.lastrowid)

    def discussion(self, ident: int) -> dict | None:
        with closing(self._connexion()) as c:
            d = c.execute("SELECT * FROM discussions WHERE id = ?", (ident,)).fetchone()
            if d is None:
                return None
            msgs = c.execute("SELECT * FROM messages WHERE discussion_id = ? ORDER BY id", (ident,)).fetchall()
        return {
            **dict(d),
            "messages": [{**dict(m), "agents": json.loads(m["agents"]), "meta": json.loads(m["meta"])} for m in msgs],
        }

    def discussions(self, recherche: str = "", limite: int = 60) -> list[dict]:
        requete = "SELECT d.* FROM discussions d"
        params: list = []
        if recherche.strip():
            requete += (
                " WHERE d.titre LIKE ? OR EXISTS (SELECT 1 FROM messages m WHERE m.discussion_id = d.id AND m.texte LIKE ?)"
            )
            motif = f"%{recherche.strip()}%"
            params += [motif, motif]
        requete += " ORDER BY d.modifiee DESC, d.id DESC LIMIT ?"
        params.append(limite)
        with closing(self._connexion()) as c:
            return [dict(l) for l in c.execute(requete, params).fetchall()]

    def ajouter_message(self, discussion_id: int, role: str, texte: str, horodatage: str, agents=None, meta=None) -> int:
        with closing(self._connexion()) as c, c:
            cur = c.execute(
                "INSERT INTO messages (discussion_id, role, texte, agents, meta, horodatage) VALUES (?, ?, ?, ?, ?, ?)",
                (discussion_id, role, texte, json.dumps(agents or [], ensure_ascii=False), json.dumps(meta or {}), horodatage),
            )
            c.execute("UPDATE discussions SET modifiee = ? WHERE id = ?", (horodatage, discussion_id))
            return int(cur.lastrowid)

    def supprimer_dernier_message_chef(self, discussion_id: int) -> None:
        """Pour « Régénérer » : retire la dernière réponse du Grand Chef."""
        with closing(self._connexion()) as c, c:
            c.execute(
                "DELETE FROM messages WHERE id = (SELECT id FROM messages WHERE discussion_id = ? ORDER BY id DESC LIMIT 1) AND role = 'chef'",
                (discussion_id,),
            )

    def echanges(self, discussion_id: int, limite: int = 10) -> list[tuple[str, str]]:
        """Les derniers couples (question de Monsieur, réponse du Grand Chef), pour la mémoire."""
        d = self.discussion(discussion_id)
        if not d:
            return []
        paires, question = [], None
        for m in d["messages"]:
            if m["role"] == "moi":
                question = m["texte"]
            elif question is not None and not m["meta"].get("erreur"):
                paires.append((question, m["texte"]))
                question = None
        return paires[-limite:]

    # ------------------------------------------------------------ produits suivis (Galaxus)

    def ajouter_produit(self, galaxus_id: str, url: str, nom: str, horodatage: str) -> int:
        with closing(self._connexion()) as c, c:
            cur = c.execute(
                "INSERT INTO produits (galaxus_id, url, nom, ajoute) VALUES (?, ?, ?, ?)", (galaxus_id, url, nom, horodatage)
            )
            return int(cur.lastrowid)

    def produit(self, ident: int) -> dict | None:
        with closing(self._connexion()) as c:
            l = c.execute("SELECT * FROM produits WHERE id = ?", (ident,)).fetchone()
        return dict(l) if l else None

    def produit_par_galaxus_id(self, galaxus_id: str) -> dict | None:
        with closing(self._connexion()) as c:
            l = c.execute("SELECT * FROM produits WHERE galaxus_id = ?", (galaxus_id,)).fetchone()
        return dict(l) if l else None

    def produits(self) -> list[dict]:
        with closing(self._connexion()) as c:
            return [dict(l) for l in c.execute("SELECT * FROM produits ORDER BY id").fetchall()]

    def modifier_produit(self, ident: int, **champs) -> None:
        autorises = {k: v for k, v in champs.items() if k in ("nom", "statut", "message")}
        if not autorises:
            return
        affectations = ", ".join(f"{k} = ?" for k in autorises)
        with closing(self._connexion()) as c, c:
            c.execute(f"UPDATE produits SET {affectations} WHERE id = ?", (*autorises.values(), ident))

    def supprimer_produit(self, ident: int) -> None:
        with closing(self._connexion()) as c, c:
            c.execute("DELETE FROM produits WHERE id = ?", (ident,))

    def noter_prix(self, produit_id: int, horodatage: str, prix: float, source: str) -> None:
        with closing(self._connexion()) as c, c:
            c.execute(
                "INSERT OR REPLACE INTO prix (produit_id, horodatage, prix, source) VALUES (?, ?, ?, ?)",
                (produit_id, horodatage, prix, source),
            )

    def historique_prix(self, produit_id: int) -> list[dict]:
        with closing(self._connexion()) as c:
            lignes = c.execute(
                "SELECT horodatage, prix, source FROM prix WHERE produit_id = ? ORDER BY horodatage", (produit_id,)
            ).fetchall()
        return [dict(l) for l in lignes]

    # ------------------------------------------------------------ archives (section Renseignement)

    def archiver(self, horodatage: str, sujet: str, contenu: str) -> int:
        with closing(self._connexion()) as c, c:
            cur = c.execute("INSERT INTO archives (horodatage, sujet, contenu) VALUES (?, ?, ?)", (horodatage, sujet[:200], contenu[:20000]))
            return int(cur.lastrowid)

    def archives(self, recherche: str = "", limite: int = 20) -> list[dict]:
        requete, params = "SELECT * FROM archives", []
        if recherche.strip():
            requete += " WHERE sujet LIKE ? OR contenu LIKE ?"
            motif = f"%{recherche.strip()}%"
            params += [motif, motif]
        requete += " ORDER BY id DESC LIMIT ?"
        params.append(limite)
        with closing(self._connexion()) as c:
            return [dict(l) for l in c.execute(requete, params).fetchall()]
