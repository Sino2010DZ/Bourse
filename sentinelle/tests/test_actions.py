"""Actions proposées par les agents : rien ne s'exécute sans « Confirmer ». Spotify (DJ) avec un faux Spotify."""

import asyncio
import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from cerveau import Reponse
from conftest import METEO_BRUTE, FauxCerveau, fabriquer_reglages, lecteur_f1
from outils.actions_ordinateur import RefusAction, nettoyer_temporaires, ranger_fichiers, verifier_rangement
from outils.comptes import Comptes
from outils.spotify import ErreurSpotify, ServiceSpotify


class CerveauActions(FauxCerveau):
    """Le faux agent propose l'action demandée dans `proposition` (comme le ferait Claude)."""

    def __init__(self, proposition, **kw):
        super().__init__(**kw)
        self.proposition = proposition

    async def __call__(self, d):
        if d.format_json and "actions" in d.format_json.get("properties", {}):
            self.demandes.append(d)
            return Reponse("", d.modele, 10, donnees={"reponse": "Voici ma proposition.", "actions": [self.proposition]})
        if d.qui == "grand_chef" and d.outils:
            res = await d.outils[0].handler({"missions": [{"commandant": self.section, "mission": "Fais-le"}]})
            self.demandes.append(d)
            return Reponse("Monsieur, " + res["content"][0]["text"], d.modele, 10)
        return await super().__call__(d)


class FauxSpotify:
    """Imite l'API Spotify et note chaque appel."""

    def __init__(self):
        self.appels = []

    def __call__(self, methode, url, jeton=None, corps=None, formulaire=None):
        self.appels.append((methode, url.split("spotify.com")[-1].split("?")[0], corps))
        if url.endswith("/api/token"):
            return 200, {"access_token": "acces", "refresh_token": "rafraichi", "expires_in": 3600}
        if "/me/player" in url and methode == "GET" and "recently" not in url:
            return 200, {"is_playing": True, "item": {"name": "Hello", "artists": [{"name": "Adele"}], "album": {"name": "25", "images": []}}, "device": {"name": "PC"}}
        if "/search" in url:
            q = parse_qs(urlparse(url).query)["q"][0]
            if "Inexistant" in q:
                return 200, {"tracks": {"items": []}}
            return 200, {"tracks": {"items": [{"uri": f"spotify:track:{abs(hash(q)) % 1000}", "name": "Titre", "artists": [{"name": "Artiste"}]}]}}
        if url.endswith("/me/playlists") and methode == "POST":
            return 201, {"id": "pl1", "external_urls": {"spotify": "https://open.spotify.com/playlist/pl1"}}
        if "/items" in url:
            return 201, {"snapshot_id": "x"}
        if "/me/player/pause" in url:
            return 204, None
        return 200, {"items": []}


def client_avec(tmp_path, cerveau, http=None):
    from main import creer_app
    from outils.f1 import ServiceF1
    from outils.meteo import ServiceMeteo

    return TestClient(creer_app(fabriquer_reglages(tmp_path), cerveau, planificateur=False,
                                meteo=ServiceMeteo(lambda u: METEO_BRUTE), f1=ServiceF1(lecteur_f1), http_spotify=http))


# ---------------------------------------------------------------- rangement (dans les dossiers choisis seulement)


def test_ranger_deplace_sans_supprimer(tmp_path):
    dossier = tmp_path / "Telechargements"
    dossier.mkdir()
    (dossier / "facture.pdf").write_text("1")
    (dossier / "photo.jpg").write_text("2")
    (dossier / "Factures").mkdir()
    (dossier / "Factures" / "facture.pdf").write_text("déjà là")
    resultat = ranger_fichiers(str(dossier), [{"fichier": "facture.pdf", "vers": "Factures"}, {"fichier": "photo.jpg", "vers": "Photos"}], [str(dossier)])
    assert "1 fichiers rangés" in resultat and "facture.pdf" in resultat          # nom déjà pris : laissé en place
    assert (dossier / "Photos" / "photo.jpg").exists() and (dossier / "facture.pdf").exists()
    assert (dossier / "Factures" / "facture.pdf").read_text() == "déjà là"          # rien d'écrasé


@pytest.mark.parametrize("deplacement", [
    {"fichier": "../secret.txt", "vers": "X"}, {"fichier": "a.txt", "vers": "../hors"}, {"fichier": "a.txt", "vers": ".."},
])
def test_ranger_refuse_les_chemins_dangereux(tmp_path, deplacement):
    dossier = tmp_path / "D"
    dossier.mkdir()
    (dossier / "a.txt").write_text("x")
    with pytest.raises(RefusAction):
        verifier_rangement(str(dossier), [deplacement], [str(dossier)])


def test_ranger_refuse_un_dossier_non_choisi(tmp_path):
    with pytest.raises(RefusAction):
        verifier_rangement(str(tmp_path), [{"fichier": "a", "vers": "b"}], [])


def test_nettoyer_seulement_les_vieux_fichiers_temporaires(tmp_path):
    vieux, recent = tmp_path / "vieux.tmp", tmp_path / "recent.tmp"
    vieux.write_bytes(b"x" * 1024)
    recent.write_text("y")
    ancien = time.time() - 10 * 86400
    os.utime(vieux, (ancien, ancien))
    with pytest.raises(RefusAction):
        nettoyer_temporaires(3, tmp_path)                                          # moins de 7 jours : refusé
    assert "1 fichiers temporaires" in nettoyer_temporaires(7, tmp_path)
    assert not vieux.exists() and recent.exists()


