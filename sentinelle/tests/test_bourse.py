"""Tests de la Phase 2 : section Bourse (Commandant Finance + 5 agents). Sans Internet ni Claude."""

import asyncio
import json
import time

import pytest

from agents.chargeur import agents_de_section, lire_agent
from commandants.finance import CommandantFinance
from conftest import FauxCerveau, FausseSource, fabriquer_reglages
from outils.base_de_donnees import BaseDeDonnees
from outils.bourse import ServiceBourse, SourceYahoo, fiche_depuis_historique, rsi
from outils.portefeuille import Portefeuille
from planificateur import releve_bourse

# ---------------------------------------------------------------- agents


def test_cinq_agents_bourse_bien_formes():
    agents = agents_de_section("bourse", systeme="mac")
    assert sorted(a.id for a in agents) == ["analyste", "comptable", "journaliste", "radar", "trader"]
    outils_disponibles = set(CommandantFinance.outils(object.__new__(CommandantFinance)))
    for a in agents:
        assert a.section == "bourse" and a.systeme == "tous"
        assert set(a.outils) <= outils_disponibles, a.id
        assert "jamais de conseil d'achat ou de vente" in a.instructions, a.id


def test_lecture_fiche_agent(tmp_path):
    fiche = tmp_path / "test.md"
    fiche.write_text(
        "---\nnom: Test\nsection: essai\nrole: Teste.\noutils: [a, b]\nsysteme: mac   # ou windows\n---\nConsignes.",
        encoding="utf-8",
    )
    a = lire_agent(fiche)
    assert (a.id, a.outils, a.systeme, a.instructions) == ("test", ("a", "b"), "mac", "Consignes.")


# ---------------------------------------------------------------- calculs


def test_rsi():
    assert rsi([float(i) for i in range(30)]) == 100.0          # ne fait que monter
    assert rsi([float(30 - i) for i in range(30)]) == 0.0        # ne fait que baisser
    assert rsi([1.0, 2.0]) is None                               # pas assez de données


def test_fiche_action():
    f = fiche_depuis_historique("AMD", FausseSource().donnees["AMD"])
    assert f["prix"] == 359 and f["cloture_veille"] == 358
    assert f["variation_jour_pct"] == pytest.approx(0.28, abs=0.01)
    assert f["moyenne_mobile_20j"] == pytest.approx(349.5)
    assert f["plus_haut_52s"] == 359


def test_positions_et_gains_en_chf(tmp_path):
    pf = Portefeuille(tmp_path)
    donnees = pf.lire()
    donnees["positions"][0].update(quantite=10, prix_achat=300)    # AMD en USD
    donnees["positions"][2].update(quantite=1000)                  # Aston Martin en pence, sans prix d'achat
    pf.enregistrer(donnees)
    res = asyncio.run(ServiceBourse(FausseSource()).positions(pf.lire()))
    amd, etf, aml = res["positions"]
    assert amd["valeur_chf"] == pytest.approx(2872.0)          # 10 × 359 USD × 0.80
    assert amd["gain_chf"] == pytest.approx(472.0)             # 10 × (359 − 300) × 0.80
    assert amd["gain_pct"] == pytest.approx(19.67, abs=0.01)
    assert aml["valeur_chf"] == pytest.approx(358.05)          # 1000 × 34.1 p × 1.05 / 100
    assert aml["gain"] is None and etf["valeur"] is None       # données manquantes : pas de chiffre inventé
    assert res["gains_complets"] is False


def test_radar_repere_les_gros_mouvements():
    res = asyncio.run(ServiceBourse(FausseSource()).radar(["AMD", "NVDA", "INCONNU"], 4.0))
    assert [m["ticker"] for m in res["forts_mouvements"]] == ["NVDA"]


def test_cache_evite_de_redemander():
    source = FausseSource()
    service = ServiceBourse(source)
    asyncio.run(service.fiches(["AMD", "AMD"]))
    assert source.appels.count(("historique", "AMD")) == 1


def test_une_requete_par_seconde_maximum(monkeypatch):
    s = SourceYahoo(intervalle=0.2)
    debut = time.monotonic()
    for _ in range(3):
        s._patienter()
    assert time.monotonic() - debut >= 0.35   # marge : l horloge de Windows est moins précise (~15 ms)


# ---------------------------------------------------------------- portefeuille (API)


def test_portefeuille_par_defaut(client):
    pf = client.get("/api/portefeuille").json()
    assert [p["ticker"] for p in pf["positions"]] == ["AMD", "SXLK.SW", "AML.L"]
    assert all(p["quantite"] is None for p in pf["positions"])


