"""Tests des corrections de la relecture : CSRF, bac à sable de Claude Code, chantiers interrompus, etc."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import METEO_BRUTE, fabriquer_reglages, lecteur_f1
from outils.base_de_donnees import BaseDeDonnees
from outils.claude_code import Chantier, executer_chantier


def application(dossier, **kw):
    from main import creer_app
    from outils.f1 import ServiceF1
    from outils.meteo import ServiceMeteo
    from conftest import FauxCerveau

    return creer_app(fabriquer_reglages(dossier), kw.pop("cerveau", FauxCerveau()), planificateur=False,
                     meteo=ServiceMeteo(lambda u: METEO_BRUTE), f1=ServiceF1(lecteur_f1), **kw)


# ---------------------------------------------------------------- CSRF


@pytest.mark.parametrize("origine,attendu", [
    ("https://site-malveillant.com", 403), ("null", 403),
    ("tauri://localhost", 404), ("http://tauri.localhost", 404), (None, 404),
])
def test_un_autre_site_ne_peut_rien_declencher(tmp_path, origine, attendu):
    client = TestClient(application(tmp_path))
    entetes = {"Origin": origine} if origine else {}
    assert client.post("/api/actions/1/confirmer", headers=entetes).status_code == attendu   # 404 = passé, action inconnue
    assert client.get("/api/sante", headers=entetes).status_code == 200                       # la lecture reste possible


# ---------------------------------------------------------------- bac à sable de Claude Code


@pytest.mark.parametrize("outil,entree", [
    ("Glob", {"pattern": "/Users/moi/Documents/**/*"}),
    ("Glob", {"pattern": "../../**/*.pdf"}),
    ("Grep", {"pattern": "motdepasse", "glob": "C:\\\\Users\\\\moi\\\\**"}),
    ("Glob", {"pattern": "*.txt", "path": "/etc"}),
])
def test_recherches_hors_projet_refusees(tmp_path, outil, entree):
    chantier = Chantier(tmp_path / "projet", tmp_path / "sauv")
    (tmp_path / "projet").mkdir()
    assert chantier.avant_outil(outil, entree) is not None


def test_recherches_dans_le_projet_permises(tmp_path):
    (tmp_path / "projet").mkdir()
    chantier = Chantier(tmp_path / "projet", tmp_path / "sauv")
    assert chantier.avant_outil("Glob", {"pattern": "src/**/*.py"}) is None
    assert chantier.avant_outil("Grep", {"pattern": "def ", "glob": "*.py"}) is None


def test_chantier_qui_plante_reste_annulable(tmp_path):
    projet = tmp_path / "p"
    projet.mkdir()
    (projet / "a.txt").write_text("original")

    async def requete_qui_plante(prompt, options):
        garde = options.hooks["PreToolUse"][0].hooks[0]
        await garde({"tool_name": "Edit", "tool_input": {"file_path": "a.txt"}}, None, None)
        (projet / "a.txt").write_text("modifié")
        raise ConnectionError("réseau coupé")
        yield  # pragma: no cover

    r = asyncio.run(executer_chantier(str(projet), "x" * 20, tmp_path / "sauv", "m", 1.0, requete_qui_plante))
    assert r["erreur"] and r["modifies"] == ["a.txt"] and "arrêté" in r["resume"]
    assert json.loads((tmp_path / "sauv" / "chantier.json").read_text())["modifies"] == ["a.txt"]


def test_action_interrompue_au_redemarrage_reste_annulable(tmp_path):
    base = BaseDeDonnees(tmp_path)
    ident = base.creer_action("claude_code_modifier", "chantier", {"projet": str(tmp_path / "p"), "consigne": "x"}, "2026-11-26T10:00")
    base.changer_statut_action(ident, "en_attente", "en_cours")
    sauvegarde = tmp_path / "sauvegardes" / f"action-{ident}"
    sauvegarde.mkdir(parents=True)
    (sauvegarde / "chantier.json").write_text(json.dumps({"modifies": ["a.txt"], "crees": []}))
    client = TestClient(application(tmp_path))                         # « redémarrage » de Sentinelle
    etat = client.get(f"/api/actions/{ident}").json()
    assert etat["statut"] == "echec" and "Interrompue" in etat["resultat"] and etat["annulable"] is True


# ---------------------------------------------------------------- divers


def test_reponse_non_structuree_relue(tmp_path):
    from commandants.entretien import CommandantMaintenance
    from cerveau import Reponse
    from conftest import FauxCerveau
    from journal import Journal, Trace
    from outils.preferences import Preferences
    from agents.chargeur import agents_de_section

    class CerveauTexte(FauxCerveau):
        async def __call__(self, d):
            if d.format_json and "actions" in d.format_json.get("properties", {}):
                return Reponse(json.dumps({"reponse": "Proposé.", "actions": [{"type": "changer_theme", "parametres_json": '{"mode": "clair"}'}]}),
                               d.modele, 10, donnees=None)
            return await super().__call__(d)

    cmd = CommandantMaintenance(fabriquer_reglages(tmp_path), CerveauTexte(), Preferences(tmp_path))
    agent = next(a for a in agents_de_section("entretien", systeme="windows") if a.id == "eclairagiste")
    trace = Trace(Journal(tmp_path))
    _, texte = asyncio.run(cmd.lancer_agent(agent, "Mode clair", {}, trace))
    assert trace.actions and "en attente du bouton « Confirmer »" in texte
