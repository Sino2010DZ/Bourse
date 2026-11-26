"""Commandant Atelier — section Création : code, design Liquid Glass, idées, débogage, suivi de projets."""

from __future__ import annotations

from pathlib import Path

from cerveau import Cerveau
from commandants.base import ActionImpossible, Commandant, Outil
from config import Reglages
from outils.ordinateur import dans_dossiers_autorises
from sections import AGENTS, SECTIONS

BUDGET_CHANTIER_USD = 1.0


class CommandantAtelier(Commandant):
    section = "creation"
    nom = "Commandant Atelier"
    description = (
        "Création : écrire du code ou préparer des consignes prêtes à coller dans Claude Code, designs style Liquid Glass "
        "(HTML/CSS), idées de nouveaux projets, recherche de bugs dans un code ou un message d'erreur, avancement des projets."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, preferences=None) -> None:
        super().__init__(reglages, cerveau)
        self.preferences = preferences

    def outils(self) -> dict[str, Outil]:
        return {"projet_sentinelle": self._sentinelle, "projets": self._projets}

    def _dossiers_projets(self) -> list[str]:
        return self.preferences.lire()["dossiers_projets"] if self.preferences else []

    async def _projets(self, mission: str) -> dict:
        projets = []
        for d in self._dossiers_projets():
            base = Path(d).expanduser()
            if base.is_dir():
                contenu = sorted(e.name + ("/" if e.is_dir() else "") for e in base.iterdir() if not e.name.startswith("."))[:60]
                projets.append({"dossier": d, "contenu": contenu})
            else:
                projets.append({"dossier": d, "existe": False})
        return {"projets": projets} if projets else {
            "info": "Aucun projet choisi : Monsieur peut ajouter le dossier d'un projet dans Réglages › Projets."}

    async def preparer_action(self, type_action: str, parametres: dict) -> tuple[str, dict]:
        if type_action != "claude_code_modifier":
            raise ActionImpossible("action inconnue")
        projet = str(parametres.get("projet", "")).strip()
        consigne = str(parametres.get("consigne", "")).strip()
        if not projet or not Path(projet).expanduser().is_dir() or not dans_dossiers_autorises(Path(projet).expanduser(), self._dossiers_projets()):
            raise ActionImpossible("ce dossier n'est pas un projet choisi dans Réglages › Projets")
        if not 10 <= len(consigne) <= 4000:
            raise ActionImpossible("la consigne doit être précise (entre 10 et 4000 caractères)")
        nom = Path(projet).expanduser().name
        apercu = consigne if len(consigne) <= 160 else consigne[:157] + "…"
        return (f"laisser Claude Code modifier le projet « {nom} » : {apercu} — sans terminal ni Internet, "
                f"originaux sauvegardés, budget maximum {BUDGET_CHANTIER_USD:.2f} $"), {"projet": projet, "consigne": consigne}

    async def _sentinelle(self, mission: str) -> dict:
        from agents.chargeur import agents_de_section

        etat = []
        for s in SECTIONS:
            actifs = {a.id for a in agents_de_section(s["id"])}
            etat.append({
                "section": s["nom"],
                "agents_en_service": [n for i, n in AGENTS[s["id"]] if i in actifs],
                "agents_a_construire": [n for i, n in AGENTS[s["id"]] if i not in actifs],
            })
        return {"projet": "Sentinelle", "sections": etat}
