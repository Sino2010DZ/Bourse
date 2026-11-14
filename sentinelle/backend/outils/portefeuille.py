"""Le portefeuille de Monsieur : quelles actions, combien, à quel prix d'achat.

Stocké dans data/portefeuille.json (reste sur l'ordinateur, jamais publié).
Les quantités et prix d'achat sont vides au départ : Monsieur les remplit dans l'app.
"""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path

# Devises reconnues. « GBp » = pence britanniques (1/100 de livre), comme à la bourse de Londres.
DEVISES = {"CHF", "USD", "EUR", "GBP", "GBp"}

PORTEFEUILLE_DE_DEPART = {
    "positions": [
        {"ticker": "AMD", "nom": "AMD", "devise": "USD", "quantite": None, "prix_achat": None},
        {
            "ticker": "SXLK.SW",
            "nom": "SPDR S&P U.S. Technology (ETF)",
            "devise": "USD",
            "quantite": None,
            "prix_achat": None,
        },
        {"ticker": "AML.L", "nom": "Aston Martin", "devise": "GBp", "quantite": None, "prix_achat": None},
    ],
    # Actions surveillées par l'agent Radar en plus du portefeuille
    "radar": ["NVDA", "AAPL", "MSFT", "TSLA", "INTC", "NESN.SW", "NOVN.SW", "UBSG.SW"],
    "seuil_radar_pct": 4.0,
}


class ErreurPortefeuille(ValueError):
    pass


def valider(donnees: dict) -> dict:
    """Vérifie et nettoie un portefeuille. Lève ErreurPortefeuille avec un message clair en français."""
    if not isinstance(donnees, dict):
        raise ErreurPortefeuille("Format invalide.")
    positions = []
    for p in donnees.get("positions", []):
        ticker = str(p.get("ticker", "")).strip().upper()
        if not ticker or len(ticker) > 20:
            raise ErreurPortefeuille("Chaque position doit avoir un ticker (ex. AMD).")
        devise = str(p.get("devise", "USD")).strip()
        if devise not in DEVISES:
            raise ErreurPortefeuille(f"Devise inconnue pour {ticker} : {devise}.")
        position = {"ticker": ticker, "nom": str(p.get("nom") or ticker)[:60], "devise": devise}
        for champ in ("quantite", "prix_achat"):
            valeur = p.get(champ)
            if valeur in (None, ""):
                position[champ] = None
                continue
            try:
                valeur = float(valeur)
            except (TypeError, ValueError):
                raise ErreurPortefeuille(f"{champ} de {ticker} doit être un nombre.") from None
            if valeur < 0:
                raise ErreurPortefeuille(f"{champ} de {ticker} ne peut pas être négatif.")
            position[champ] = valeur
        positions.append(position)
    radar = [str(t).strip().upper() for t in donnees.get("radar", []) if str(t).strip()][:30]
    try:
        seuil = float(donnees.get("seuil_radar_pct", 4.0))
    except (TypeError, ValueError):
        raise ErreurPortefeuille("Le seuil du radar doit être un nombre.") from None
    return {"positions": positions, "radar": radar, "seuil_radar_pct": max(0.5, min(seuil, 50.0))}


class Portefeuille:
    def __init__(self, dossier_donnees: Path) -> None:
        self.chemin = dossier_donnees / "portefeuille.json"
        self._verrou = threading.Lock()

    def lire(self) -> dict:
        with self._verrou:
            if not self.chemin.exists():
                return deepcopy(PORTEFEUILLE_DE_DEPART)
            return valider(json.loads(self.chemin.read_text(encoding="utf-8")))

    def enregistrer(self, donnees: dict) -> dict:
        propre = valider(donnees)
        with self._verrou:
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
            self.chemin.write_text(json.dumps(propre, ensure_ascii=False, indent=2), encoding="utf-8")
        return propre

    def tickers(self) -> list[str]:
        return [p["ticker"] for p in self.lire()["positions"]]
