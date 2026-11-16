"""Informations sur l'ordinateur, en LECTURE SEULE.

Aucun fichier n'est jamais modifié, déplacé ou supprimé ici : les agents d'entretien proposent,
Monsieur décide (et toute suppression future passera par un bouton « Confirmer »).
Les dossiers personnels ne sont lus que s'ils ont été choisis dans les Réglages.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

LIMITE_FICHIERS = 20_000      # on arrête de compter au-delà (dossiers énormes)


def taille_dossier(dossier: Path) -> dict:
    """Taille et nombre de fichiers d'un dossier (parcours limité, sans suivre les raccourcis)."""
    total, nombre, plus_vieux = 0, 0, None
    if not dossier.is_dir():
        return {"dossier": str(dossier), "existe": False}
    for racine, _, fichiers in os.walk(dossier, followlinks=False):
        for f in fichiers:
            try:
                st = os.lstat(os.path.join(racine, f))
            except OSError:
                continue
            total += st.st_size
            nombre += 1
            plus_vieux = st.st_mtime if plus_vieux is None else min(plus_vieux, st.st_mtime)
            if nombre >= LIMITE_FICHIERS:
                break
        if nombre >= LIMITE_FICHIERS:
            break
    return {
        "dossier": str(dossier),
        "existe": True,
        "taille_mo": round(total / 1024**2, 1),
        "fichiers": nombre,
        "compte_partiel": nombre >= LIMITE_FICHIERS,
        "plus_ancien_jours": None if plus_vieux is None else int((time.time() - plus_vieux) / 86400),
    }


# ---------------------------------------------------------------- jeux installés

_CLE_VALEUR = re.compile(r'"([^"]+)"\s+"([^"]*)"')


def _steam_bibliotheques(steamapps: Path) -> list[Path]:
    dossiers = [steamapps]
    vdf = steamapps / "libraryfolders.vdf"
    if vdf.exists():
        for cle, valeur in _CLE_VALEUR.findall(vdf.read_text(encoding="utf-8", errors="replace")):
            if cle == "path":
                autre = Path(valeur.replace("\\\\", "\\")) / "steamapps"
                if autre not in dossiers:
                    dossiers.append(autre)
    return dossiers


def jeux_steam(dossiers_steamapps: list[Path]) -> list[dict]:
    jeux = []
    for base in dossiers_steamapps:
        for biblio in _steam_bibliotheques(base) if base.is_dir() else []:
            for acf in sorted(biblio.glob("appmanifest_*.acf")):
                infos = dict(_CLE_VALEUR.findall(acf.read_text(encoding="utf-8", errors="replace")))
                if "name" in infos:
                    jeux.append({
                        "nom": infos["name"],
                        "launcher": "Steam",
                        "taille_go": round(int(infos.get("SizeOnDisk", 0)) / 1024**3, 1),
                        "mis_a_jour": time.strftime("%d.%m.%Y", time.localtime(int(infos.get("LastUpdated", 0) or 0))) if infos.get("LastUpdated") else None,
                    })
    return jeux


def jeux_epic(dossiers_manifestes: list[Path]) -> list[dict]:
    jeux = []
    for dossier in dossiers_manifestes:
        for item in sorted(dossier.glob("*.item")) if dossier.is_dir() else []:
            try:
                infos = json.loads(item.read_text(encoding="utf-8", errors="replace"))
            except ValueError:
                continue
            if infos.get("DisplayName"):
                jeux.append({"nom": infos["DisplayName"], "launcher": "Epic Games",
                             "taille_go": round(int(infos.get("InstallSize", 0)) / 1024**3, 1)})
    return jeux


# ---------------------------------------------------------------- dossiers choisis par Monsieur

def dans_dossiers_autorises(chemin: Path, autorises: list[str]) -> bool:
    try:
        chemin = chemin.resolve()
    except OSError:
        return False
    for a in autorises:
        try:
            base = Path(a).expanduser().resolve()
        except OSError:
            continue
        if chemin == base or base in chemin.parents:
            return True
    return False


def inventaire_dossiers(autorises: list[str], limite: int = 300) -> dict:
    """Liste (sans les ouvrir) les fichiers des dossiers choisis dans les Réglages : nom, type, taille, âge."""
    if not autorises:
        return {"info": "Aucun dossier choisi. Monsieur peut en ajouter dans Réglages › Dossiers."}
    resultat = []
    for a in autorises:
        base = Path(a).expanduser()
        if not base.is_dir():
            resultat.append({"dossier": a, "existe": False})
            continue
        fichiers = []
        for entree in sorted(base.iterdir(), key=lambda e: e.name.lower())[:limite]:
            try:
                st = entree.lstat()
            except OSError:
                continue
            fichiers.append({
                "nom": entree.name,
                "type": "dossier" if entree.is_dir() else (entree.suffix.lower().lstrip(".") or "sans extension"),
                "taille_ko": None if entree.is_dir() else round(st.st_size / 1024),
                "modifie_il_y_a_jours": int((time.time() - st.st_mtime) / 86400),
            })
        resultat.append({"dossier": str(base), "existe": True, "elements": fichiers})
    return {"dossiers": resultat}
