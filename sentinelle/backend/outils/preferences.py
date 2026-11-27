"""Préférences de l'interface (thème, mode automatique, budget du jour), dans data/preferences.json."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

DEFAUTS = {
    "theme": "nuit-or",
    "auto": False,             # suit le réglage clair/sombre du Mac
    "theme_clair": "ivoire",
    "theme_sombre": "nuit-or",
    "budget_jour_usd": 1.0,    # jauge « Quota du jour »
    "mode": "economique",      # « economique » (Grand Chef sur Haiku) ou « puissant » (Opus)
    "dossiers_autorises": [],  # seuls dossiers que les agents Fichiers ont le droit de lire
    "dossiers_projets": [],    # projets de code que le Codeur peut modifier (après « Confirmer »)
}
MODES = ("economique", "puissant")
_ID_THEME = re.compile(r"^[a-z0-9-]{1,40}$")


class ErreurPreferences(ValueError):
    pass


def valider(donnees: dict) -> dict:
    propre = dict(DEFAUTS)
    for cle in ("theme", "theme_clair", "theme_sombre"):
        valeur = str(donnees.get(cle, DEFAUTS[cle]))
        if not _ID_THEME.match(valeur):
            raise ErreurPreferences(f"Nom de thème invalide : {valeur}")
        propre[cle] = valeur
    mode = str(donnees.get("mode", DEFAUTS["mode"]))
    if mode not in MODES:
        raise ErreurPreferences(f"Mode inconnu : {mode}")
    propre["mode"] = mode
    propre["auto"] = bool(donnees.get("auto", DEFAUTS["auto"]))
    try:
        budget = float(donnees.get("budget_jour_usd", DEFAUTS["budget_jour_usd"]))
    except (TypeError, ValueError):
        raise ErreurPreferences("Le budget doit être un nombre.") from None
    propre["budget_jour_usd"] = round(min(max(budget, 0.05), 100.0), 2)
    propre["dossiers_autorises"] = _dossiers(donnees.get("dossiers_autorises", []))
    propre["dossiers_projets"] = _dossiers(donnees.get("dossiers_projets", []))
    return propre


def _dossiers(dossiers) -> list[str]:
    if not isinstance(dossiers, list):
        raise ErreurPreferences("La liste des dossiers est invalide.")
    propres = []
    for d in dossiers:
        d = str(d).strip()
        if not d:
            continue
        if len(d) > 300 or "\x00" in d:
            raise ErreurPreferences("Chemin de dossier invalide.")
        if d in ("/", "\\") or (len(d) <= 3 and d[1:2] == ":"):
            raise ErreurPreferences("Choisissez un dossier précis, pas tout le disque.")
        try:
            if Path(d).expanduser().resolve() == Path.home().resolve():
                raise ErreurPreferences("Choisissez un sous-dossier précis (ex. Téléchargements), pas tout le dossier personnel.")
        except OSError:
            raise ErreurPreferences("Chemin de dossier invalide.") from None
        propres.append(d)
    return propres[:10]


class Preferences:
    def __init__(self, dossier_donnees: Path) -> None:
        self.chemin = dossier_donnees / "preferences.json"
        self._verrou = threading.Lock()

    def lire(self) -> dict:
        with self._verrou:
            if not self.chemin.exists():
                return dict(DEFAUTS)
            try:
                return valider(json.loads(self.chemin.read_text(encoding="utf-8")))
            except (ValueError, ErreurPreferences):
                return dict(DEFAUTS)

    def modifier(self, changements: dict) -> dict:
        propre = valider({**self.lire(), **changements})
        with self._verrou:
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
            self.chemin.write_text(json.dumps(propre, ensure_ascii=False, indent=2), encoding="utf-8")
        return propre
