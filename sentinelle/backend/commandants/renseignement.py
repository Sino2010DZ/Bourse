"""Commandant Veille — section Renseignement : recherches web, résumés, vérification, traduction, archives."""

from __future__ import annotations

from cerveau import Cerveau
from commandants.base import Commandant, Outil
from config import Reglages
from journal import FUSEAU, Trace
from outils.base_de_donnees import BaseDeDonnees


class CommandantVeille(Commandant):
    section = "renseignement"
    nom = "Commandant Veille"
    description = (
        "Renseignement : recherches sur le web (actualités, informations générales), résumé d'une page ou d'un texte "
        "en 3 phrases, vérification d'une information, traduction en français, et archives des trouvailles passées."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, base: BaseDeDonnees) -> None:
        super().__init__(reglages, cerveau)
        self.base = base

    def outils(self) -> dict[str, Outil]:
        return {"archives": self._archives}

    async def _archives(self, mission: str) -> list[dict]:
        trouvailles = [
            {"date": a["horodatage"][:10], "sujet": a["sujet"], "contenu": a["contenu"][:1500]} for a in self.base.archives(limite=15)
        ]
        return trouvailles or [{"info": "Les archives sont vides pour l'instant."}]

    async def executer(self, mission: str, trace: Trace) -> str:
        """Chaque compte rendu est gardé dans les archives (l'Archiviste pourra le retrouver)."""
        from datetime import datetime

        compte_rendu = await super().executer(mission, trace)
        if compte_rendu and not compte_rendu.startswith("("):
            self.base.archiver(datetime.now(FUSEAU).isoformat(timespec="seconds"), mission, compte_rendu)
        return compte_rendu
