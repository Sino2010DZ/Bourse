"""Tests de la Phase 1 : serveur local, Grand Chef, journal. Aucun appel payant à Claude."""

import json

from conftest import fabriquer_reglages
from fastapi.testclient import TestClient
from grand_chef import consigne_systeme
from main import creer_app


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
    demande = cerveau.par("grand_chef")[0]
    assert demande.modele == "claude-opus-5-5"
    assert "Monsieur" in demande.systeme


def test_le_grand_chef_se_souvient_de_la_conversation(client, cerveau):
    d = client.post("/api/chat", json={"message": "Je m'appelle Tony"}).json()["discussion_id"]
    client.post("/api/chat", json={"message": "Comment je m'appelle ?", "discussion_id": d})
    assert "Je m'appelle Tony" in cerveau.par("grand_chef")[1].prompt


def test_journal_et_consommation(client, tmp_path):
    client.post("/api/chat", json={"message": "Bonjour"})
    client.post("/api/chat", json={"message": "Merci"})
    fichiers = list((tmp_path / "journal").glob("*.jsonl"))
    assert len(fichiers) == 1
    lignes = [json.loads(l) for l in fichiers[0].read_text(encoding="utf-8").splitlines()]
    assert [l["qui"] for l in lignes] == ["grand_chef", "grand_chef"]
    conso = client.get("/api/consommation").json()
    assert conso == {"echanges": 2, "tokens_entree": 200, "tokens_sortie": 40, "cout_usd": 0.002, "budget_jour_usd": 1.0}


def test_sans_cle_api_message_poli(tmp_path):
    client = TestClient(creer_app(fabriquer_reglages(tmp_path, cle=""), planificateur=False))
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
    consigne = consigne_systeme({})
    assert "N'invente jamais" in consigne
    assert "Ne recommande jamais d'acheter ou de vendre" in consigne


def test_interface_servie(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Sentinelle" in r.text


def test_coller_la_cle_dans_l_app(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = TestClient(creer_app(fabriquer_reglages(tmp_path, cle=""), planificateur=False))
    assert client.get("/api/sante").json()["cle_api"] is False
    assert client.post("/api/cle", json={"cle": "pas-une-cle"}).status_code == 422
    cle = "sk-ant-api03-" + "x" * 40
    assert client.post("/api/cle", json={"cle": cle}).json() == {"cle_api": True}
    assert client.get("/api/sante").json()["cle_api"] is True
    fichier = tmp_path / ".env"
    assert fichier.read_text(encoding="utf-8").strip() == f"ANTHROPIC_API_KEY={cle}"
    assert oct(fichier.stat().st_mode & 0o777) == "0o600"
