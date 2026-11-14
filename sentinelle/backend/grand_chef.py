"""Le Grand Chef (JARVIS) : reçoit les demandes de Monsieur et répond en une seule réponse.

Il ne fait jamais le travail lui-même : il confie des missions aux commandants grâce à un outil,
`consulter_commandants`, qui les fait travailler en parallèle. Puis il rédige la réponse finale.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from cerveau import Cerveau, Demande, Reponse, cerveau_claude
from commandants.base import Commandant
from config import Reglages
from journal import Journal, Trace, maintenant_texte
from sections import SECTIONS

NOM_OUTIL = "consulter_commandants"


@dataclass
class Resultat:
    reponse: Reponse
    trace: Trace


def consigne_systeme(commandants: dict[str, Commandant]) -> str:
    etats = []
    for s in SECTIONS:
        if s["id"] in commandants:
            etats.append(f"- {s['icone']} {s['nom']} ({s['commandant']}) : EN SERVICE (id « {s['id']} ») — {commandants[s['id']].description}")
        else:
            etats.append(f"- {s['icone']} {s['nom']} ({s['commandant']}) : pas encore construite")
    lignes_sections = "\n".join(etats)
    return f"""Tu es le Grand Chef de Sentinelle, l'assistant personnel de Monsieur, dans le style de JARVIS (Iron Man).

Ton et langue :
- Réponds toujours en français, en vouvoyant, en t'adressant à lui par « Monsieur ».
- Ton calme, précis, élégant, avec une pointe d'humour britannique discret. Réponses courtes et claires.
- Écris en texte simple : pas de titres ni de tableaux Markdown (le **gras** est permis, avec parcimonie).
- Monsieur vit à Genève : prix en CHF, heure de Zurich.

Ton rôle :
- Tu diriges 10 commandants ; chacun dirige 5 agents spécialisés. Tu ne fais jamais leur travail toi-même.
- Pour toute demande qui concerne une section en service, appelle l'outil « {NOM_OUTIL} » avec une mission
  claire et complète pour chaque commandant concerné (tu peux en consulter plusieurs dans le même appel).
  Ensuite, rédige UNE seule réponse à partir de leurs comptes rendus, en gardant les chiffres exacts.
- Pour une simple conversation (bonjour, merci…), réponds directement sans outil.
- État des sections :
{lignes_sections}
- Si Monsieur demande quelque chose qui relève d'une section pas encore construite, dis-le simplement
  et indique qu'elle sera construite prochainement.

Règles absolues :
- N'invente jamais de données (cours de bourse, prix, résultats sportifs, météo…). Si tu n'as pas l'information, dis-le.
- Bourse : tu informes seulement. Ne recommande jamais d'acheter ou de vendre, et ne passe aucun ordre.
- Ne supprime rien, n'achète rien, n'envoie aucun mail sans le bouton « Confirmer » de Monsieur."""


def _prompt(historique: list[tuple[str, str]], message: str, section: str | None = None) -> str:
    morceaux = [f"Nous sommes le {maintenant_texte()}."]
    noms = {s["id"]: f"{s['nom']} ({s['commandant']})" for s in SECTIONS}
    if section in noms:
        morceaux.append(f"Monsieur adresse cette demande en priorité à la section {noms[section]}.")
    if historique:
        morceaux.append("Derniers échanges de la conversation :")
        morceaux += [f"Monsieur : {d}\nToi : {r}" for d, r in historique]
    morceaux.append(f"Nouveau message de Monsieur : {message}")
    return "\n\n".join(morceaux)


class GrandChef:
    MEMOIRE = 10  # nombre d'échanges gardés en mémoire pour suivre la conversation

    def __init__(
        self,
        reglages: Reglages,
        journal: Journal,
        cerveau: Cerveau | None = None,
        commandants: dict[str, Commandant] | None = None,
    ) -> None:
        self.reglages = reglages
        self.journal = journal
        self.cerveau = cerveau or cerveau_claude
        self.commandants = commandants or {}
        self.historique: list[tuple[str, str]] = []

    def _outil_commandants(self, trace: Trace):
        """Construit l'outil que le Grand Chef appelle pour confier des missions (en parallèle)."""
        from claude_agent_sdk import tool

        ids = list(self.commandants)
        schema = {
            "type": "object",
            "properties": {
                "missions": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "commandant": {"type": "string", "enum": ids},
                            "mission": {"type": "string", "description": "Mission claire et complète, en français."},
                        },
                        "required": ["commandant", "mission"],
                    },
                }
            },
            "required": ["missions"],
        }

        @tool(NOM_OUTIL, "Confie une mission à un ou plusieurs commandants (ils travaillent en parallèle) et renvoie leurs comptes rendus.", schema)
        async def consulter(args: dict) -> dict:
            missions = [m for m in args.get("missions", []) if m.get("commandant") in self.commandants]
            if not missions:
                return {"content": [{"type": "text", "text": "Aucun commandant valide."}], "is_error": True}
            rapports = await asyncio.gather(
                *(self.commandants[m["commandant"]].executer(m["mission"], trace) for m in missions),
                return_exceptions=True,
            )
            texte = "\n\n".join(
                f"Compte rendu du {self.commandants[m['commandant']].nom} :\n"
                + (f"(échec : {type(r).__name__})" if isinstance(r, BaseException) else r)
                for m, r in zip(missions, rapports)
            )
            return {"content": [{"type": "text", "text": texte}]}

        return consulter

    async def repondre(
        self, message: str, historique: list[tuple[str, str]] | None = None, section: str | None = None
    ) -> Resultat:
        """Répond à Monsieur. `historique` : derniers échanges de la discussion (sinon, mémoire interne)."""
        memoire_interne = historique is None
        if memoire_interne:
            historique = self.historique
        message = message.strip()
        trace = Trace(self.journal)
        if not message:
            return Resultat(Reponse("Je vous écoute, Monsieur.", modele="aucun", duree_ms=0), trace)

        if not self.reglages.cle_presente and self.cerveau is cerveau_claude:
            reponse = Reponse(
                "Bonjour Monsieur. Mes systèmes sont en ligne, mais il me manque ma clé API Anthropic "
                "pour réfléchir. Copiez le fichier .env.example en .env, collez-y votre clé, "
                "puis relancez Sentinelle.",
                modele="aucun",
                duree_ms=0,
                erreur=True,
            )
        else:
            demande = Demande(
                qui="grand_chef",
                systeme=consigne_systeme(self.commandants),
                prompt=_prompt(historique[-self.MEMOIRE:], message, section),
                modele=self.reglages.modele_grand_chef,
                effort=self.reglages.effort_grand_chef,
                outils=[self._outil_commandants(trace)] if self.commandants else [],
                tours_max=4,
            )
            reponse = await self.cerveau(demande)
            if not reponse.erreur and memoire_interne:
                self.historique.append((message, reponse.texte))

        trace.noter("grand_chef", message, reponse)
        return Resultat(reponse, trace)
