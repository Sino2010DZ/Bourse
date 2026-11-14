"""Réglages de Sentinelle, lus depuis le fichier .env (jamais écrits dans le code)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent  # dossier « sentinelle/ »
DOSSIER_BACKEND = RACINE / "backend"
DOSSIER_DONNEES = DOSSIER_BACKEND / "data"
DOSSIER_UI = RACINE / "app" / "ui"

load_dotenv(RACINE / ".env")

# Prix en dollars US par million de tokens (entrée, sortie).
# Sert seulement de secours : le SDK renvoie déjà le coût exact de chaque échange.
PRIX_PAR_MILLION = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


@dataclass(frozen=True)
class Reglages:
    cle_api: str
    modele_grand_chef: str
    modele_agents: str
    effort_grand_chef: str
    port: int
    dossier_donnees: Path

    @property
    def cle_presente(self) -> bool:
        return self.cle_api.startswith("sk-ant-")


def charger_reglages() -> Reglages:
    return Reglages(
        cle_api=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        modele_grand_chef=os.getenv("MODELE_GRAND_CHEF", "claude-opus-5-5").strip(),
        modele_agents=os.getenv("MODELE_AGENTS", "claude-haiku-5-5").strip(),
        effort_grand_chef=os.getenv("EFFORT_GRAND_CHEF", "low").strip(),
        port=int(os.getenv("PORT", "8765")),
        dossier_donnees=Path(os.getenv("SENTINELLE_DONNEES", str(DOSSIER_DONNEES))),
    )
