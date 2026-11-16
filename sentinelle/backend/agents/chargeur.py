"""Lit les fichiers .md des agents (en-tête entre deux lignes « --- », puis les instructions)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

DOSSIER_AGENTS = Path(__file__).resolve().parent
CHAMPS_OBLIGATOIRES = ("nom", "section", "role", "outils", "systeme")


@dataclass(frozen=True)
class FicheAgent:
    id: str            # nom du fichier sans « .md », ex. « trader »
    nom: str
    section: str
    role: str
    outils: tuple[str, ...]
    systeme: str       # « tous », « mac » ou « windows »
    instructions: str


class ErreurAgent(ValueError):
    pass


def _valeur(brut: str):
    brut = brut.split(" #", 1)[0].strip()          # retire les commentaires en fin de ligne
    if brut.startswith("[") and brut.endswith("]"):
        return tuple(x.strip().strip("'\"") for x in brut[1:-1].split(",") if x.strip())
    return brut.strip("'\"")


def lire_agent(chemin: Path) -> FicheAgent:
    texte = chemin.read_text(encoding="utf-8")
    morceaux = texte.split("---", 2)
    if not texte.startswith("---") or len(morceaux) < 3:
        raise ErreurAgent(f"{chemin.name} : en-tête « --- » manquant.")
    entete = {}
    for ligne in morceaux[1].strip().splitlines():
        if ":" in ligne:
            cle, val = ligne.split(":", 1)
            entete[cle.strip()] = _valeur(val)
    manquants = [c for c in CHAMPS_OBLIGATOIRES if c not in entete]
    if manquants:
        raise ErreurAgent(f"{chemin.name} : champs manquants {manquants}.")
    if entete["systeme"] not in ("tous", "mac", "windows"):
        raise ErreurAgent(f"{chemin.name} : systeme doit être tous, mac ou windows.")
    outils = entete["outils"] if isinstance(entete["outils"], tuple) else (entete["outils"],)
    return FicheAgent(
        # « id » facultatif : permet deux fiches (ex. pilotes-mac.md et pilotes-windows.md) pour un même agent.
        id=entete.get("id") or chemin.stem,
        nom=entete["nom"],
        section=entete["section"],
        role=entete["role"],
        outils=outils,
        systeme=entete["systeme"],
        instructions=morceaux[2].strip(),
    )


def systeme_courant() -> str:
    return "mac" if sys.platform == "darwin" else "windows" if sys.platform.startswith("win") else "autre"


def agents_de_section(section: str, systeme: str | None = None) -> list[FicheAgent]:
    """Tous les agents d'une section qui tournent sur ce système."""
    systeme = systeme or systeme_courant()
    dossier = DOSSIER_AGENTS / section
    if not dossier.is_dir():
        return []
    agents = [lire_agent(p) for p in sorted(dossier.glob("*.md"))]
    return [a for a in agents if a.systeme in ("tous", systeme)]