def test_modifier_portefeuille(client):
    pf = client.get("/api/portefeuille").json()
    pf["positions"][0]["quantite"] = 5
    assert client.put("/api/portefeuille", json=pf).status_code == 200
    assert client.get("/api/portefeuille").json()["positions"][0]["quantite"] == 5
    pf["positions"][0]["quantite"] = -1
    r = client.put("/api/portefeuille", json=pf)
    assert r.status_code == 422 and "négatif" in r.json()["detail"]


def test_carte_mes_actions(client):
    res = client.get("/api/bourse/mes-actions").json()
    assert [p["prix"] for p in res["positions"]][0] == 359


# ---------------------------------------------------------------- hiérarchie complète


def test_comment_vont_mes_actions(client, cerveau, tmp_path):
    r = client.post("/api/chat", json={"message": "Comment vont mes actions ?"}).json()
    assert r["reponse"].startswith("Monsieur, Compte rendu du Commandant Finance")
    # Le commandant a choisi ses agents, ils ont travaillé, puis il a résumé.
    qui = [d.qui for d in cerveau.demandes]
    assert qui[:2] == ["grand_chef", "bourse/commandant"] and qui[-1] == "bourse/commandant"
    assert sorted(qui[2:4]) == ["bourse/comptable", "bourse/trader"]
    # Les agents utilisent le modèle le moins cher, le Grand Chef le plus puissant.
    assert {d.modele for d in cerveau.demandes if d.qui != "grand_chef"} == {"claude-haiku-5-5"}
    # Le Trader a reçu les vrais chiffres (fournis par le programme).
    trader = cerveau.par("bourse/trader")[0]
    assert '"prix": 359' in trader.prompt and "cours_portefeuille" in trader.prompt
    # Tout est noté au journal, et le coût total de la chaîne est renvoyé.
    assert r["intervenants"][-1] == "grand_chef" and len(r["intervenants"]) == 5
    assert r["cout_usd"] == pytest.approx(0.005)
    lignes = (next((tmp_path / "journal").glob("*.jsonl"))).read_text(encoding="utf-8").splitlines()
    assert len(lignes) == 5
    assert {json.loads(l)["qui"] for l in lignes} == {"grand_chef", "bourse/commandant", "bourse/trader", "bourse/comptable"}


def test_agents_en_parallele(tmp_path):
    class CerveauLent(FauxCerveau):
        async def __call__(self, d):
            if d.qui.startswith("bourse/") and not d.format_json:
                await asyncio.sleep(0.3)
            return await super().__call__(d)

    from journal import Journal, Trace

    cerveau = CerveauLent(agents_choisis=["trader", "analyste", "radar"])
    cmd = CommandantFinance(fabriquer_reglages(tmp_path), cerveau, ServiceBourse(FausseSource()), Portefeuille(tmp_path))
    debut = time.monotonic()
    asyncio.run(cmd.executer("Analyse complète", Trace(Journal(tmp_path))))
    # 3 agents de 0,3 s + résumé 0,3 s : environ 0,6 s en parallèle (1,2 s s'ils étaient l'un après l'autre)
    assert time.monotonic() - debut < 0.9


def test_choix_invalide_retombe_sur_les_agents_principaux(tmp_path):
    from journal import Journal, Trace

    cerveau = FauxCerveau(agents_choisis=["agent_qui_n_existe_pas"])
    cmd = CommandantFinance(fabriquer_reglages(tmp_path), cerveau, ServiceBourse(FausseSource()), Portefeuille(tmp_path))
    asyncio.run(cmd.executer("Point", Trace(Journal(tmp_path))))
    assert len([d for d in cerveau.demandes if d.qui not in ("bourse/commandant",)]) == 3


# ---------------------------------------------------------------- tâche automatique


def test_releve_et_alerte_une_seule_fois(tmp_path):
    envoyees = []
    service = ServiceBourse(FausseSource())
    pf, base = Portefeuille(tmp_path), BaseDeDonnees(tmp_path)
    notifier = lambda titre, msg: envoyees.append(msg) or True
    asyncio.run(releve_bourse(service, pf, base, notifier))
    asyncio.run(releve_bourse(service, pf, base, notifier))
    assert envoyees == ["NVDA monte de 10.0 % aujourd'hui (cours : 110)."]
    assert base.derniers_cours("AMD")[0]["prix"] == 359
