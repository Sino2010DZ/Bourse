"""Outils communs aux tests : faux cerveau (pas d'appel payant) et fausse bourse (pas d'Internet)."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from cerveau import Reponse  # noqa: E402
from config import Reglages  # noqa: E402


def fabriquer_reglages(dossier, cle="sk-ant-test-0123456789abcdef"):
    return Reglages(
        cle_api=cle,
        modele_grand_chef="claude-opus-5-5",
        modele_agents="claude-haiku-5-5",
        effort_grand_chef="low",
        port=8765,
        dossier_donnees=dossier,
    )


class FauxCerveau:
    """Remplace Claude. Note chaque demande reçue.

    - Grand Chef : si on lui donne l'outil des commandants et que le message parle de bourse,
      il l'appelle (comme le ferait Claude), puis renvoie « Monsieur, » + les comptes rendus.
    - Commandant (choix des agents) : renvoie la liste `agents_choisis`.
    - Agents et résumés : renvoient « rapport de <qui> ».
    """

    def __init__(self, agents_choisis=("trader", "comptable")):
        self.demandes = []
        self.agents_choisis = list(agents_choisis)

    def par(self, qui):
        return [d for d in self.demandes if d.qui == qui]

    async def __call__(self, d):
        self.demandes.append(d)
        r = lambda texte, **kw: Reponse(texte, d.modele, duree_ms=10, tokens_entree=100, tokens_sortie=20, cout_usd=0.001, **kw)
        if d.qui == "grand_chef":
            if d.outils and ("action" in d.prompt or "bourse" in d.prompt):
                res = await d.outils[0].handler({"missions": [{"commandant": "bourse", "mission": "Point sur les actions"}]})
                return r("Monsieur, " + res["content"][0]["text"])
            return r("Bonjour Monsieur.")
        if d.format_json:
            return r("", donnees={"agents": self.agents_choisis})
        return r(f"rapport de {d.qui}")


def historique_regulier(depart, pas, jours=260):
    """Faux historique : un prix qui monte de `pas` chaque jour ouvrable."""
    debut = date(2025, 11, 14)
    return [((debut + timedelta(days=i)).isoformat(), round(depart + i * pas, 4)) for i in range(jours)]


class FausseSource:
    def __init__(self):
        self.appels = []
        self.donnees = {
            "AMD": historique_regulier(100, 1),            # dernier 359, veille 358
            "SXLK.SW": historique_regulier(150, 0.1),
            "AML.L": historique_regulier(60, -0.1),        # baisse
            "USDCHF=X": [("2026-11-13", 0.80), ("2026-11-14", 0.80)],
            "GBPCHF=X": [("2026-11-13", 1.05), ("2026-11-14", 1.05)],
            "NVDA": [("2026-11-13", 100.0), ("2026-11-14", 110.0)],   # +10 %
        }

    def historique(self, ticker):
        self.appels.append(("historique", ticker))
        return self.donnees.get(ticker, [])

    def actus(self, ticker):
        self.appels.append(("actus", ticker))
        return [{"titre": f"News {ticker}", "resume": "", "source": "Test", "date": "2026-11-14", "lien": ""}]


class FauxGalaxus:
    """Remplace Galaxus : chaque produit a une liste de prix successifs ; « refuse » simule un blocage."""

    def __init__(self):
        self.prix = {}          # numéro produit -> liste de prix (le dernier est réutilisé)
        self.refuse = False
        self.appels = []

    def lire(self, url):
        from outils.galaxus import ErreurGalaxus, FicheProduit, valider_lien

        _, ident = valider_lien(url)
        self.appels.append(ident)
        if self.refuse:
            raise ErreurGalaxus("refuse", "Galaxus refuse la lecture automatique : saisissez le prix à la main.")
        serie = self.prix.setdefault(ident, [499.0])
        prix = serie.pop(0) if len(serie) > 1 else serie[0]
        return FicheProduit(nom=f"Produit {ident}", prix=prix, disponible=True)


METEO_BRUTE = {
    "current": {"time": "2026-11-16T18:15", "temperature_2m": 11.9, "apparent_temperature": 9.8, "weather_code": 61,
                "wind_speed_10m": 9.7, "precipitation": 0.4},
    "daily": {"time": ["2026-11-16", "2026-11-17"], "weather_code": [80, 3], "temperature_2m_max": [13.5, 9.0],
              "temperature_2m_min": [10.5, 4.2], "precipitation_probability_max": [93, 20],
              "sunrise": ["2026-11-16T07:37", "2026-11-17T07:38"], "sunset": ["2026-11-16T17:02", "2026-11-17T17:01"]},
}


def calendrier_f1(dates_courses=("2026-11-22", "2026-12-06")):
    courses = []
    for i, date in enumerate(dates_courses, start=21):
        courses.append({
            "round": str(i), "raceName": f"Grand Prix {i}", "date": date, "time": "13:00:00Z",
            "Circuit": {"circuitName": f"Circuit {i}", "Location": {"locality": "Ville", "country": "Pays"}},
            "Qualifying": {"date": date[:-2] + f"{int(date[-2:]) - 1:02d}", "time": "14:00:00Z"},
        })
    return {"MRData": {"RaceTable": {"Races": courses}}}


def lecteur_f1(url):
    if url.endswith("current.json"):
        return calendrier_f1()
    if "results" in url:
        return {"MRData": {"RaceTable": {"Races": [{"raceName": "Brazilian Grand Prix", "date": "2026-11-08", "Results": [
            {"position": "1", "Driver": {"givenName": "Lando", "familyName": "Norris"}, "Constructor": {"name": "McLaren"},
             "points": "25", "status": "Finished"}]}]}}}
    if "driverstandings" in url:
        return {"MRData": {"StandingsTable": {"StandingsLists": [{"DriverStandings": [
            {"position": "1", "Driver": {"givenName": "Andrea Kimi", "familyName": "Antonelli"},
             "Constructors": [{"name": "Mercedes"}], "points": "390", "wins": "9"}]}]}}}
    return {"MRData": {"StandingsTable": {"StandingsLists": [{"ConstructorStandings": [
        {"position": "1", "Constructor": {"name": "Mercedes"}, "points": "600", "wins": "11"}]}]}}}


@pytest.fixture
def galaxus():
    return FauxGalaxus()


@pytest.fixture
def cerveau():
    return FauxCerveau()


@pytest.fixture
def source():
    return FausseSource()


@pytest.fixture
def client(tmp_path, cerveau, source, galaxus):
    from fastapi.testclient import TestClient

    from main import creer_app

    from outils.f1 import ServiceF1
    from outils.meteo import ServiceMeteo

    return TestClient(creer_app(
        fabriquer_reglages(tmp_path), cerveau, source, planificateur=False, lecteur_galaxus=galaxus,
        meteo=ServiceMeteo(lambda url: METEO_BRUTE), f1=ServiceF1(lecteur_f1),
    ))


def _intraday(self, ticker, periode):
    self.appels.append(("intraday", ticker))
    base = self.donnees.get(ticker, [("", 100.0)])[-1][1]
    return [(f"2026-11-13T{15 + i // 12:02d}:{(i % 12) * 5:02d}", base + i * 0.1) for i in range(20)]


FausseSource.intraday = _intraday
