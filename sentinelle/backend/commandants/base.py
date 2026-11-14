"""Le modèle commun à tous les commandants.

Un commandant :
1. lit les fiches .md des agents de sa section ;
2. choisit les agents utiles pour la mission (petit appel au modèle le moins cher) ;
3. prépare les données de chaque agent (outils exécutés par le programme, chiffres exacts) ;
4. lance ses agents en parallèle ;
5. résume leurs rapports en un court compte rendu pour le Grand Chef.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

from agents.chargeur import FicheAgent, agents_de_section
from cerveau import Cerveau, Demande
from config import Reglages
from journal import Trace, maintenant_texte

# Un outil reçoit la mission et renvoie des données (dict/list) que l'agent lira.
Outil = Callable[[str], Awaitable[Any]]


class Commandant:
    section: str = ""
    nom: str = ""
    description: str = ""          # ce que le Grand Chef doit savoir pour lui confier une mission

    def __init__(self, reglages: Reglages, cerveau: Cerveau) -> None:
        self.reglages = reglages
        self.cerveau = cerveau

    # À définir par chaque commandant : nom d'outil -> fonction qui produit les données.
    def outils(self) -> dict[str, Outil]:
        return {}

    def agents(self) -> list[FicheAgent]:
        return agents_de_section(self.section)

    # ------------------------------------------------------------------ étapes

    async def choisir_agents(self, mission: str, agents: list[FicheAgent], trace: Trace) -> list[FicheAgent]:
        ids = [a.id for a in agents]
        liste = "\n".join(f"- {a.id} : {a.role}" for a in agents)
        schema = {
            "type": "object",
            "properties": {"agents": {"type": "array", "items": {"type": "string", "enum": ids}}},
            "required": ["agents"],
            "additionalProperties": False,
        }
        demande = Demande(
            qui=f"{self.section}/commandant",
            systeme=(
                f"Tu es le {self.nom}. Choisis le plus petit nombre d'agents nécessaires pour accomplir la mission. "
                "Si la mission est générale (ex. « comment vont mes actions »), prends les agents qui donnent "
                "les cours, les gains et les actualités."
            ),
            prompt=f"Tes agents :\n{liste}\n\nMission : {mission}",
            modele=self.reglages.modele_agents,
            format_json=schema,
            tours_max=2,
        )
        r = await self.cerveau(demande)
        trace.noter(demande.qui, f"[choix des agents] {mission}", r)
        choisis = []
        if not r.erreur and isinstance(r.donnees, dict):
            choisis = [i for i in r.donnees.get("agents", []) if i in ids]
        if not choisis:  # en cas de doute, on interroge les agents principaux
            choisis = ids[:3]
        return [a for a in agents if a.id in dict.fromkeys(choisis)]

    async def preparer_donnees(self, agent: FicheAgent, mission: str, deja: dict[str, Any]) -> dict[str, Any]:
        outils = self.outils()
        donnees = {}
        for nom in agent.outils:
            if nom not in deja:
                if nom not in outils:
                    deja[nom] = {"erreur": f"outil « {nom} » indisponible"}
                else:
                    try:
                        deja[nom] = await outils[nom](mission)
                    except Exception as exc:
                        deja[nom] = {"erreur": f"données indisponibles ({type(exc).__name__})"}
            donnees[nom] = deja[nom]
        return donnees

    async def lancer_agent(self, agent: FicheAgent, mission: str, donnees: dict, trace: Trace) -> tuple[FicheAgent, str]:
        demande = Demande(
            qui=f"{self.section}/{agent.id}",
            systeme=agent.instructions,
            prompt=(
                f"Nous sommes le {maintenant_texte()}.\n\n"
                f"Mission de ton commandant : {mission}\n\n"
                "Données fournies par le programme (chiffres exacts) :\n"
                f"```json\n{json.dumps(donnees, ensure_ascii=False, default=str)}\n```"
            ),
            modele=self.reglages.modele_agents,
        )
        r = await self.cerveau(demande)
        trace.noter(demande.qui, mission, r)
        return agent, ("(rapport indisponible)" if r.erreur else r.texte)

    async def resumer(self, mission: str, rapports: list[tuple[FicheAgent, str]], trace: Trace) -> str:
        if len(rapports) == 1:
            return rapports[0][1]
        texte = "\n\n".join(f"Rapport de l'agent {a.nom} :\n{t}" for a, t in rapports)
        demande = Demande(
            qui=f"{self.section}/commandant",
            systeme=(
                f"Tu es le {self.nom}. Fusionne les rapports de tes agents en un compte rendu court et "
                "précis pour le Grand Chef : garde tous les chiffres importants exactement, supprime les "
                "répétitions. Pas de titres. Tu informes seulement, sans conseil d'achat ou de vente."
            ),
            prompt=f"Mission : {mission}\n\n{texte}",
            modele=self.reglages.modele_agents,
        )
        r = await self.cerveau(demande)
        trace.noter(demande.qui, f"[résumé] {mission}", r)
        return texte if r.erreur else r.texte

    # ------------------------------------------------------------------ mission complète

    async def executer(self, mission: str, trace: Trace) -> str:
        agents = self.agents()
        if not agents:
            return f"Le {self.nom} n'a encore aucun agent en service."
        choisis = await self.choisir_agents(mission, agents, trace)
        cache: dict[str, Any] = {}
        donnees = [await self.preparer_donnees(a, mission, cache) for a in choisis]
        rapports = await asyncio.gather(*(self.lancer_agent(a, mission, d, trace) for a, d in zip(choisis, donnees)))
        return await self.resumer(mission, list(rapports), trace)
