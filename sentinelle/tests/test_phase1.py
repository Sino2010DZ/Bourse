"""Tests de la Phase 1 : serveur local, Grand Chef, journal. Aucun appel payant à Claude."""

import json

import pytest
from fastapi.testclient import TestClient

from config import Reglages
from grand_chef import Reponse, consigne_systeme
from main import creer_app


def reglages(tmp_path, cle="sk-ant-test"):
    return Reglages(
        cle_api=cle,
        modele_grand_chef="claude-opus-5-5",
        modele_agents="claude-haiku-5-5",
        effort_grand_chef="low",
        port=8765,
        dossier_donnees=tmp_path,
    )


class FauxCerveau:
    """Remplace Claude pendant les tests : répond « Bonjour Monsieur » et note ce qu'il reçoit."""

    def __init__(self):
        self.appels = []

    async def __call__(self, systeme, prompt, modele, effort):
        self.appels.append({"systeme": systeme, "prompt": prompt, "modele": modele, "effort": effort})
        return Reponse("Bonjour Monsieur.", modele, duree_ms=12, tokens_entree=100, tokens_sortie=20, cout_usd=0.0008)


@pytest.fixture
def cerveau():
    return FauxCerveau()


@pytest.fixture
def client(tmp_path, cerveau):
    return TestClient(creer_app(reglages(tmp_path), cerveau))


def test_sante(client):
    r = client.get("/api/sante")
    assert r.status_code == 200
    assert r.json()["statut"] == "en_ligne"
    assert r.json()["cle_api"] is True


def test_dix_sections(client):
    sections = client.get("/api/sections").json()
    assert len(sections) == 10
    assert {s["statut"] for s in sections} <= {"active", "en_preparation", "a_construire"}


def test_grand_chef_repond_bonjour_monsieur(client, cerveau):
    r = client.post("/api/chat", json={"message": "Bonjour"})
    assert r.status_code == 200
    assert r.json()["reponse"] == "Bonjour Monsieur."
    appel = cerveau.appels[0]
    assert appel["modele"] == "claude-opus-5-5"
    assert "Monsieur" in appel["systeme"]


def test_le_grand_chef_se_souvient_de_la_conversation(client, cerveau):
    client.post("/api/chat", json={"message": "Je m'appelle Tony"})
    client.post("/api/chat", json={"message": "Comment je m'appelle ?"})
    assert "Je m'appelle Tony" in cerveau.appels[1]["prompt"]


def test_journal_et_consommation(client, tmp_path):
    client.post("/api/chat", json={"message": "Bonjour"})
    client.post("/api/chat", json={"message": "Merci"})
    fichiers = list((tmp_path / "journal").glob("*.jsonl"))
    assert len(fichiers) == 1
    lignes = [json.loads(l) for l in fichiers[0].read_text(encoding="utf-8").splitlines()]
    assert [l["qui"] for l in lignes] == ["grand_chef", "grand_chef"]
    assert lignes[0]["duree_ms"] == 12
    conso = client.get("/api/consommation").json()
    assert conso == {"echanges": 2, "tokens_entree": 200, "tokens_sortie": 40, "cout_usd": 0.0016}


def test_sans_cle_api_message_poli(tmp_path):
    client = TestClient(creer_app(reglages(tmp_path, cle="")))
    r = client.post("/api/chat", json={"message": "Bonjour"}).json()
    assert r["erreur"] is True
    assert "Monsieur" in r["reponse"] and ".env" in r["reponse"]


def test_message_vide_refuse(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_refuse_les_sites_exterieurs(client):
    # Protection : seul l'ordinateur lui-même peut parler au serveur.
    r = client.get("/api/sante", headers={"Host": "site-malveillant.com"})
    assert r.status_code == 400


def test_consigne_interdit_les_ordres_de_bourse():
    consigne = consigne_systeme()
    assert "N'invente jamais" in consigne
    assert "ordre d'achat ou de vente" in consigne


def test_interface_servie(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Sentinelle" in r.text
