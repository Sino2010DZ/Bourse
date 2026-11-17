"""Tests des sections construites ensuite : Renseignement, Matériel, Sport, Organisation, Divertissement,
Jeux vidéo, Entretien, Création. Sans Internet ni Claude (faux cerveau, fausses données)."""

import asyncio
import os
from datetime import datetime
from pathlib import Path

import pytest

from agents.chargeur import agents_de_section
from commandants.base import OUTILS_INTEGRES
from conftest import METEO_BRUTE, FauxCerveau, calendrier_f1, fabriquer_reglages, lecteur_f1
from journal import FUSEAU, Journal, Trace
from outils.base_de_donnees import BaseDeDonnees
from outils.f1 import ServiceF1, prochaine_course
from outils.meteo import mettre_en_forme
from outils.ordinateur import dans_dossiers_autorises, inventaire_dossiers, jeux_steam, taille_dossier
from outils.preferences import ErreurPreferences, valider
from sections import AGENTS, SECTIONS

SECTIONS_IDS = [s["id"] for s in SECTIONS]


# ---------------------------------------------------------------- les 50 agents


@pytest.mark.parametrize("systeme", ["mac", "windows"])
def test_cinquante_agents_par_systeme(systeme):
    total = {s: {a.id for a in agents_de_section(s, systeme=systeme)} for s in SECTIONS_IDS}
    assert sum(len(v) for v in total.values()) == 50
    for section, ids in total.items():
        assert ids <= {i for i, _ in AGENTS[section]}, section          # pas d'agent inconnu
    absents = {n for s in SECTIONS_IDS for i, n in AGENTS[s] if i not in total[s]}
    assert absents == set()                                                 # les 50 agents sont en service


def test_chaque_agent_a_ses_outils_et_ses_regles(tmp_path):
    from main import creer_app
    import grand_chef

    capture = {}
    original = grand_chef.GrandChef.__init__

    def espion(self, reglages, journal, cerveau=None, commandants=None):
        capture.update(commandants or {})
        original(self, reglages, journal, cerveau, commandants)

    grand_chef.GrandChef.__init__ = espion
    try:
        creer_app(fabriquer_reglages(tmp_path), FauxCerveau(), planificateur=False)
    finally:
        grand_chef.GrandChef.__init__ = original
    assert sorted(capture) == sorted(SECTIONS_IDS)
    for section, commandant in capture.items():
        outils = set(commandant.outils()) | set(OUTILS_INTEGRES)
        for systeme in ("mac", "windows"):
            for a in agents_de_section(section, systeme=systeme):
                assert set(a.outils) <= outils, (section, a.id, set(a.outils) - outils)
                assert "N'invente" in a.instructions or "Utilise uniquement" in a.instructions, (section, a.id)


def test_versions_mac_et_windows():
    mac = {a.id: a for a in agents_de_section("entretien", systeme="mac")}
    win = {a.id: a for a in agents_de_section("entretien", systeme="windows")}
    assert set(mac) == set(win) == {"rangeur", "nettoyeur", "sauvegarde", "thermometre", "eclairagiste"}
    assert "Time Machine" in mac["sauvegarde"].role and "OneDrive" in win["sauvegarde"].role
    for a in list(mac.values()) + list(win.values()):
        assert "ne supprimes aucun fichier" in a.instructions


# ---------------------------------------------------------------- recherche web et archives


def test_agent_web_recoit_la_recherche_et_les_regles(tmp_path):
    from commandants.renseignement import CommandantVeille

    cerveau = FauxCerveau(agents_choisis=["eclaireur", "traducteur"])
    base = BaseDeDonnees(tmp_path)
    cmd = CommandantVeille(fabriquer_reglages(tmp_path), cerveau, base)
    asyncio.run(cmd.executer("Que s'est-il passé au CERN cette semaine ?", Trace(Journal(tmp_path))))
    eclaireur = cerveau.par("renseignement/eclaireur")[0]
    assert eclaireur.outils_integres == ["WebSearch", "WebFetch"] and eclaireur.tours_max > 1
    assert "Cite tes sources" in eclaireur.systeme and "ne te connecte à aucun compte" in eclaireur.systeme
    traducteur = cerveau.par("renseignement/traducteur")[0]
    assert traducteur.outils_integres == [] and "Données fournies" not in traducteur.prompt
    assert base.archives()[0]["sujet"].startswith("Que s'est-il passé au CERN")


# ---------------------------------------------------------------- météo et F1


def test_meteo_mise_en_forme():
    m = mettre_en_forme(METEO_BRUTE)
    assert (m["temperature"], m["temps"], m["icone"]) == (11.9, "Pluie faible", "🌦️")
    assert m["jours"][1] == {**m["jours"][1], "temps": "Couvert", "min": 4.2, "max": 9.0}


