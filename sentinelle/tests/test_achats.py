"""Tests de la Phase 3 : Prix & Achats (Galaxus). Aucune connexion à Galaxus : faux lecteur."""

import asyncio

import pytest

from agents.chargeur import agents_de_section
from commandants.achats import CommandantAchats
from conftest import FauxGalaxus
from outils.base_de_donnees import BaseDeDonnees
from outils.galaxus import ErreurGalaxus, extraire_fiche, valider_lien
from outils.suivi_prix import SuiviPrix

LIEN = "https://www.galaxus.ch/fr/s1/product/sapphire-pulse-radeon-rx-9070-xt-16-go-carte-graphique-54429498"

# ---------------------------------------------------------------- lecture d'une page Galaxus


def page(jsonld):
    return f'<html><head><script type="application/ld+json">{jsonld}</script></head><body>…</body></html>'


def test_lien_galaxus_valide():
    lien, ident = valider_lien(LIEN + "?utm_source=x#avis")
    assert ident == "54429498"
    assert lien == LIEN


@pytest.mark.parametrize(
    "mauvais",
    [
        "https://www.digitec.ch/fr/s1/product/truc-123456",
        "https://www.galaxus.ch/fr/search?q=gpu",
        "https://galaxus.ch.pirate.com/fr/s1/product/x-123456",
        "javascript:alert(1)",
        "pas un lien",
    ],
)
def test_lien_refuse(mauvais):
    with pytest.raises(ErreurGalaxus):
        valider_lien(mauvais)


def test_prix_dans_jsonld():
    f = extraire_fiche(page('{"@context":"https://schema.org","@type":"Product","name":"Sapphire Pulse RX 9070 XT",'
                            '"offers":{"@type":"Offer","price":"649.00","priceCurrency":"CHF",'
                            '"availability":"https://schema.org/InStock"}}'))
    assert (f.nom, f.prix, f.disponible) == ("Sapphire Pulse RX 9070 XT", 649.0, True)


def test_prix_dans_graph_et_liste_d_offres():
    f = extraire_fiche(page('{"@graph":[{"@type":"BreadcrumbList"},{"@type":["Product"],"name":"Écran &amp; support",'
                            '"offers":[{"price":12.5,"priceCurrency":"EUR"},{"lowPrice":"1\'299.90","priceCurrency":"CHF"}]}]}'))
    assert (f.nom, f.prix) == ("Écran & support", 1299.9)


def test_page_sans_prix():
    with pytest.raises(ErreurGalaxus) as e:
        extraire_fiche("<html><body>Access Denied</body></html>")
    assert e.value.raison == "prix_absent"


# ---------------------------------------------------------------- suivi des prix


def suivi(tmp_path, lecteur=None):
    return SuiviPrix(BaseDeDonnees(tmp_path), lecteur or FauxGalaxus())


def test_ajouter_et_courbe(tmp_path):
    lecteur = FauxGalaxus()
    lecteur.prix["54429498"] = [699.0, 649.0, 629.0]
    s = suivi(tmp_path, lecteur)
    f = asyncio.run(s.ajouter(LIEN))
    assert (f["nom"], f["prix"], f["nb_releves"]) == ("Produit 54429498", 699.0, 1)
    with pytest.raises(ErreurGalaxus):
        asyncio.run(s.ajouter(LIEN))                                   # déjà suivi
    for _ in range(2):
        asyncio.run(s.relever(f["id"]))
    f = s.fiche(f["id"])
    assert [h["prix"] for h in f["historique"]] == [699.0, 649.0, 629.0]
    assert (f["prix_min"], f["prix_max"], f["variation"]) == (629.0, 699.0, -20.0)


def test_galaxus_refuse_puis_saisie_manuelle(tmp_path):
    lecteur = FauxGalaxus()
    lecteur.refuse = True
    s = suivi(tmp_path, lecteur)
    f = asyncio.run(s.ajouter(LIEN, nom="Carte graphique"))
    assert f["statut"] == "refuse" and f["prix"] is None and f["nom"] == "Carte graphique"
    s.saisir(f["id"], 649.0)
    s.saisir(f["id"], 599.0)
    f = s.fiche(f["id"])
    assert [h["source"] for h in f["historique"]] == ["manuel", "manuel"] and f["prix"] == 599.0