# ---------------------------------------------------------------- confirmation obligatoire


def test_action_proposee_puis_confirmee_une_seule_fois(tmp_path, monkeypatch):
    cerveau = CerveauActions({"type": "changer_theme", "parametres_json": json.dumps({"mode": "sombre"})}, agents_choisis=["eclairagiste"])
    cerveau.section = "entretien"
    monkeypatch.setattr("agents.chargeur.systeme_courant", lambda: "windows")
    changements = []
    from plateforme.windows import systeme as win

    monkeypatch.setattr(win, "changer_theme", lambda mode: changements.append(mode) or True)
    monkeypatch.setattr("plateforme.systeme", lambda: win)
    monkeypatch.setattr("main.systeme", lambda: win)
    client = client_avec(tmp_path, cerveau)
    r = client.post("/api/chat", json={"message": "Passe en mode sombre"}).json()
    assert len(r["actions"]) == 1 and r["actions"][0]["statut"] == "en_attente"
    assert "passer l'ordinateur en mode sombre" in r["actions"][0]["description"]
    assert changements == []                                                      # rien n'est fait avant « Confirmer »
    ident = r["actions"][0]["id"]
    fait = client.post(f"/api/actions/{ident}/confirmer").json()
    assert fait["statut"] == "faite" and changements == ["sombre"]
    assert client.post(f"/api/actions/{ident}/confirmer").status_code == 409     # jamais deux fois
    msgs = client.get(f"/api/discussions/{r['discussion_id']}").json()["messages"]
    assert msgs[1]["actions"][0]["statut"] == "faite"


def test_action_annulee(tmp_path, monkeypatch):
    cerveau = CerveauActions({"type": "changer_theme", "parametres_json": '{"mode": "clair"}'}, agents_choisis=["eclairagiste"])
    cerveau.section = "entretien"
    monkeypatch.setattr("agents.chargeur.systeme_courant", lambda: "windows")
    client = client_avec(tmp_path, cerveau)
    ident = client.post("/api/chat", json={"message": "Mode clair"}).json()["actions"][0]["id"]
    assert client.post(f"/api/actions/{ident}/annuler").json()["statut"] == "annulee"
    assert client.post(f"/api/actions/{ident}/confirmer").status_code == 409


def test_action_invalide_refusee_par_le_programme(tmp_path, monkeypatch):
    cerveau = CerveauActions({"type": "changer_theme", "parametres_json": '{"mode": "fluo"}'}, agents_choisis=["eclairagiste"])
    cerveau.section = "entretien"
    monkeypatch.setattr("agents.chargeur.systeme_courant", lambda: "windows")
    r = client_avec(tmp_path, cerveau).post("/api/chat", json={"message": "Mode fluo"}).json()
    assert r["actions"] == [] and "Action non préparée" in r["reponse"]


# ---------------------------------------------------------------- Spotify (DJ)


def test_connexion_spotify_pkce(tmp_path):
    faux = FauxSpotify()
    s = ServiceSpotify(Comptes(tmp_path), faux)
    with pytest.raises(ErreurSpotify):
        s.demarrer_connexion("pas-un-id")
    url = s.demarrer_connexion("0123456789abcdef0123456789abcdef")
    q = parse_qs(urlparse(url).query)
    assert q["code_challenge_method"] == ["S256"] and q["redirect_uri"] == ["http://127.0.0.1:8765/api/spotify/retour"]
    with pytest.raises(ErreurSpotify):
        s.terminer_connexion("code", "etat-falsifie")                          # protection anti-falsification
    s.terminer_connexion("code", q["state"][0])
    assert s.en_cours()["titre"] == "Hello"
    token = [c for c in faux.appels if c[1] == "/api/token"]
    assert len(token) == 1


def test_dj_propose_puis_cree_la_playlist(tmp_path):
    faux = FauxSpotify()
    proposition = {"type": "spotify_creer_playlist", "parametres_json": json.dumps({
        "nom": "Soirée", "titres": [{"titre": "Hello", "artiste": "Adele"}, {"titre": "Inexistant", "artiste": "Personne"}]})}
    cerveau = CerveauActions(proposition, agents_choisis=["dj"])
    cerveau.section = "divertissement"
    client = client_avec(tmp_path, cerveau, faux)
    Comptes(tmp_path).definir_spotify("0123456789abcdef0123456789abcdef", "r", "a", time.time() + 3600)
    r = client.post("/api/chat", json={"message": "Fais-moi une playlist"}).json()
    action = r["actions"][0]
    assert "créer la playlist privée « Soirée »" in action["description"] and "1 introuvables" in action["description"]
    assert not any(c[0] == "POST" and c[1].endswith("/me/playlists") for c in faux.appels)   # pas avant « Confirmer »
    fait = client.post(f"/api/actions/{action['id']}/confirmer").json()
    assert fait["statut"] == "faite" and "1 titres" in fait["resultat"]
    assert any(c[1].endswith("/me/playlists") for c in faux.appels)


def test_spotify_non_connecte(tmp_path):
    client = client_avec(tmp_path, FauxCerveau())
    assert client.get("/api/spotify/en-cours").json() == {"connecte": False}
    assert client.post("/api/spotify/pause").status_code == 409
