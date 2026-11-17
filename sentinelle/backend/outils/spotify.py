"""Spotify : connexion sécurisée (OAuth « PKCE », sans mot de passe ni secret), musique en cours, pause/lecture,
goûts musicaux, et création de playlist APRÈS le bouton « Confirmer » de Monsieur.

Monsieur crée une petite application sur developer.spotify.com (identifiant « Client ID ») avec l'adresse de retour
http://127.0.0.1:8765/api/spotify/retour . Le jeton reste sur l'ordinateur (comptes.json).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

COMPTES = "https://accounts.spotify.com"
API = "https://api.spotify.com/v1"
RETOUR = "http://127.0.0.1:8765/api/spotify/retour"
PERMISSIONS = " ".join([
    "user-read-playback-state", "user-modify-playback-state", "user-read-currently-playing",
    "user-top-read", "user-read-recently-played", "playlist-read-private",
    "playlist-modify-private", "playlist-modify-public",
])


class ErreurSpotify(Exception):
    pass


def valider_client_id(client_id: str) -> str:
    client_id = client_id.strip()
    if not re.fullmatch(r"[0-9a-f]{32}", client_id):
        raise ErreurSpotify("Le Client ID Spotify fait 32 caractères (chiffres et lettres a à f).")
    return client_id


def preparer_connexion(client_id: str) -> tuple[str, str, str]:
    """Renvoie (adresse d'autorisation, vérificateur PKCE, état anti-falsification)."""
    verificateur = secrets.token_urlsafe(64)[:96]
    defi = base64.urlsafe_b64encode(hashlib.sha256(verificateur.encode()).digest()).decode().rstrip("=")
    etat = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id, "response_type": "code", "redirect_uri": RETOUR, "scope": PERMISSIONS,
        "code_challenge_method": "S256", "code_challenge": defi, "state": etat,
    }
    return f"{COMPTES}/authorize?{urllib.parse.urlencode(params)}", verificateur, etat


def _http(methode: str, url: str, jeton: str | None = None, corps: dict | None = None, formulaire: dict | None = None):
    entetes = {"User-Agent": "Sentinelle/0.7"}
    donnees = None
    if jeton:
        entetes["Authorization"] = f"Bearer {jeton}"
    if formulaire is not None:
        donnees = urllib.parse.urlencode(formulaire).encode()
        entetes["Content-Type"] = "application/x-www-form-urlencoded"
    elif corps is not None:
        donnees = json.dumps(corps).encode()
        entetes["Content-Type"] = "application/json"
    elif methode in ("PUT", "POST"):
        donnees = b""
    requete = urllib.request.Request(url, data=donnees, method=methode, headers=entetes)
    try:
        with urllib.request.urlopen(requete, timeout=15) as r:
            brut = r.read()
            return r.status, (json.loads(brut) if brut else None)
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read() or b"{}")
        except ValueError:
            detail = {}
        return e.code, detail


