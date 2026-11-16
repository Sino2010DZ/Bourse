"""Fonctions macOS."""

from __future__ import annotations

import platform
import subprocess


def nom() -> str:
    version = platform.mac_ver()[0]
    return f"macOS {version}" if version else "macOS"


def notifier(titre: str, message: str) -> bool:
    """Notification native du Mac (Centre de notifications)."""
    def echapper(texte: str) -> str:
        return texte.replace("\\", "\\\\").replace('"', '\\"')

    script = f'display notification "{echapper(message)}" with title "{echapper(titre)}"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, timeout=5, capture_output=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def ouvrir_lien(url: str) -> bool:
    """Ouvre un lien dans le navigateur par défaut du Mac."""
    try:
        subprocess.run(["open", url], check=True, timeout=10, capture_output=True)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------- informations (lecture seule)

def _commande(args: list[str], delai: int = 15) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=delai).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def infos_materiel() -> dict:
    import json as _json
    import os

    infos = {"systeme": nom(), "processeur": _commande(["sysctl", "-n", "machdep.cpu.brand_string"]).strip(),
             "coeurs": os.cpu_count(), "cartes_graphiques": []}
    try:
        infos["memoire_go"] = round(int(_commande(["sysctl", "-n", "hw.memsize"]).strip()) / 1024**3)
    except ValueError:
        infos["memoire_go"] = None
    try:
        affichage = _json.loads(_commande(["system_profiler", "SPDisplaysDataType", "-json"], 30) or "{}")
        for carte in affichage.get("SPDisplaysDataType", []):
            infos["cartes_graphiques"].append({"nom": carte.get("sppci_model"), "memoire": carte.get("spdisplays_vram") or carte.get("spdisplays_vram_shared")})
    except ValueError:
        pass
    return infos


def batterie() -> dict | None:
    texte = _commande(["pmset", "-g", "batt"])
    if "InternalBattery" not in texte:
        return None
    ligne = [l for l in texte.splitlines() if "InternalBattery" in l][0]
    return {"etat": ligne.split("\t", 1)[-1].strip(), "source": texte.splitlines()[0].replace("Now drawing from", "Alimentation :").strip()}


def temperatures() -> dict:
    """Sans droits administrateur, macOS ne donne pas les degrés ; il indique la « pression thermique »."""
    texte = _commande(["pmset", "-g", "therm"]).strip()
    return {"disponible": bool(texte), "resume": texte or None,
            "note": "macOS ne donne pas les températures en degrés sans droits administrateur."}


def sauvegarde() -> dict:
    derniere = _commande(["tmutil", "latestbackup"]).strip()
    destination = _commande(["tmutil", "destinationinfo"]).strip()
    return {"outil": "Time Machine", "configuree": "Name" in destination,
            "derniere_sauvegarde": derniere or None, "destination": destination or None}


def apparence() -> dict:
    sombre = "Dark" in _commande(["defaults", "read", "-g", "AppleInterfaceStyle"])
    return {"mode": "sombre" if sombre else "clair", "eclairage_rgb": "non géré sur Mac"}


def dossiers_temporaires() -> list:
    from pathlib import Path

    return [Path.home() / "Library" / "Caches"]


def dossiers_jeux() -> dict:
    from pathlib import Path

    return {"steam": [Path.home() / "Library" / "Application Support" / "Steam" / "steamapps"], "epic": []}
