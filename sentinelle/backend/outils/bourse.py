"""Outil Bourse : cours, indicateurs, actualités et conversion en CHF, via Yahoo Finance.

Tous les calculs (gains, moyennes mobiles, RSI…) sont faits ici en Python, de façon exacte.
Les agents IA ne font que lire ces chiffres et les expliquer : ils n'inventent rien.

Politesse envers Yahoo : au maximum une requête par seconde, et un cache de quelques minutes.
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("Europe/Zurich")
DUREE_CACHE_COURS = 10 * 60      # secondes
DUREE_CACHE_ACTUS = 30 * 60

# Paire de change Yahoo pour convertir chaque devise en francs suisses.
PAIRES_CHF = {"USD": "USDCHF=X", "EUR": "EURCHF=X", "GBP": "GBPCHF=X", "GBp": "GBPCHF=X"}


# ---------------------------------------------------------------- Sources de données

class Source(Protocol):
    def historique(self, ticker: str) -> list[tuple[str, float]]:
        """Cours de clôture quotidiens sur un an : [(date ISO, prix), …], du plus ancien au plus récent.
        La dernière valeur est le cours actuel pendant la séance."""

    def actus(self, ticker: str) -> list[dict]:
        """Dernières actualités : [{titre, resume, source, date, lien}, …]."""


class SourceYahoo:
    """Yahoo Finance (bibliothèque yfinance), limité à une requête par seconde."""

    def __init__(self, intervalle: float = 1.0) -> None:
        self.intervalle = intervalle
        self._verrou = threading.Lock()
        self._derniere = 0.0

    def _patienter(self) -> None:
        with self._verrou:
            attente = self._derniere + self.intervalle - time.monotonic()
            if attente > 0:
                time.sleep(attente)
            self._derniere = time.monotonic()

    def historique(self, ticker: str) -> list[tuple[str, float]]:
        import yfinance as yf

        self._patienter()
        h = yf.Ticker(ticker).history(period="1y", interval="1d", auto_adjust=False)
        if h is None or h.empty:
            return []
        return [(idx.date().isoformat(), float(v)) for idx, v in h["Close"].dropna().items()]

    def actus(self, ticker: str) -> list[dict]:
        import yfinance as yf

        self._patienter()
        resultat = []
        for item in yf.Ticker(ticker).news or []:
            c = item.get("content", item)
            titre = c.get("title")
            if not titre:
                continue
            fournisseur = c.get("provider") or {}
            lien = (c.get("canonicalUrl") or c.get("clickThroughUrl") or {}) or {}
            resultat.append(
                {
                    "titre": titre,
                    "resume": (c.get("summary") or "")[:400],
                    "source": fournisseur.get("displayName", "") if isinstance(fournisseur, dict) else "",
                    "date": c.get("pubDate") or c.get("displayTime") or "",
                    "lien": lien.get("url", "") if isinstance(lien, dict) else "",
                }
            )
        return resultat


# ---------------------------------------------------------------- Calculs

def _moyenne(valeurs: list[float]) -> float | None:
    return sum(valeurs) / len(valeurs) if valeurs else None


def _perf(prix: list[float], seances: int) -> float | None:
    if len(prix) <= seances or prix[-1 - seances] == 0:
        return None
    return round((prix[-1] / prix[-1 - seances] - 1) * 100, 2)


def rsi(prix: list[float], periode: int = 14) -> float | None:
    """Indice de force relative (0-100) : >70 = suracheté, <30 = survendu. Méthode de Wilder."""
    if len(prix) <= periode:
        return None
    ecarts = [b - a for a, b in zip(prix[:-1], prix[1:])]
    hausse = sum(max(e, 0) for e in ecarts[:periode]) / periode
    baisse = sum(max(-e, 0) for e in ecarts[:periode]) / periode
    for e in ecarts[periode:]:
        hausse = (hausse * (periode - 1) + max(e, 0)) / periode
        baisse = (baisse * (periode - 1) + max(-e, 0)) / periode
    if baisse == 0:
        return 100.0
    return round(100 - 100 / (1 + hausse / baisse), 1)


def fiche_depuis_historique(ticker: str, historique: list[tuple[str, float]]) -> dict:
    """Résumé chiffré d'une action à partir de son historique quotidien."""
    if len(historique) < 2:
        return {"ticker": ticker, "disponible": False}
    prix = [p for _, p in historique]
    dernier, veille = prix[-1], prix[-2]
    un_an = prix[-252:]
    mm20, mm50, mm200 = _moyenne(prix[-20:]), _moyenne(prix[-50:]), _moyenne(prix[-200:])
    arrondi = lambda v: None if v is None else round(v, 4)
    return {
        "ticker": ticker,
        "disponible": True,
        "date": historique[-1][0],
        "prix": round(dernier, 4),
        "cloture_veille": round(veille, 4),
        "variation_jour_pct": round((dernier / veille - 1) * 100, 2) if veille else None,
        "perf_1_semaine_pct": _perf(prix, 5),
        "perf_1_mois_pct": _perf(prix, 21),
        "perf_3_mois_pct": _perf(prix, 63),
        "perf_6_mois_pct": _perf(prix, 126),
        "perf_1_an_pct": _perf(prix, len(prix) - 1) if len(prix) > 200 else None,
        "moyenne_mobile_20j": arrondi(mm20) if len(prix) >= 20 else None,
        "moyenne_mobile_50j": arrondi(mm50) if len(prix) >= 50 else None,
        "moyenne_mobile_200j": arrondi(mm200) if len(prix) >= 200 else None,
        "rsi_14j": rsi(prix),
        "plus_haut_52s": round(max(un_an), 4),
        "plus_bas_52s": round(min(un_an), 4),
        "ecart_plus_haut_52s_pct": round((dernier / max(un_an) - 1) * 100, 2),
        "20_dernieres_clotures": [round(p, 4) for p in prix[-20:]],
    }


