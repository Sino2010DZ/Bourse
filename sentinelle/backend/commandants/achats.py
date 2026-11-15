"""Commandant Achats — section Prix & Achats.

Agents en service : Chasseur, Historien, Alarme (fiches dans agents/achats/).
Comparateur et Black Friday arriveront avec la section Renseignement (recherche web).
Règle absolue : rien n'est jamais acheté. Sentinelle informe et donne le lien Galaxus.
"""

from __future__ import annotations

from cerveau import Cerveau
from commandants.base import Commandant, Outil
from config import Reglages
from outils.base_de_donnees import BaseDeDonnees
from outils.suivi_prix import SuiviPrix


class CommandantAchats(Commandant):
    section = "achats"
    nom = "Commandant Achats"
    description = (
        "Prix & Achats : produits Galaxus suivis par Monsieur, prix actuel en CHF, historique et courbe des prix, "
        "baisses de prix et alertes. Ne fait jamais d'achat."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, suivi: SuiviPrix, base: BaseDeDonnees) -> None:
        super().__init__(reglages, cerveau)
        self.suivi = suivi
        self.base = base

    def outils(self) -> dict[str, Outil]:
        return {
            "produits_suivis": self._produits,
            "historique_prix": self._historique,
            "alertes_prix": self._alertes,
        }

    async def _produits(self, mission: str) -> list[dict]:
        champs = ("id", "nom", "url", "prix", "prix_precedent", "variation", "prix_min", "prix_max",
                  "premier_prix", "dernier_releve", "nb_releves", "statut", "message")
        produits = []
        for f in self.suivi.liste():
            p = {k: f[k] for k in champs}
            source = f["historique"][-1]["source"] if f["historique"] else None
            p["source_du_prix_actuel"] = {
                "auto": "lu automatiquement sur Galaxus",
                "manuel": "saisi à la main par Monsieur d'après la page Galaxus (fiable)",
            }.get(source, "aucun prix encore")
            if f["statut"] != "ok":
                p["lecture_automatique"] = "refusée par Galaxus : Monsieur note les prix à la main"
            produits.append(p)
        return produits or [{"info": "Aucun produit suivi pour l'instant."}]

    async def _historique(self, mission: str) -> list[dict]:
        return [
            {"nom": f["nom"], "devise": "CHF", "releves": [{"date": h["horodatage"][:16].replace("T", " "), "prix": h["prix"], "source": h["source"]} for h in f["historique"][-60:]]}
            for f in self.suivi.liste()
        ] or [{"info": "Aucun produit suivi pour l'instant."}]

    async def _alertes(self, mission: str) -> list[dict]:
        alertes = [a for a in self.base.dernieres_alertes(20) if a["cle"].startswith("prix:")]
        return alertes or [{"info": "Aucune baisse de prix détectée pour l'instant."}]
