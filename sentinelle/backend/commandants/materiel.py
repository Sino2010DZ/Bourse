"""Commandant Tech — section Matériel PC : conseils de pièces, compatibilité, tests, pilotes, performance."""

from __future__ import annotations

import asyncio

from commandants.base import Commandant, Outil
from plateforme import systeme

# Configuration connue de Monsieur (SENTINELLE.md). Les infos réelles de l'ordinateur sont lues en plus.
MA_CONFIG = {"carte_graphique": "AMD Radeon RX 9070 XT", "memoire_vive": "DDR4"}


class CommandantTech(Commandant):
    section = "materiel"
    nom = "Commandant Tech"
    description = (
        "Matériel PC : conseils de pièces (config de Monsieur : Radeon RX 9070 XT, RAM DDR4), compatibilité entre pièces, "
        "tests et avis, mises à jour de pilotes (AMD / macOS), performance, batterie et réglages graphiques."
    )

    def outils(self) -> dict[str, Outil]:
        return {"ma_config": self._config, "infos_ordinateur": self._infos, "batterie": self._batterie}

    async def _config(self, mission: str) -> dict:
        return MA_CONFIG

    async def _infos(self, mission: str) -> dict:
        return await asyncio.to_thread(systeme().infos_materiel)

    async def _batterie(self, mission: str) -> dict:
        b = await asyncio.to_thread(systeme().batterie)
        return b or {"info": "Pas de batterie (ordinateur de bureau) ou information indisponible."}
