"""Lecture polie d'API publiques gratuites (sans clé, sans compte) : une requête par seconde et par site,
avec un cache pour ne pas redemander la même chose."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from urllib.parse import urlparse

AGENT = "Sentinelle/0.5 (assistant personnel)"
_verrou = threading.Lock()
_derniere: dict[str, float] = {}
_cache: dict[str, tuple[float, object]] = {}


def lire_json(url: str, duree_cache: float = 600, delai: float = 15.0):
    """Télécharge un JSON public. Lève OSError / ValueError en cas de souci."""
    maintenant = time.monotonic()
    en_cache = _cache.get(url)
    if en_cache and maintenant - en_cache[0] < duree_cache:
        return en_cache[1]
    hote = urlparse(url).hostname or ""
    with _verrou:
        attente = _derniere.get(hote, 0) + 1.0 - time.monotonic()
        if attente > 0:
            time.sleep(attente)
        _derniere[hote] = time.monotonic()
    requete = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
    for essai in range(3):   # jusqu'à 3 essais si la connexion a été coupée
        try:
            with urllib.request.urlopen(requete, timeout=delai) as r:
                donnees = json.loads(r.read(5_000_000).decode("utf-8"))
            break
        except OSError:
            if essai == 2:
                raise
            time.sleep(1.5 * (essai + 1))
    _cache[url] = (time.monotonic(), donnees)
    return donnees