def test_alerte_de_baisse_une_seule_fois(tmp_path):
    lecteur = FauxGalaxus()
    lecteur.prix["54429498"] = [699.0, 599.0]
    s = suivi(tmp_path, lecteur)
    ident = asyncio.run(s.ajouter(LIEN))["id"]
    envoyees = []
    notifier = lambda titre, msg: envoyees.append(msg) or True
    assert asyncio.run(s.relever_tous(notifier)) and len(envoyees) == 1
    assert "599.00 CHF au lieu de 699.00 CHF" in envoyees[0] and "Plus bas prix jamais vu" in envoyees[0]
    asyncio.run(s.relever_tous(notifier))                            # même prix : pas de nouvelle alerte
    assert len(envoyees) == 1
    assert s.fiche(ident)["prix"] == 599.0


def test_nouvelle_alerte_si_le_prix_baisse_encore(tmp_path):
    lecteur = FauxGalaxus()
    lecteur.prix["54429498"] = [699.0, 649.0, 649.0, 599.0]
    s = suivi(tmp_path, lecteur)
    ident = asyncio.run(s.ajouter(LIEN))["id"]
    envoyees = []
    for _ in range(3):
        asyncio.run(s.relever_tous(lambda t, m: envoyees.append(m)))
    assert len(envoyees) == 2 and "599.00 CHF" in envoyees[1]
    s.supprimer(ident)
    assert [a for a in s.base.dernieres_alertes(20) if a["cle"].startswith("prix:")] == []


def test_pas_d_alerte_si_le_prix_monte(tmp_path):
    lecteur = FauxGalaxus()
    lecteur.prix["54429498"] = [599.0, 699.0]
    s = suivi(tmp_path, lecteur)
    asyncio.run(s.ajouter(LIEN))
    envoyees = []
    asyncio.run(s.relever_tous(lambda t, m: envoyees.append(m)))
    assert envoyees == []


# ---------------------------------------------------------------- API et sécurité


def test_api_produits(client, galaxus):
    galaxus.prix["54429498"] = [699.0, 649.0]
    r = client.post("/api/produits", json={"url": LIEN})
    assert r.status_code == 201
    ident = r.json()["id"]
    assert client.post("/api/produits", json={"url": "https://www.digitec.ch/fr/s1/product/x-123456"}).status_code == 422
    r = client.post(f"/api/produits/{ident}/relever").json()
    assert r["prix"] == 649.0 and "649.00 CHF au lieu de 699.00 CHF" in r["alerte"]
    r = client.post(f"/api/produits/{ident}/prix", json={"prix": 619.0}).json()
    assert r["prix"] == 619.0
    assert [p["prix"] for p in client.get("/api/produits").json()] == [619.0]


def test_suppression_exige_le_bouton_confirmer(client):
    ident = client.post("/api/produits", json={"url": LIEN}).json()["id"]
    assert client.delete(f"/api/produits/{ident}").status_code == 409
    assert len(client.get("/api/produits").json()) == 1
    assert client.delete(f"/api/produits/{ident}", params={"confirmer": True}).status_code == 200
    assert client.get("/api/produits").json() == []


def test_ouvrir_seulement_les_produits_suivis(client):
    assert client.post("/api/produits/999/ouvrir").status_code == 404


# ---------------------------------------------------------------- agents et hiérarchie


def test_agents_achats():
    agents = agents_de_section("achats", systeme="mac")
    assert sorted(a.id for a in agents) == ["alarme", "black_friday", "chasseur", "comparateur", "historien"]
    outils = set(CommandantAchats.outils(object.__new__(CommandantAchats))) | {"recherche_web"}
    for a in agents:
        assert set(a.outils) <= outils, a.id
        assert "n'achètes" in a.instructions.lower(), a.id


def test_le_grand_chef_peut_consulter_le_commandant_achats(client, cerveau):
    client.post("/api/chat", json={"message": "Bonjour"})
    consigne = cerveau.par("grand_chef")[0].systeme
    assert "Commandant Achats) : EN SERVICE" in consigne
    outil = cerveau.par("grand_chef")[0].outils[0]
    assert "achats" in outil.input_schema["properties"]["missions"]["items"]["properties"]["commandant"]["enum"]
