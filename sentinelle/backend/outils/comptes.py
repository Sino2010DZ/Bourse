"""Accès aux comptes de Monsieur (agenda, Gmail), donnés par lui dans Réglages › Comptes.

- Rangés dans data/comptes.json, lisible par lui seul sur l'ordinateur ; jamais renvoyés à l'interface
  (elle voit seulement « configuré : oui/non »), jamais écrits dans le journal ni sur GitHub.
- Uniquement des accès en LECTURE : lien iCal secret (agenda) et mot de passe d'application Gmail.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from urllib.parse import urlparse


class ErreurCompte(ValueError):
    pass


_EMAIL = re.compile(r"^[^@\s]+@(gmail|googlemail)\.com$", re.I)


def valider_lien_ical(lien: str) -> str:
    lien = lien.strip()
    if lien.startswith("webcal://"):
        lien = "https://" + lien[len("webcal://"):]
    u = urlparse(lien)
    if u.scheme != "https" or not u.hostname or u.hostname in ("localhost", "127.0.0.1") or len(lien) > 1000:
        raise ErreurCompte("Collez le lien iCal secret de votre agenda (il commence par https:// ou webcal://).")
    return lien


def valider_gmail(adresse: str, mot_de_passe: str) -> tuple[str, str]:
    adresse = adresse.strip()
    mot_de_passe = mot_de_passe.replace(" ", "").strip()
    if not _EMAIL.match(adresse):
        raise ErreurCompte("Indiquez une adresse Gmail (…@gmail.com).")
    if not re.fullmatch(r"[a-zA-Z]{16}", mot_de_passe):
        raise ErreurCompte("Le mot de passe d'application Gmail fait 16 lettres (créé sur myaccount.google.com › Sécurité).")
    return adresse, mot_de_passe


class Comptes:
    def __init__(self, dossier_donnees: Path) -> None:
        self.chemin = dossier_donnees / "comptes.json"
        self._verrou = threading.Lock()

    def _lire(self) -> dict:
        if not self.chemin.exists():
            return {}
        try:
            return json.loads(self.chemin.read_text(encoding="utf-8"))
        except ValueError:
            return {}

    def _ecrire(self, donnees: dict) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            self.chemin.chmod(0o600)
        except OSError:
            pass

    def etat(self) -> dict:
        """Ce que l'interface a le droit de voir : jamais les secrets eux-mêmes."""
        d = self._lire()
        return {
            "agenda": bool(d.get("agenda_ical")),
            "gmail": bool(d.get("gmail_adresse")),
            "gmail_adresse": d.get("gmail_adresse"),
            "spotify": bool(d.get("spotify_rafraichissement")),
        }

    def definir_agenda(self, lien: str) -> None:
        with self._verrou:
            d = self._lire()
            d["agenda_ical"] = valider_lien_ical(lien)
            self._ecrire(d)

    def definir_gmail(self, adresse: str, mot_de_passe: str) -> None:
        with self._verrou:
            d = self._lire()
            d["gmail_adresse"], d["gmail_mot_de_passe"] = valider_gmail(adresse, mot_de_passe)
            self._ecrire(d)

    def oublier(self, compte: str) -> None:
        with self._verrou:
            d = self._lire()
            cles = {
                "agenda": ["agenda_ical"],
                "gmail": ["gmail_adresse", "gmail_mot_de_passe"],
                "spotify": ["spotify_client_id", "spotify_rafraichissement", "spotify_acces", "spotify_expire"],
            }.get(compte, [])
            for c in cles:
                d.pop(c, None)
            self._ecrire(d)

    def lien_agenda(self) -> str | None:
        return self._lire().get("agenda_ical")

    def gmail(self) -> tuple[str, str] | None:
        d = self._lire()
        return (d["gmail_adresse"], d["gmail_mot_de_passe"]) if d.get("gmail_adresse") else None

    def definir_spotify(self, client_id: str, rafraichissement: str, acces: str, expire: float) -> None:
        with self._verrou:
            d = self._lire()
            d.update(spotify_client_id=client_id, spotify_rafraichissement=rafraichissement,
                     spotify_acces=acces, spotify_expire=expire)
            self._ecrire(d)

    def spotify(self) -> dict | None:
        d = self._lire()
        if not d.get("spotify_rafraichissement"):
            return None
        return {"client_id": d["spotify_client_id"], "rafraichissement": d["spotify_rafraichissement"],
                "acces": d.get("spotify_acces"), "expire": d.get("spotify_expire", 0)}
