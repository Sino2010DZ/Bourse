"""Commandant Secrétariat — section Organisation : météo de Genève et briefing du matin.

Agenda, Rappels et Courrier (Gmail) demandent l'accès aux comptes de Monsieur : ils seront branchés
plus tard, avec son autorisation explicite.
"""

from __future__ import annotations

from cerveau import Cerveau
from commandants.base import Commandant, Outil
from config import Reglages
from outils.bourse import ServiceBourse
from outils.f1 import ServiceF1
from outils.meteo import ServiceMeteo
from outils.portefeuille import Portefeuille
from outils.suivi_prix import SuiviPrix


class CommandantSecretariat(Commandant):
    section = "organisation"
    nom = "Commandant Secrétariat"
    description = "Organisation : météo de Genève (aujourd'hui et prochains jours) et briefing du matin (météo, bourse, prix suivis, F1)."

    def __init__(self, reglages: Reglages, cerveau: Cerveau, meteo: ServiceMeteo, bourse: ServiceBourse,
                 portefeuille: Portefeuille, suivi: SuiviPrix, f1: ServiceF1) -> None:
        super().__init__(reglages, cerveau)
        self.meteo, self.bourse, self.portefeuille, self.suivi, self.f1 = meteo, bourse, portefeuille, suivi, f1

    def outils(self) -> dict[str, Outil]:
        return {"meteo_geneve": self._meteo, "resume_bourse": self._bourse, "resume_prix": self._prix, "f1_calendrier": self._f1}

    async def _meteo(self, mission: str) -> dict:
        return await self.meteo.geneve()

    async def _bourse(self, mission: str) -> dict:
        pos = await self.bourse.positions(self.portefeuille.lire())
        return {
            "actions": [{k: p[k] for k in ("nom", "prix", "devise", "variation_jour_pct", "date_cours", "valeur_chf")} for p in pos["positions"]],
            "valeur_totale_chf": pos["valeur_totale_chf"] if pos["valeurs_completes"] else None,
        }

    async def _prix(self, mission: str) -> list[dict]:
        return [{k: f[k] for k in ("nom", "prix", "variation", "prix_min")} for f in self.suivi.liste()] or [{"info": "Aucun produit suivi."}]

    async def _f1(self, mission: str) -> dict:
        return await self.f1.prochaine() or {"info": "Pas de course F1 à venir."}

    async def briefing(self, trace) -> str | None:
        """Le briefing du matin, préparé directement par l'agent Briefing (sans passer par le choix des agents)."""
        agent = next((a for a in self.agents() if a.id == "briefing"), None)
        if agent is None:
            return None
        mission = "Prépare le briefing du matin de Monsieur."
        donnees = await self.preparer_donnees(agent, mission, {})
        _, texte = await self.lancer_agent(agent, mission, donnees, trace)
        return None if texte.startswith("(") else texte
