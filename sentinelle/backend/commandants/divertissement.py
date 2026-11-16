"""Commandant Détente — section Divertissement : musique, films, séries, sorties à Genève (recherche web).

Le DJ (playlists Spotify) demande l'accès au compte Spotify de Monsieur : il sera branché plus tard.
"""

from __future__ import annotations

from commandants.base import Commandant, Outil


class CommandantDetente(Commandant):
    section = "divertissement"
    nom = "Commandant Détente"
    description = (
        "Divertissement : découverte de musique, critiques de films et séries (vaut le coup ou pas), nouvelles sorties "
        "cinéma et streaming, concerts et événements à Genève."
    )

    def outils(self) -> dict[str, Outil]:
        return {}
