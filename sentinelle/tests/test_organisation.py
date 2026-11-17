"""Tests Agenda (iCal), Rappels et Courrier (Gmail) : lecture seule, secrets jamais renvoyés. Sans Internet."""

import asyncio
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from conftest import METEO_BRUTE, FauxCerveau, fabriquer_reglages, lecteur_f1
from journal import FUSEAU, Journal, Trace
from outils.agenda import evenements
from outils.base_de_donnees import BaseDeDonnees
from outils.comptes import Comptes, ErreurCompte, valider_gmail, valider_lien_ical
from outils.courrier import lire_entetes
from planificateur import verifier_rappels

ICAL = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//FR
BEGIN:VEVENT
UID:1
DTSTART;TZID=Europe/Zurich:20261118T090000
DTEND;TZID=Europe/Zurich:20261118T100000
SUMMARY:Dentiste
LOCATION:Rue du Rh\xc3\xb4ne 1, Gen\xc3\xa8ve
END:VEVENT
BEGIN:VEVENT
UID:2
DTSTART:20261116T170000Z
DTEND:20261116T180000Z
RRULE:FREQ=DAILY;COUNT=5
SUMMARY:Sport
END:VEVENT
BEGIN:VEVENT
UID:3
DTSTART;VALUE=DATE:20261119
SUMMARY:Anniversaire de Tony
END:VEVENT
END:VCALENDAR
"""


class FauxImap:
    """Imite imaplib.IMAP4_SSL et note chaque commande pour vérifier la lecture seule."""

    commandes = []

    def __init__(self, serveur):
        FauxImap.commandes = [("connexion", serveur)]

    def login(self, adresse, mdp):
        FauxImap.commandes.append(("login", adresse))
        if mdp != "abcdabcdabcdabcd":
            import imaplib

            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    def select(self, boite, readonly=False):
        FauxImap.commandes.append(("select", boite, readonly))

    def search(self, charset, critere):
        FauxImap.commandes.append(("search", critere))
        return "OK", [b"1 2"]

    def fetch(self, ident, quoi):
        FauxImap.commandes.append(("fetch", quoi))
        entetes = {
            b"1": b"From: =?utf-8?q?Banque_Cantonale?= <info@bcge.ch>\r\nSubject: =?utf-8?q?Votre_relev=C3=A9?=\r\nDate: Mon, 16 Nov 2026 08:00:00 +0100\r\n\r\n",
            b"2": b"From: Promo <promo@shop.ch>\r\nSubject: -50% ce week-end\r\nDate: Mon, 16 Nov 2026 09:00:00 +0100\r\n\r\n",
        }
        return "OK", [(b"x", entetes[ident])]

    def logout(self):
        FauxImap.commandes.append(("logout",))


def lecteur_mails(adresse, mdp, nombre=30):
    return lire_entetes(adresse, mdp, nombre, fabrique=FauxImap)


@pytest.fixture
def client_orga(tmp_path):
    from main import creer_app
    from outils.f1 import ServiceF1
    from outils.meteo import ServiceMeteo

    app = creer_app(
        fabriquer_reglages(tmp_path), FauxCerveau(), planificateur=False,
        meteo=ServiceMeteo(lambda u: METEO_BRUTE), f1=ServiceF1(lecteur_f1),
        telecharger_ical=lambda lien: ICAL, lecteur_mails=lecteur_mails,
    )
    return TestClient(app)


# ---------------------------------------------------------------- agenda


def test_evenements_ical_avec_repetitions_et_journees():
    debut = datetime(2026, 11, 18, tzinfo=FUSEAU)
    evs = evenements(ICAL, debut, debut + timedelta(days=2))
    assert [e["titre"] for e in evs] == ["Dentiste", "Sport", "Anniversaire de Tony", "Sport"]
    assert evs[0]["debut"] == "2026-11-18T09:00:00+01:00" and evs[0]["lieu"] == "Rue du Rhône 1, Genève"
    assert evs[1]["debut"] == "2026-11-18T18:00:00+01:00"          # 17h UTC = 18h à Zurich
    assert evs[2]["toute_la_journee"] is True


@pytest.mark.parametrize("lien", ["http://exemple.ch/cal.ics", "https://localhost/cal.ics", "pas un lien"])
def test_lien_ical_refuse(lien):
    with pytest.raises(ErreurCompte):
        valider_lien_ical(lien)


def test_webcal_converti():
    assert valider_lien_ical("webcal://p01-caldav.icloud.com/published/2/abc") == "https://p01-caldav.icloud.com/published/2/abc"


def test_connecter_agenda_sans_renvoyer_le_lien(client_orga, tmp_path):
    secret = "https://calendar.google.com/calendar/ical/moi%40gmail.com/private-SECRET123/basic.ics"
    r = client_orga.put("/api/comptes/agenda", json={"lien": secret})
    assert r.status_code == 200 and r.json()["agenda"] is True
    assert "SECRET123" not in json.dumps(client_orga.get("/api/comptes").json())
    assert "SECRET123" in (tmp_path / "comptes.json").read_text()
    a = client_orga.get("/api/agenda").json()
    assert a["connecte"] is True and "evenements" in a
    assert client_orga.delete("/api/comptes/agenda").status_code == 409            # bouton Confirmer obligatoire
    assert client_orga.delete("/api/comptes/agenda", params={"confirmer": True}).json()["agenda"] is False


# ---------------------------------------------------------------- courrier (Gmail)


def test_gmail_lecture_seule():
    messages = lecteur_mails("moi@gmail.com", "abcdabcdabcdabcd")
    assert messages[0] == {"de": "Promo", "adresse": "promo@shop.ch", "objet": "-50% ce week-end", "date": "Mon, 16 Nov 2026 09:00:00 +0100"}
    assert messages[1]["de"] == "Banque Cantonale" and messages[1]["objet"] == "Votre relevé"
    commandes = FauxImap.commandes
    assert ("select", "INBOX", True) in commandes                                   # boîte ouverte en lecture seule
    assert all("PEEK" in c[1] for c in commandes if c[0] == "fetch")              # rien n'est marqué comme lu
    assert not any(c[0] in ("store", "expunge", "append", "copy", "move") for c in commandes)


@pytest.mark.parametrize("adresse,mdp", [("moi@yahoo.fr", "abcdabcdabcdabcd"), ("moi@gmail.com", "court"), ("moi@gmail.com", "monVraiMotDePasse!")])
def test_gmail_identifiants_refuses(adresse, mdp):
    with pytest.raises(ErreurCompte):
        valider_gmail(adresse, mdp)


def test_connecter_gmail(client_orga):
    assert client_orga.put("/api/comptes/gmail", json={"adresse": "moi@gmail.com", "mot_de_passe": "zzzz zzzz zzzz zzzz"}).status_code == 422
    r = client_orga.put("/api/comptes/gmail", json={"adresse": "moi@gmail.com", "mot_de_passe": "abcd abcd abcd abcd"})
    assert r.json() == {"agenda": False, "gmail": True, "gmail_adresse": "moi@gmail.com", "spotify": False}


# ---------------------------------------------------------------- rappels


def test_rappels_api_et_notification(client_orga, tmp_path):
    passe = (datetime.now(FUSEAU) - timedelta(minutes=1)).isoformat(timespec="minutes")
    r = client_orga.post("/api/rappels", json={"texte": "Appeler le garage", "echeance": passe})
    assert r.status_code == 201
    base, notifs = BaseDeDonnees(tmp_path), []
    for _ in range(2):
        asyncio.run(verifier_rappels(base, lambda t, m: notifs.append(m)))
    assert notifs == ["Appeler le garage"]                                       # une seule notification
    ident = r.json()["id"]
    assert client_orga.post(f"/api/rappels/{ident}/fait").json()["fait"] == 1
    assert client_orga.delete(f"/api/rappels/{ident}").status_code == 409
    assert client_orga.delete(f"/api/rappels/{ident}", params={"confirmer": True}).status_code == 200


def test_agent_rappels_cree_un_rappel(tmp_path):
    from commandants.organisation import CommandantSecretariat

    class CerveauRappels(FauxCerveau):
        async def __call__(self, d):
            if d.qui == "organisation/rappels":
                self.demandes.append(d)
                from cerveau import Reponse

                demain = (datetime.now(FUSEAU) + timedelta(days=1)).strftime("%Y-%m-%dT09:00")
                return Reponse("", d.modele, 10, donnees={
                    "reponse": "C'est noté, Monsieur.",
                    "nouveaux_rappels": [{"texte": "Appeler Pepper", "echeance": demain},
                                         {"texte": "Trop tard", "echeance": "2020-01-01T09:00"}],
                })
            return await super().__call__(d)

    base = BaseDeDonnees(tmp_path)
    cmd = CommandantSecretariat(fabriquer_reglages(tmp_path), CerveauRappels(agents_choisis=["rappels"]),
                                None, None, None, None, None, base=base)
    texte = asyncio.run(cmd.executer("Rappelle-moi demain d'appeler Pepper", Trace(Journal(tmp_path))))
    assert "C'est noté" in texte and "Rappel créé par Sentinelle : « Appeler Pepper »" in texte
    assert "non créé" in texte                                                   # date passée refusée
    assert [r["texte"] for r in base.rappels()] == ["Appeler Pepper"]
