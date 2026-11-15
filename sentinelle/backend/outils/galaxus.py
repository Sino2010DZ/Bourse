"""Outil Galaxus : lit le nom et le prix (CHF) d'une page produit publique de galaxus.ch.

Règles de politesse (voir SENTINELLE.md) :
- uniquement des pages produits publiques (autorisées par le robots.txt de Galaxus), sans compte ;
- une requête par seconde au maximum, et en pratique une seule par produit et par jour ;
- le programme se présente honnêtement (« Sentinelle ») : il ne se fait pas passer pour un navigateur
  et ne contourne aucune protection. Si Galaxus refuse, Monsieur saisit le prix à la main.

Le prix est lu dans les données « schema.org » (JSON-LD) que Galaxus publie pour les moteurs de recherche.
"""

from __future__ import annotations

import html
import json
import re
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

DOMAINES = {"galaxus.ch", "www.galaxus.ch"}
AGENT = "Mozilla/5.0 (compatible; Sentinelle/0.3; assistant personnel; une lecture par jour)"
_ID_PRODUIT = re.compile(r"-(\d{4,12})(?:[/?#]|$)")


class ErreurGalaxus(Exception):
    """Lecture impossible. `raison` : lien_invalide, refuse, introuvable, prix_absent, reseau."""

    def __init__(self, raison: str, message: str) -> None:
        super().__init__(message)
        self.raison = raison


@dataclass
class FicheProduit:
    nom: str
    prix: float          # en CHF
    disponible: bool | None = None


def valider_lien(url: str) -> tuple[str, str]:
    """Vérifie un lien Galaxus et renvoie (lien propre, numéro du produit)."""
    url = url.strip()
    try:
        u = urlparse(url)
    except ValueError:
        raise ErreurGalaxus("lien_invalide", "Ce lien n'est pas valide.") from None
    if u.scheme not in ("http", "https") or (u.hostname or "").lower() not in DOMAINES:
        raise ErreurGalaxus("lien_invalide", "Collez un lien de produit galaxus.ch (Suisse).")
    if "/product/" not in u.path:
        raise ErreurGalaxus("lien_invalide", "Ce lien Galaxus ne mène pas à une page produit.")
    trouve = _ID_PRODUIT.search(u.path)
    if not trouve:
        raise ErreurGalaxus("lien_invalide", "Je ne trouve pas le numéro du produit dans ce lien.")
    return f"https://www.galaxus.ch{u.path}", trouve.group(1)


def _objets_jsonld(page: str):
    for bloc in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            donnees = json.loads(html.unescape(bloc.strip()))
        except ValueError:
            continue
        pile = [donnees]
        while pile:
            o = pile.pop()
            if isinstance(o, list):
                pile.extend(o)
            elif isinstance(o, dict):
                yield o
                if "@graph" in o:
                    pile.append(o["@graph"])


def _prix(offre: dict) -> float | None:
    for cle in ("price", "lowPrice"):
        valeur = offre.get(cle)
        if valeur in (None, ""):
            continue
        try:
            return float(str(valeur).replace("'", "").replace(",", "."))
        except ValueError:
            continue
    spec = offre.get("priceSpecification")
    if isinstance(spec, dict):
        return _prix(spec)
    return None


def extraire_fiche(page: str) -> FicheProduit:
    """Trouve le nom et le prix en CHF dans le HTML d'une page produit."""
    for o in _objets_jsonld(page):
        types = o.get("@type")
        types = types if isinstance(types, list) else [types]
        if "Product" not in types:
            continue
        offres = o.get("offers")
        offres = offres if isinstance(offres, list) else [offres]
        for offre in offres:
            if not isinstance(offre, dict):
                continue
            devise = offre.get("priceCurrency", "CHF")
            prix = _prix(offre)
            if prix is None or devise != "CHF":
                continue
            dispo = offre.get("availability")
            disponible = None if dispo is None else str(dispo).endswith("InStock")
            nom = html.unescape(str(o.get("name") or "")).strip() or "Produit Galaxus"
            return FicheProduit(nom=nom[:120], prix=round(prix, 2), disponible=disponible)
    raise ErreurGalaxus("prix_absent", "Je ne trouve pas le prix sur cette page.")


class LecteurGalaxus:
    """Télécharge une page produit (une requête par seconde au maximum)."""

    def __init__(self, intervalle: float = 1.0, delai: float = 20.0) -> None:
        self.intervalle = intervalle
        self.delai = delai
        self._verrou = threading.Lock()
        self._derniere = 0.0

    def _patienter(self) -> None:
        with self._verrou:
            attente = self._derniere + self.intervalle - time.monotonic()
            if attente > 0:
                time.sleep(attente)
            self._derniere = time.monotonic()

    def lire(self, url: str) -> FicheProduit:
        lien, _ = valider_lien(url)
        self._patienter()
        requete = urllib.request.Request(lien, headers={"User-Agent": AGENT, "Accept-Language": "fr-CH,fr;q=0.9"})
        try:
            with urllib.request.urlopen(requete, timeout=self.delai) as r:
                page = r.read(3_000_000).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 429):
                raise ErreurGalaxus("refuse", "Galaxus refuse la lecture automatique : saisissez le prix à la main.") from None
            if e.code == 404:
                raise ErreurGalaxus("introuvable", "Ce produit n'existe plus sur Galaxus.") from None
            raise ErreurGalaxus("reseau", f"Galaxus a répondu avec l'erreur {e.code}.") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ErreurGalaxus("reseau", "Galaxus est injoignable (connexion Internet ?).") from None
        return extraire_fiche(page)
