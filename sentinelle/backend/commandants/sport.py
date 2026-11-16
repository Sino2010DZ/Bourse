"""Commandant Stade — section Sport : Formule 1 (données officielles Jolpica), NBA et football (web)."""

from __future__ import annotations

from cerveau import Cerveau
from commandants.base import Commandant, Outil
from config import Reglages
from outils.f1 import ServiceF1


class CommandantStade(Commandant):
    section = "sport"
    nom = "Commandant Stade"
    description = (
        "Sport : Formule 1 (prochaine course et horaires à l'heure de Zurich, résultats, classements), matchs NBA, "
        "football, statistiques et classements."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, f1: ServiceF1) -> None:
        super().__init__(reglages, cerveau)
        self.f1 = f1

    def outils(self) -> dict[str, Outil]:
        return {"f1_calendrier": self._prochaine, "f1_resultats": self._resultats, "f1_classements": self._classements}

    async def _prochaine(self, mission: str) -> dict:
        return await self.f1.prochaine() or {"info": "Saison terminée : pas de prochaine course au calendrier."}

    async def _resultats(self, mission: str) -> dict:
        return await self.f1.dernier_resultat() or {"info": "Aucun résultat cette saison."}

    async def _classements(self, mission: str) -> dict:
        return await self.f1.classements()