class ServiceSpotify:
    def __init__(self, comptes, http: Callable = _http) -> None:
        self.comptes = comptes
        self.http = http
        self._attente: dict[str, tuple[str, str, float]] = {}   # état -> (client_id, vérificateur, date)

    # ------------------------------------------------------------ connexion

    def demarrer_connexion(self, client_id: str) -> str:
        client_id = valider_client_id(client_id)
        url, verificateur, etat = preparer_connexion(client_id)
        self._attente = {e: v for e, v in self._attente.items() if time.time() - v[2] < 900}
        self._attente[etat] = (client_id, verificateur, time.time())
        return url

    def terminer_connexion(self, code: str, etat: str) -> None:
        attente = self._attente.pop(etat, None)
        if not attente:
            raise ErreurSpotify("Demande de connexion inconnue ou expirée : recommencez depuis Sentinelle.")
        client_id, verificateur, _ = attente
        statut, rep = self.http("POST", f"{COMPTES}/api/token", formulaire={
            "grant_type": "authorization_code", "code": code, "redirect_uri": RETOUR,
            "client_id": client_id, "code_verifier": verificateur,
        })
        if statut != 200 or not rep or "access_token" not in rep:
            raise ErreurSpotify("Spotify a refusé la connexion.")
        self.comptes.definir_spotify(client_id, rep["refresh_token"], rep["access_token"], time.time() + rep.get("expires_in", 3600) - 60)

    def _jeton(self) -> str:
        infos = self.comptes.spotify()
        if not infos:
            raise ErreurSpotify("Spotify n'est pas connecté (Réglages › Comptes).")
        if infos.get("expire", 0) > time.time() and infos.get("acces"):
            return infos["acces"]
        statut, rep = self.http("POST", f"{COMPTES}/api/token", formulaire={
            "grant_type": "refresh_token", "refresh_token": infos["rafraichissement"], "client_id": infos["client_id"],
        })
        if statut != 200 or not rep or "access_token" not in rep:
            raise ErreurSpotify("La connexion Spotify a expiré : reconnectez-le dans Réglages › Comptes.")
        self.comptes.definir_spotify(infos["client_id"], rep.get("refresh_token", infos["rafraichissement"]),
                                     rep["access_token"], time.time() + rep.get("expires_in", 3600) - 60)
        return rep["access_token"]

    def _api(self, methode: str, chemin: str, corps: dict | None = None):
        return self.http(methode, f"{API}{chemin}", self._jeton(), corps)

    # ------------------------------------------------------------ lecture

    def en_cours(self) -> dict:
        statut, rep = self._api("GET", "/me/player")
        if statut == 204 or not rep or not rep.get("item"):
            return {"connecte": True, "en_lecture": False}
        piste = rep["item"]
        return {
            "connecte": True,
            "en_lecture": bool(rep.get("is_playing")),
            "titre": piste.get("name"),
            "artistes": ", ".join(a["name"] for a in piste.get("artists", [])),
            "album": (piste.get("album") or {}).get("name"),
            "pochette": ((piste.get("album") or {}).get("images") or [{}])[-1].get("url"),
            "appareil": (rep.get("device") or {}).get("name"),
        }

    def commande(self, action: str) -> bool:
        """Pause, lecture ou titre suivant (demandé par Monsieur avec les boutons de la carte Musique)."""
        chemins = {"pause": ("PUT", "/me/player/pause"), "lecture": ("PUT", "/me/player/play"), "suivant": ("POST", "/me/player/next")}
        if action not in chemins:
            raise ErreurSpotify("Commande inconnue.")
        statut, _ = self._api(*chemins[action])
        if statut == 403:
            raise ErreurSpotify("Spotify Premium est nécessaire pour piloter la lecture.")
        if statut == 404:
            raise ErreurSpotify("Aucun appareil Spotify actif : lancez la musique dans Spotify d'abord.")
        return statut in (200, 202, 204)

    def profil_musical(self) -> dict:
        _, top = self._api("GET", "/me/top/artists?limit=10&time_range=medium_term")
        _, recents = self._api("GET", "/me/player/recently-played?limit=15")
        _, listes = self._api("GET", "/me/playlists?limit=20")
        return {
            "artistes_preferes": [{"nom": a["name"], "genres": a.get("genres", [])[:3]} for a in (top or {}).get("items", [])],
            "ecoutes_recentes": [f"{i['track']['name']} — {i['track']['artists'][0]['name']}" for i in (recents or {}).get("items", []) if i.get("track")],
            "playlists": [p["name"] for p in (listes or {}).get("items", []) if p],
        }

    def chercher_titre(self, titre: str, artiste: str) -> dict | None:
        q = urllib.parse.quote(f"track:{titre} artist:{artiste}")
        _, rep = self._api("GET", f"/search?q={q}&type=track&limit=1")
        items = ((rep or {}).get("tracks") or {}).get("items") or []
        if not items:
            return None
        t = items[0]
        return {"uri": t["uri"], "titre": t["name"], "artiste": t["artists"][0]["name"]}

    # ------------------------------------------------------------ écriture (après « Confirmer » seulement)

    def creer_playlist(self, nom: str, description: str, uris: list[str]) -> str:
        corps = {"name": nom[:100], "description": description[:300], "public": False}
        statut, liste = self._api("POST", "/me/playlists", corps)
        if statut == 404:
            _, moi = self._api("GET", "/me")
            statut, liste = self._api("POST", f"/users/{(moi or {}).get('id')}/playlists", corps)
        if statut not in (200, 201) or not liste:
            raise ErreurSpotify("Spotify n'a pas pu créer la playlist.")
        for i in range(0, len(uris), 100):
            statut, _ = self._api("POST", f"/playlists/{liste['id']}/items", {"uris": uris[i:i + 100]})
            if statut == 404:
                self._api("POST", f"/playlists/{liste['id']}/tracks", {"uris": uris[i:i + 100]})
        return (liste.get("external_urls") or {}).get("spotify", "")




