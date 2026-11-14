"""Réglages de Sentinelle, lus depuis le fichier .env (jamais écrits dans le code).

Deux façons de lancer Sentinelle :
- depuis le code source (développement) : données dans backend/data/, clé dans sentinelle/.env ;
- depuis l'application Sentinelle.app : données et clé dans le dossier de l'app
  (~/Library/Application Support/Sentinelle sur Mac), indiqué par SENTINELLE_DONNEES.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

EST_APPLICATION = getattr(sys, "frozen", False)  # True dans Sentinelle.app (serveur empaqueté)

RACINE = Path(__file__).resolve().parent.parent  # dossier « sentinelle/ » (code source)
DOSSIER_BACKEND = RACINE / "backend"
DOSSIER_UI = RACINE / "app" / "ui"


def _dossier_donnees_par_defaut() -> Path:
    if not EST_APPLICATION:
        return DOSSIER_BACKEND / "data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Sentinelle"
    if sys.platform.startswith("win"):
        return Path(os.getenv("APPDATA", Path.home())) / "Sentinelle"
    return Path.home() / ".sentinelle"


DOSSIER_DONNEES = Path(os.getenv("SENTINELLE_DONNEES") or _dossier_donnees_par_defaut())
FICHIER_CLE = DOSSIER_DONNEES / ".env"   # où l'app enregistre la clé collée dans l'interface

load_dotenv(RACINE / ".env")
load_dotenv(FICHIER_CLE)

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
        return cle_valide(self.cle_api)


def cle_valide(cle: str) -> bool:
    return cle.startswith("sk-ant-") and 20 <= len(cle) <= 300 and cle.isascii() and " " not in cle


def charger_reglages() -> Reglages:
    return Reglages(
        cle_api=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        modele_grand_chef=os.getenv("MODELE_GRAND_CHEF", "claude-opus-5-5").strip(),
        modele_agents=os.getenv("MODELE_AGENTS", "claude-haiku-5-5").strip(),
        effort_grand_chef=os.getenv("EFFORT_GRAND_CHEF", "low").strip(),
        port=int(os.getenv("PORT", "8765")),
        dossier_donnees=DOSSIER_DONNEES,
    )


def enregistrer_cle(cle: str, dossier_donnees: Path) -> None:
    """Enregistre la clé API dans le fichier .env du dossier de données (lisible par vous seul)."""
    fichier = dossier_donnees / ".env"
    dossier_donnees.mkdir(parents=True, exist_ok=True)
    lignes = []
    if fichier.exists():
        lignes = [l for l in fichier.read_text(encoding="utf-8").splitlines() if not l.startswith("ANTHROPIC_API_KEY=")]
    lignes.append(f"ANTHROPIC_API_KEY={cle}")
    fichier.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    try:
        fichier.chmod(0o600)
    except OSError:
        pass
    os.environ["ANTHROPIC_API_KEY"] = cle   # le cerveau (Claude Agent SDK) la lit ici
