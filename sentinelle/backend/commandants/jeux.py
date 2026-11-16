"""Commandant Gaming — section Jeux vidéo : soldes, mises à jour, mods, astuces, jeux installés."""

from __future__ import annotations

import asyncio

from commandants.base import Commandant, Outil
from commandants.materiel import MA_CONFIG
from outils.ordinateur import jeux_epic, jeux_steam
from plateforme import systeme


class CommandantGaming(Commandant):
    section = "jeux"
    nom = "Commandant Gaming"
    description = (
        "Jeux vidéo : jeux en solde, résumés des mises à jour (patchs), mods (Forza…), astuces et guides, "
        "et liste des jeux installés (Steam, Epic) sur l'ordinateur de Monsieur."
    )

    def outils(self) -> dict[str, Outil]:
        return {"jeux_installes": self._installes, "ma_config": self._config}

    async def _config(self, mission: str) -> dict:
        return MA_CONFIG

    async def _installes(self, mission: str) -> dict:
        def lire():
            d = systeme().dossiers_jeux()
            jeux = jeux_steam(d.get("steam", [])) + jeux_epic(d.get("epic", []))
            return {"jeux": jeux} if jeux else {"info": "Aucun jeu Steam ou Epic trouvé sur cet ordinateur."}

        return await asyncio.to_thread(lire)
