"""Commandant Finance — section Bourse.

Agents : Trader, Journaliste, Comptable, Analyste, Radar (fiches dans agents/bourse/).
Ils informent seulement : aucun ordre d'achat ou de vente, jamais.
"""

from __future__ import annotations

from cerveau import Cerveau
from commandants.base import Commandant, Outil
from config import Reglages
from outils.bourse import ServiceBourse
from outils.portefeuille import Portefeuille


class CommandantFinance(Commandant):
    section = "bourse"
    nom = "Commandant Finance"
    description = (
        "Bourse : cours des actions de Monsieur (AMD, ETF SPDR US Tech, Aston Martin), actualités qui les "
        "concernent, valeur du portefeuille et gains/pertes, tendances techniques, actions qui bougent fort."
    )

    def __init__(self, reglages: Reglages, cerveau: Cerveau, bourse: ServiceBourse, portefeuille: Portefeuille) -> None:
        super().__init__(reglages, cerveau)
        self.bourse = bourse
        self.portefeuille = portefeuille

    def outils(self) -> dict[str, Outil]:
        return {
            "cours_portefeuille": self._cours,
            "actus_portefeuille": self._actus,
            "positions_portefeuille": self._positions,
            "indicateurs_portefeuille": self._indicateurs,
            "radar_marche": self._radar,
        }

    def _noms(self) -> dict[str, dict]:
        return {p["ticker"]: p for p in self.portefeuille.lire()["positions"]}

    async def _cours(self, mission: str) -> list[dict]:
        resultat = []
        for ticker, p in self._noms().items():
            f = await self.bourse.fiche(ticker)
            resultat.append(
                {
                    "ticker": ticker,
                    "nom": p["nom"],
                    "devise": p["devise"],
                    **{k: f.get(k) for k in ("disponible", "date", "prix", "cloture_veille", "variation_jour_pct", "perf_1_semaine_pct")},
                }
            )
        return resultat

    async def _actus(self, mission: str) -> dict:
        return {f"{p['nom']} ({t})": await self.bourse.actus(t) for t, p in self._noms().items()}

    async def _positions(self, mission: str) -> dict:
        return await self.bourse.positions(self.portefeuille.lire())

    async def _indicateurs(self, mission: str) -> list[dict]:
        resultat = []
        for ticker, p in self._noms().items():
            f = await self.bourse.fiche(ticker)
            f = {k: v for k, v in f.items() if k != "20_dernieres_clotures"}
            resultat.append({"nom": p["nom"], "devise": p["devise"], **f})
        return resultat

    async def _radar(self, mission: str) -> dict:
        pf = self.portefeuille.lire()
        tickers = list(dict.fromkeys([p["ticker"] for p in pf["positions"]] + pf["radar"]))
        return await self.bourse.radar(tickers, pf["seuil_radar_pct"])
