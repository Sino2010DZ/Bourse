"""Commandant Secrétariat — section Organisation : agenda, rappels, courrier, météo, briefing du matin.

Agenda (lien iCal secret) et Courrier (Gmail, mot de passe d'application) sont en LECTURE SEULE et
n'existent que si Monsieur les a connectés dans Réglages › Comptes. Les rappels sont gardés par Sentinelle.
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

SCHEMA_RAPPELS = {
    "type": "object",
    "properties": {
        "reponse": {"type": "string"},
        "nouveaux_rappels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"texte": {"type": "string"}, "echeance": {"type": "string"}},
                "required": ["texte", "echeance"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["reponse", "nouveaux_rappels"],
    "additionalProperties": False,
}


class CommandantSecretariat(Commandant):
    section = "organisation"
    nom = "Commandant Secrétariat"
    description = (
        "Organisation : agenda de Monsieur (rendez-vous à venir, lecture seule), rappels (en créer : « rappelle-moi… », "
        "les lister), tri des mails Gmail non lus (lecture seule), météo de Genève, briefing du matin."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, meteo: ServiceMeteo, bourse: ServiceBourse,
                 portefeuille: Portefeuille, suivi: SuiviPrix, f1: ServiceF1,
                 agenda=None, courrier=None, base=None) -> None:
        super().__init__(reglages, cerveau)
        self.meteo, self.bourse, self.portefeuille, self.suivi, self.f1 = meteo, bourse, portefeuille, suivi, f1
        self.agenda, self.courrier, self.base = agenda, courrier, base

    def outils(self) -> dict[str, Outil]:
        return {
            "meteo_geneve": self._meteo, "resume_bourse": self._bourse, "resume_prix": self._prix, "f1_calendrier": self._f1,
            "agenda": self._agenda, "rappels": self._rappels, "mails_non_lus": self._mails,
        }

    async def _agenda(self, mission: str) -> dict:
        if self.agenda is None:
            return {"connecte": False}
        return await self.agenda.prochains(7)

    async def _rappels(self, mission: str) -> list[dict]:
        if self.base is None:
            return []
        return [{"id": r["id"], "texte": r["texte"], "echeance": r["echeance"]} for r in self.base.rappels()] or [{"info": "Aucun rappel en attente."}]

    async def _mails(self, mission: str) -> dict:
        if self.courrier is None:
            return {"connecte": False}
        return await self.courrier.non_lus()

    async def lancer_agent(self, agent, mission, donnees, trace):
        """L'agent Rappels peut créer des rappels : il répond en JSON, et c'est le programme qui les enregistre."""
        if agent.id != "rappels" or self.base is None:
            return await super().lancer_agent(agent, mission, donnees, trace)
        from datetime import datetime, timedelta
        import json

        from cerveau import Demande
        from commandants.base import regle_perimetre
        from journal import FUSEAU, maintenant_texte

        maintenant = datetime.now(FUSEAU)
        demande = Demande(
            qui="organisation/rappels",
            systeme=agent.instructions + regle_perimetre(agent),
            prompt=(
                f"Nous sommes le {maintenant_texte()} (date et heure ISO : {maintenant.isoformat(timespec='minutes')}).\n\n"
                f"Mission de ton commandant : {mission}\n\nRappels en attente :\n```json\n"
                f"{json.dumps(donnees.get('rappels', []), ensure_ascii=False)}\n```"
            ),
            modele=self.reglages.modele_agents,
            format_json=SCHEMA_RAPPELS,
            tours_max=2,
        )
        r = await self.cerveau(demande)
        trace.noter(demande.qui, mission, r)
        if r.erreur or not isinstance(r.donnees, dict):
            return agent, "(rapport indisponible)"
        lignes = [r.donnees.get("reponse", "").strip()]
        for nouveau in r.donnees.get("nouveaux_rappels", [])[:5]:
            try:
                echeance = datetime.fromisoformat(nouveau["echeance"])
            except (KeyError, ValueError):
                lignes.append(f"(Rappel non créé : date illisible « {nouveau.get('echeance')} ».)")
                continue
            echeance = echeance if echeance.tzinfo else echeance.replace(tzinfo=FUSEAU)
            if echeance < maintenant - timedelta(minutes=5):
                lignes.append(f"(Rappel non créé : la date {echeance:%d.%m.%Y %H:%M} est passée.)")
                continue
            texte = str(nouveau.get("texte", "")).strip()[:300] or "Rappel"
            self.base.ajouter_rappel(texte, echeance.isoformat(timespec="minutes"), maintenant.isoformat(timespec="seconds"))
            lignes.append(f"Rappel créé par Sentinelle : « {texte} » le {echeance:%d.%m.%Y à %H:%M}.")
        return agent, "\n".join(l for l in lignes if l)

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