def test_prochaine_course_a_l_heure_de_zurich():
    c = prochaine_course(calendrier_f1(), maintenant=datetime(2026, 11, 16, tzinfo=FUSEAU))
    assert c["nom"] == "Grand Prix 21" and c["depart"] == "2026-11-22T14:00:00+01:00"
    assert [s["nom"] for s in c["seances"]] == ["Qualifications", "Course"]
    assert prochaine_course(calendrier_f1(), maintenant=datetime(2026, 12, 31, tzinfo=FUSEAU)) is None


def test_api_meteo_et_f1(client):
    assert client.get("/api/meteo").json()["temperature"] == 11.9
    assert client.get("/api/f1/prochaine").json()["circuit"].startswith("Circuit")


def test_coup_d_envoi_une_seule_fois(tmp_path):
    from planificateur import coup_d_envoi

    base, envoyees = BaseDeDonnees(tmp_path), []
    f1 = ServiceF1(lecteur_f1)
    avant_qualif = datetime(2026, 11, 21, 14, 10, tzinfo=FUSEAU)        # qualifs à 15:00 (Zurich)
    for _ in range(2):
        asyncio.run(coup_d_envoi(f1, base, lambda t, m: envoyees.append(m), maintenant=avant_qualif))
    assert envoyees == ["Qualifications du Grand Prix 21 dans 50 min (15:00, heure de Zurich)."]


def test_briefing_du_matin(tmp_path):
    from commandants.organisation import CommandantSecretariat
    from conftest import FausseSource
    from outils.bourse import ServiceBourse
    from outils.meteo import ServiceMeteo
    from outils.portefeuille import Portefeuille
    from outils.suivi_prix import SuiviPrix
    from planificateur import briefing_du_matin

    base, cerveau, notifs = BaseDeDonnees(tmp_path), FauxCerveau(), []
    secretariat = CommandantSecretariat(
        fabriquer_reglages(tmp_path), cerveau, ServiceMeteo(lambda u: METEO_BRUTE), ServiceBourse(FausseSource()),
        Portefeuille(tmp_path), SuiviPrix(base), ServiceF1(lecteur_f1),
    )
    texte = asyncio.run(briefing_du_matin(secretariat, base, Journal(tmp_path), lambda t, m: notifs.append(t)))
    assert texte == "rapport de organisation/briefing" and notifs == ["Sentinelle — Briefing du matin"]
    demande = cerveau.par("organisation/briefing")[0]
    assert "meteo_geneve" in demande.prompt and "resume_bourse" in demande.prompt and '"temperature": 11.9' in demande.prompt
    assert base.discussions()[0]["titre"].startswith("Briefing du ")


# ---------------------------------------------------------------- ordinateur (lecture seule)


def test_dossiers_autorises_seulement(tmp_path):
    choisi = tmp_path / "Telechargements"
    choisi.mkdir()
    (choisi / "facture.pdf").write_bytes(b"x" * 2048)
    (tmp_path / "secret.txt").write_text("privé")
    inv = inventaire_dossiers([str(choisi)])
    assert [e["nom"] for e in inv["dossiers"][0]["elements"]] == ["facture.pdf"]
    assert dans_dossiers_autorises(choisi / "facture.pdf", [str(choisi)])
    assert not dans_dossiers_autorises(choisi / ".." / "secret.txt", [str(choisi)])
    assert "Aucun dossier choisi" in inventaire_dossiers([])["info"]


@pytest.mark.parametrize("mauvais", ["/", "~", "C:\\", "C:/"])
def test_dossiers_trop_larges_refuses(mauvais):
    with pytest.raises(ErreurPreferences):
        valider({"dossiers_autorises": [mauvais]})


def test_taille_et_jeux_steam(tmp_path):
    steamapps = tmp_path / "steamapps"
    steamapps.mkdir()
    (steamapps / "appmanifest_1551360.acf").write_text(
        '"AppState"\n{\n\t"appid"\t\t"1551360"\n\t"name"\t\t"Forza Horizon 5"\n\t"SizeOnDisk"\t\t"161061273600"\n'
        '\t"LastUpdated"\t\t"1763000000"\n}\n', encoding="utf-8")
    jeux = jeux_steam([steamapps])
    assert jeux[0]["nom"] == "Forza Horizon 5" and jeux[0]["taille_go"] == 150.0
    t = taille_dossier(steamapps)
    assert t["fichiers"] == 1 and t["existe"]


def test_infos_systeme_ne_plantent_pas():
    """Sur un système sans PowerShell ni outils Apple, les fonctions répondent sans erreur."""
    from plateforme import systeme

    s = systeme()
    for fonction in ("infos_materiel", "temperatures", "sauvegarde", "apparence", "dossiers_temporaires", "dossiers_jeux"):
        getattr(s, fonction)()
    s.batterie()
