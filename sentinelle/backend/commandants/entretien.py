"""Commandant Maintenance — section Entretien.

Les agents observent et PROPOSENT : vider les fichiers temporaires, ranger des fichiers (déplacements seulement),
passer en mode clair ou sombre. Rien n'est exécuté sans le bouton « Confirmer » de Monsieur.
"""

from __future__ import annotations

import asyncio

from cerveau import Cerveau
from commandants.base import ActionImpossible, Commandant, Outil
from outils.actions_ordinateur import RefusAction, estimer_temporaires, verifier_rangement
from config import Reglages
from outils.ordinateur import inventaire_dossiers, taille_dossier
from outils.preferences import Preferences
from plateforme import systeme


class CommandantMaintenance(Commandant):
    section = "entretien"
    nom = "Commandant Maintenance"
    description = (
        "Entretien de l'ordinateur (lecture seule) : rangement des dossiers choisis par Monsieur, place prise par les "
        "caches et fichiers temporaires, état des sauvegardes (Time Machine / OneDrive), température, thème et éclairage."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, preferences: Preferences) -> None:
        super().__init__(reglages, cerveau)
        self.preferences = preferences

    def outils(self) -> dict[str, Outil]:
        return {
            "dossiers_choisis": self._dossiers,
            "caches": self._caches,
            "sauvegarde": self._sauvegarde,
            "temperatures": self._temperatures,
            "apparence": self._apparence,
        }

    async def _dossiers(self, mission: str) -> dict:
        return await asyncio.to_thread(inventaire_dossiers, self.preferences.lire()["dossiers_autorises"])

    async def _caches(self, mission: str) -> list[dict]:
        return await asyncio.to_thread(lambda: [taille_dossier(d) for d in systeme().dossiers_temporaires()])

    async def _sauvegarde(self, mission: str) -> dict:
        return await asyncio.to_thread(systeme().sauvegarde)

    async def _temperatures(self, mission: str) -> dict:
        return await asyncio.to_thread(systeme().temperatures)

    async def _apparence(self, mission: str) -> dict:
        return await asyncio.to_thread(systeme().apparence)

    async def preparer_action(self, type_action: str, parametres: dict) -> tuple[str, dict]:
        try:
            if type_action == "nettoyer_temporaires":
                jours = max(7, int(parametres.get("jours_minimum", 7)))
                estimation = await asyncio.to_thread(estimer_temporaires, jours)
                if not estimation["fichiers"]:
                    raise ActionImpossible(f"aucun fichier temporaire de plus de {jours} jours")
                return (f"supprimer {estimation['fichiers']} fichiers temporaires de plus de {jours} jours "
                        f"({estimation['taille_mo']} Mo) dans {estimation['dossier']}"), {"jours": jours}
            if type_action == "ranger_fichiers":
                dossier = str(parametres.get("dossier", ""))
                propres = await asyncio.to_thread(
                    verifier_rangement, dossier, list(parametres.get("deplacements") or []),
                    self.preferences.lire()["dossiers_autorises"],
                )
                sous = sorted({d["vers"] for d in propres})
                return (f"ranger {len(propres)} fichiers de {dossier} dans {len(sous)} sous-dossiers "
                        f"({', '.join(sous[:6])}) — déplacements seulement, rien n'est supprimé"), {"dossier": dossier, "deplacements": propres}
            if type_action == "changer_theme":
                mode = str(parametres.get("mode", ""))
                if mode not in ("clair", "sombre"):
                    raise ActionImpossible("le mode doit être « clair » ou « sombre »")
                return f"passer l'ordinateur en mode {mode}", {"mode": mode}
        except (RefusAction, ValueError, TypeError) as e:
            raise ActionImpossible(str(e)) from None
        raise ActionImpossible("action inconnue")
