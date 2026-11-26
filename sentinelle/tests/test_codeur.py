"""Le Codeur pilote Claude Code : seulement dans un projet choisi, après « Confirmer », avec sauvegarde et annulation.
Claude Code est simulé : le faux appelle les mêmes garde-fous (hooks) que le vrai avant chaque outil."""

import asyncio
import json
import time
from pathlib import Path

from claude_agent_sdk import ResultMessage
from fastapi.testclient import TestClient

from conftest import METEO_BRUTE, fabriquer_reglages, lecteur_f1
from outils.claude_code import OUTILS, executer_chantier, restaurer
from test_actions import CerveauActions


def faux_claude_code(actions):
    """Simule Claude Code : pour chaque (outil, chemin, contenu), demande la permission au hook, puis agit."""

    async def requete(prompt, options):
        assert options.tools == OUTILS and options.permission_mode == "acceptEdits" and options.setting_sources == []
        garde = options.hooks["PreToolUse"][0].hooks[0]
        for outil, chemin, contenu in actions:
            decision = await garde({"tool_name": outil, "tool_input": {"file_path": chemin}}, None, None)
            if decision.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
                continue
            cible = Path(chemin) if Path(chemin).is_absolute() else Path(options.cwd) / chemin
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_text(contenu, encoding="utf-8")
        yield ResultMessage(subtype="success", duration_ms=10, duration_api_ms=10, is_error=False, num_turns=3,
                            session_id="s", total_cost_usd=0.12, result="J'ai ajouté le titre et une page.")

    return requete


def test_chantier_sauvegarde_puis_annulation(tmp_path):
    projet = tmp_path / "MonSite"
    projet.mkdir()
    (projet / "index.html").write_text("<h1>Ancien</h1>", encoding="utf-8")
    secret = tmp_path / "secret.txt"
    secret.write_text("ne pas toucher")
    sauvegarde = tmp_path / "sauvegardes" / "a1"
    r = asyncio.run(executer_chantier(str(projet), "Change le titre", sauvegarde, "modele", 1.0, faux_claude_code([
        ("Edit", str(projet / "index.html"), "<h1>Nouveau</h1>"),
        ("Write", "pages/contact.html", "<p>Contact</p>"),
        ("Write", str(secret), "piraté"),                 # hors du projet : refusé
        ("Edit", "../secret.txt", "piraté"),              # remontée de dossier : refusée
    ])))
    assert r["modifies"] == ["index.html"] and r["crees"] == ["pages/contact.html"] and len(r["refus"]) == 2
    assert secret.read_text() == "ne pas toucher"
    assert (sauvegarde / "index.html").read_text(encoding="utf-8") == "<h1>Ancien</h1>"
    texte = restaurer(str(projet), sauvegarde, r["modifies"], r["crees"])
    assert "1 fichiers remis" in texte and "1 fichiers créés retirés" in texte
    assert (projet / "index.html").read_text(encoding="utf-8") == "<h1>Ancien</h1>" and not (projet / "pages/contact.html").exists()


def test_codeur_propose_confirmer_puis_annuler(tmp_path):
    projet = tmp_path / "Projet"
    projet.mkdir()
    (projet / "app.py").write_text("print('v1')\n", encoding="utf-8")
    cerveau = CerveauActions({"type": "claude_code_modifier", "parametres_json": json.dumps(
        {"projet": str(projet), "consigne": "Affiche v2 au lieu de v1 dans app.py"})}, agents_choisis=["codeur"])
    cerveau.section = "creation"
    from main import creer_app
    from outils.f1 import ServiceF1
    from outils.meteo import ServiceMeteo

    app = creer_app(fabriquer_reglages(tmp_path / "donnees"), cerveau, planificateur=False,
                    meteo=ServiceMeteo(lambda u: METEO_BRUTE), f1=ServiceF1(lecteur_f1),
                    requete_claude_code=faux_claude_code([("Edit", "app.py", "print('v2')\n")]))
    with TestClient(app) as client:
        # Sans projet choisi dans les Réglages, l'action est refusée par le programme.
        r = client.post("/api/chat", json={"message": "Modifie mon projet"}).json()
        assert r["actions"] == [] and "Action non préparée" in r["reponse"]

        client.put("/api/preferences", json={**client.get("/api/preferences").json(), "dossiers_projets": [str(projet)]})
        r = client.post("/api/chat", json={"message": "Modifie mon projet"}).json()
        action = r["actions"][0]
        assert "laisser Claude Code modifier le projet « Projet »" in action["description"]
        assert (projet / "app.py").read_text() == "print('v1')\n"              # rien avant « Confirmer »

        etat = client.post(f"/api/actions/{action['id']}/confirmer").json()
        for _ in range(100):
            if etat["statut"] != "en_cours":
                break
            time.sleep(0.05)
            etat = client.get(f"/api/actions/{action['id']}").json()
        assert etat["statut"] == "faite" and etat["annulable"] and "app.py" in etat["resultat"]
        assert (projet / "app.py").read_text() == "print('v2')\n"

        assert client.post(f"/api/actions/{action['id']}/restaurer").status_code == 409   # Confirmer obligatoire
        etat = client.post(f"/api/actions/{action['id']}/restaurer", params={"confirmer": True}).json()
        assert etat["statut"] == "annulee" and (projet / "app.py").read_text() == "print('v1')\n"
