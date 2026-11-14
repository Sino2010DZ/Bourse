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


@pytest.fixture
def cerveau():
    return FauxCerveau()


@pytest.fixture
def source():
    return FausseSource()


@pytest.fixture
def client(tmp_path, cerveau, source):
    from fastapi.testclient import TestClient

    from main import creer_app

    return TestClient(creer_app(fabriquer_reglages(tmp_path), cerveau, source, planificateur=False))
