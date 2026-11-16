"""Commandant Maintenance — section Entretien (LECTURE SEULE).

Les agents observent et proposent : rien n'est trié, nettoyé ni supprimé sans le bouton « Confirmer »
de Monsieur (les actions elles-mêmes arriveront dans une version suivante).
"""

from __future__ import annotations

import asyncio

from cerveau import Cerveau
from commandants.base import Commandant, Outil
from config import Reglages
from outils.ordinateur import inventaire_dossiers, taille_dossier
from outils.preferences import Preferences
from plateforme import systeme


class CommandantMaintenance(Commandant):
    section = "entretien"
    nom = "Commandant Maintenance"
    description = (
        "Entretien de l'ordinateur (lecture seule) : rangement des dossiers choisis par Monsieur, place prise par les "
        "caches et fichiers temporaires, état des sauvegardes (Time Machine / OneDrive), température, thème et éclairage."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, preferences: Preferences) -> None:
        super().__init__(reglages, cerveau)
        self.preferences = preferences

    def outils(self) -> dict[str, Outil]:
        return {
            "dossiers_choisis": self._dossiers,
            "caches": self._caches,
            "sauvegarde": self._sauvegarde,
            "temperatures": self._temperatures,
            "apparence": self._apparence,
        }

    async def _dossiers(self, mission: str) -> dict:
        return await asyncio.to_thread(inventaire_dossiers, self.preferences.lire()["dossiers_autorises"])

    async def _caches(self, mission: str) -> list[dict]:
        return await asyncio.to_thread(lambda: [taille_dossier(d) for d in systeme().dossiers_temporaires()])

    async def _sauvegarde(self, mission: str) -> dict:
        return await asyncio.to_thread(systeme().sauvegarde)

    async def _temperatures(self, mission: str) -> dict:
        return await asyncio.to_thread(systeme().temperatures)

    async def _apparence(self, mission: str) -> dict:
        return await asyncio.to_thread(systeme().apparence)
