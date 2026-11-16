"""Commandant Atelier — section Création : code, design Liquid Glass, idées, débogage, suivi de projets."""

from __future__ import annotations

from commandants.base import Commandant, Outil
from sections import AGENTS, SECTIONS


class CommandantAtelier(Commandant):
    section = "creation"
    nom = "Commandant Atelier"
    description = (
        "Création : écrire du code ou préparer des consignes prêtes à coller dans Claude Code, designs style Liquid Glass "
        "(HTML/CSS), idées de nouveaux projets, recherche de bugs dans un code ou un message d'erreur, avancement des projets."
    )

    def outils(self) -> dict[str, Outil]:
        return {"projet_sentinelle": self._sentinelle}

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
