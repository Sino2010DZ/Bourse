"""Actions sur l'ordinateur, exécutées UNIQUEMENT après le bouton « Confirmer » de Monsieur.

- nettoyer_temporaires : supprime les fichiers du dossier temporaire du système plus vieux que N jours
  (jamais ailleurs ; les fichiers en cours d'utilisation sont simplement ignorés).
- ranger_fichiers : DÉPLACE des fichiers dans des sous-dossiers, à l'intérieur d'un dossier choisi dans les Réglages.
  Rien n'est supprimé ni écrasé : si un fichier du même nom existe déjà, il est laissé à sa place.
- changer_theme : mode clair ou sombre du système (réversible).
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from outils.ordinateur import dans_dossiers_autorises

_NOM_SUR = re.compile(r'^[^<>:"/\\|?*\x00-\x1f]{1,120}$')


class RefusAction(ValueError):
    pass


def dossier_temporaire() -> Path:
    return Path(tempfile.gettempdir())


def estimer_temporaires(jours: int, dossier: Path | None = None) -> dict:
    dossier = dossier or dossier_temporaire()
    limite = time.time() - jours * 86400
    nombre, taille = 0, 0
    for racine, _, fichiers in os.walk(dossier, followlinks=False):
        for f in fichiers:
            try:
                st = os.lstat(os.path.join(racine, f))
            except OSError:
                continue
            if st.st_mtime < limite:
                nombre += 1
                taille += st.st_size
    return {"dossier": str(dossier), "fichiers": nombre, "taille_mo": round(taille / 1024**2, 1)}


def nettoyer_temporaires(jours: int, dossier: Path | None = None) -> str:
    if jours < 7:
        raise RefusAction("seuls les fichiers temporaires de plus de 7 jours peuvent être supprimés")
    dossier = (dossier or dossier_temporaire()).resolve()
    limite = time.time() - jours * 86400
    supprimes, octets, ignores = 0, 0, 0
    for racine, dossiers, fichiers in os.walk(dossier, followlinks=False):
        for f in fichiers:
            chemin = Path(racine) / f
            try:
                st = chemin.lstat()
                if st.st_mtime >= limite or not str(chemin.resolve()).startswith(str(dossier)):
                    continue
                chemin.unlink()
                supprimes += 1
                octets += st.st_size
            except OSError:
                ignores += 1     # fichier utilisé par un programme : on le laisse
    return (f"{supprimes} fichiers temporaires de plus de {jours} jours supprimés ({octets / 1024**2:.1f} Mo libérés)"
            + (f", {ignores} ignorés car en cours d'utilisation." if ignores else "."))


def verifier_rangement(dossier: str, deplacements: list[dict], autorises: list[str]) -> list[dict]:
    base = Path(dossier).expanduser()
    if not base.is_dir() or not dans_dossiers_autorises(base, autorises):
        raise RefusAction("ce dossier n'est pas dans la liste des dossiers choisis (Réglages › Dossiers)")
    propres = []
    for d in deplacements[:200]:
        fichier, vers = str(d.get("fichier", "")).strip(), str(d.get("vers", "")).strip()
        if not _NOM_SUR.match(fichier) or not _NOM_SUR.match(vers) or vers in (".", "..") or fichier in (".", ".."):
            raise RefusAction(f"nom invalide : « {fichier} » → « {vers} »")
        if not (base / fichier).is_file():
            raise RefusAction(f"fichier introuvable : « {fichier} »")
        propres.append({"fichier": fichier, "vers": vers})
    if not propres:
        raise RefusAction("aucun fichier à ranger")
    return propres


def ranger_fichiers(dossier: str, deplacements: list[dict], autorises: list[str]) -> str:
    propres = verifier_rangement(dossier, deplacements, autorises)      # revérifié au moment d'agir
    base = Path(dossier).expanduser()
    faits, laisses = 0, []
    for d in propres:
        cible = base / d["vers"]
        cible.mkdir(exist_ok=True)
        destination = cible / d["fichier"]
        if destination.exists():
            laisses.append(d["fichier"])
            continue
        shutil.move(str(base / d["fichier"]), str(destination))
        faits += 1
    return f"{faits} fichiers rangés dans {base}." + (f" Laissés en place (nom déjà pris) : {', '.join(laisses)}." if laisses else "")
