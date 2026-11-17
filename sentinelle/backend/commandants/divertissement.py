"""Commandant Détente — section Divertissement : musique (Spotify), films, séries, sorties à Genève.

Le DJ lit les goûts de Monsieur sur Spotify et PROPOSE des playlists : elles ne sont créées qu'après « Confirmer ».
"""

from __future__ import annotations

import asyncio

from cerveau import Cerveau
from commandants.base import ActionImpossible, Commandant, Outil
from config import Reglages
from outils.spotify import ErreurSpotify


class CommandantDetente(Commandant):
    section = "divertissement"
    nom = "Commandant Détente"
    description = (
        "Divertissement : découverte de musique, critiques de films et séries (vaut le coup ou pas), nouvelles sorties "
        "cinéma et streaming, concerts et événements à Genève, playlists Spotify (DJ) et musique en cours."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, spotify=None) -> None:
        super().__init__(reglages, cerveau)
        self.spotify = spotify

    def outils(self) -> dict[str, Outil]:
        return {"spotify_profil": self._profil}

    async def _profil(self, mission: str) -> dict:
        if self.spotify is None or not self.spotify.comptes.spotify():
            return {"connecte": False, "info": "Spotify non connecté : Monsieur peut le connecter dans Réglages › Comptes."}
        try:
            en_cours = await asyncio.to_thread(self.spotify.en_cours)
            profil = await asyncio.to_thread(self.spotify.profil_musical)
        except ErreurSpotify as e:
            return {"connecte": True, "erreur": str(e)}
        return {"connecte": True, "en_cours": en_cours, **profil}

    async def preparer_action(self, type_action: str, parametres: dict) -> tuple[str, dict]:
        if type_action != "spotify_creer_playlist":
            raise ActionImpossible("action inconnue")
        if self.spotify is None or not self.spotify.comptes.spotify():
            raise ActionImpossible("Spotify n'est pas connecté")
        nom = str(parametres.get("nom", "")).strip()[:100] or "Sélection Sentinelle"
        titres = parametres.get("titres") or []
        if not isinstance(titres, list) or not titres:
            raise ActionImpossible("aucun titre proposé")
        trouves, absents = [], []
        for t in titres[:50]:
            if not isinstance(t, dict):
                continue
            # Les titres sont retrouvés sur Spotify par le programme : aucun identifiant n'est inventé.
            res = await asyncio.to_thread(self.spotify.chercher_titre, str(t.get("titre", "")), str(t.get("artiste", "")))
            (trouves if res else absents).append(res or f"{t.get('titre')} — {t.get('artiste')}")
        if not trouves:
            raise ActionImpossible("aucun des titres proposés n'a été trouvé sur Spotify")
        description = f"créer la playlist privée « {nom} » sur Spotify avec {len(trouves)} titres"
        if absents:
            description += f" ({len(absents)} introuvables : {', '.join(absents[:5])})"
        return description, {"nom": nom, "description": str(parametres.get("description", ""))[:300],
                             "uris": [t["uri"] for t in trouves], "titres": [f"{t['titre']} — {t['artiste']}" for t in trouves]}