# ---------------------------------------------------------------- Service

class ServiceBourse:
    """Point d'entrée unique pour les données de bourse (avec cache)."""

    def __init__(self, source: Source | None = None) -> None:
        self.source = source or SourceYahoo()
        self._cache_hist: dict[str, tuple[float, list[tuple[str, float]]]] = {}
        self._cache_actus: dict[str, tuple[float, list[dict]]] = {}
        self._verrous: dict[str, asyncio.Lock] = {}

    def _verrou(self, cle: str) -> asyncio.Lock:
        return self._verrous.setdefault(cle, asyncio.Lock())

    async def _historique(self, ticker: str, forcer: bool = False) -> list[tuple[str, float]]:
        async with self._verrou("h:" + ticker):
            en_cache = self._cache_hist.get(ticker)
            if en_cache and not forcer and time.monotonic() - en_cache[0] < DUREE_CACHE_COURS:
                return en_cache[1]
            try:
                hist = await asyncio.to_thread(self.source.historique, ticker)
            except Exception:
                hist = en_cache[1] if en_cache else []
            self._cache_hist[ticker] = (time.monotonic(), hist)
            return hist

    async def fiche(self, ticker: str, forcer: bool = False) -> dict:
        return fiche_depuis_historique(ticker, await self._historique(ticker, forcer))

    async def fiches(self, tickers: list[str], forcer: bool = False) -> list[dict]:
        return [await self.fiche(t, forcer) for t in tickers]  # l'un après l'autre : 1 requête/s

    async def taux_vers_chf(self, devise: str) -> float | None:
        """Combien de CHF vaut 1 unité de la devise (1 penny pour « GBp »)."""
        if devise == "CHF":
            return 1.0
        paire = PAIRES_CHF.get(devise)
        if not paire:
            return None
        hist = await self._historique(paire)
        if not hist:
            return None
        taux = hist[-1][1]
        return taux / 100 if devise == "GBp" else taux

    async def actus(self, ticker: str, nombre: int = 5) -> list[dict]:
        async with self._verrou("a:" + ticker):
            en_cache = self._cache_actus.get(ticker)
            if en_cache and time.monotonic() - en_cache[0] < DUREE_CACHE_ACTUS:
                return en_cache[1][:nombre]
            try:
                actus = await asyncio.to_thread(self.source.actus, ticker)
            except Exception:
                actus = en_cache[1] if en_cache else []
            self._cache_actus[ticker] = (time.monotonic(), actus)
            return actus[:nombre]

    async def positions(self, portefeuille: dict) -> dict:
        """Valeur et gains/pertes de chaque position, en devise d'origine et en CHF."""
        lignes = []
        total_chf = 0.0
        gain_total_chf = 0.0
        valeurs_completes = True
        gains_complets = True
        for p in portefeuille["positions"]:
            f = await self.fiche(p["ticker"])
            taux = await self.taux_vers_chf(p["devise"])
            ligne = {
                "ticker": p["ticker"],
                "nom": p["nom"],
                "devise": p["devise"],
                "prix": f.get("prix"),
                "variation_jour_pct": f.get("variation_jour_pct"),
                "date_cours": f.get("date"),
                "quantite": p["quantite"],
                "prix_achat": p["prix_achat"],
                "taux_vers_chf": None if taux is None else round(taux, 6),
                "valeur": None,
                "valeur_chf": None,
                "gain": None,
                "gain_pct": None,
                "gain_chf": None,
                "variation_jour_chf": None,
            }
            if f.get("disponible") and p["quantite"]:
                ligne["valeur"] = round(p["quantite"] * f["prix"], 2)
                if taux is not None:
                    ligne["valeur_chf"] = round(ligne["valeur"] * taux, 2)
                    total_chf += ligne["valeur_chf"]
                    veille = f["cloture_veille"]
                    ligne["variation_jour_chf"] = round(p["quantite"] * (f["prix"] - veille) * taux, 2)
                else:
                    valeurs_completes = False
                if p["prix_achat"]:
                    ligne["gain"] = round(p["quantite"] * (f["prix"] - p["prix_achat"]), 2)
                    ligne["gain_pct"] = round((f["prix"] / p["prix_achat"] - 1) * 100, 2)
                    if taux is not None:
                        ligne["gain_chf"] = round(ligne["gain"] * taux, 2)
                        gain_total_chf += ligne["gain_chf"]
                else:
                    gains_complets = False
            else:
                valeurs_completes = False
                gains_complets = False
            lignes.append(ligne)
        return {
            "positions": lignes,
            "valeur_totale_chf": round(total_chf, 2) if lignes else None,
            "gain_total_chf": round(gain_total_chf, 2),
            "valeurs_completes": valeurs_completes,
            "gains_complets": gains_complets,
            "note": "Gains convertis en CHF au taux de change du jour (l'effet de change depuis l'achat n'est pas compté).",
            "horodatage": datetime.now(FUSEAU).isoformat(timespec="minutes"),
        }

    async def radar(self, tickers: list[str], seuil_pct: float) -> dict:
        """Actions qui bougent fort aujourd'hui (au-delà du seuil, à la hausse ou à la baisse)."""
        fiches = await self.fiches(tickers)
        mouvements = [
            {"ticker": f["ticker"], "variation_jour_pct": f["variation_jour_pct"], "prix": f["prix"], "date": f["date"]}
            for f in fiches
            if f.get("disponible") and f.get("variation_jour_pct") is not None
        ]
        mouvements.sort(key=lambda m: abs(m["variation_jour_pct"]), reverse=True)
        return {
            "seuil_pct": seuil_pct,
            "forts_mouvements": [m for m in mouvements if abs(m["variation_jour_pct"]) >= seuil_pct],
            "tous": mouvements,
        }
