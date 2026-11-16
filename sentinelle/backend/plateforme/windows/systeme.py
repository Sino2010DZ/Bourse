"""Fonctions Windows (complétées lors de la dernière phase)."""

from __future__ import annotations

import platform


def nom() -> str:
    return f"{platform.system()} {platform.release()}".strip()


# Notification Windows (centre de notifications) via PowerShell, sans fenêtre visible.
_SCRIPT_NOTIF = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$modele = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textes = $modele.GetElementsByTagName('text')
$textes.Item(0).AppendChild($modele.CreateTextNode($env:SENTINELLE_TITRE)) > $null
$textes.Item(1).AppendChild($modele.CreateTextNode($env:SENTINELLE_MESSAGE)) > $null
$id = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show([Windows.UI.Notifications.ToastNotification]::new($modele))
"""


def notifier(titre: str, message: str) -> bool:
    """Notification native Windows. Le texte passe par des variables d'environnement (jamais dans le script)."""
    import os
    import subprocess

    env = {**os.environ, "SENTINELLE_TITRE": titre[:120], "SENTINELLE_MESSAGE": message[:400]}
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", _SCRIPT_NOTIF],
            env=env, check=True, timeout=15, capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def ouvrir_lien(url: str) -> bool:
    """Ouvre un lien dans le navigateur par défaut."""
    import webbrowser

    return webbrowser.open(url)


# ---------------------------------------------------------------- informations (lecture seule)

def _powershell(script: str, delai: int = 20) -> str:
    import subprocess

    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=delai, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except (OSError, ValueError, Exception):
        return ""


def _json_ps(script: str):
    import json

    texte = _powershell(script + " | ConvertTo-Json -Compress").strip()
    if not texte:
        return []
    try:
        donnees = json.loads(texte)
    except ValueError:
        return []
    return donnees if isinstance(donnees, list) else [donnees]


def infos_materiel() -> dict:
    import os

    cartes = _json_ps("Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate")
    memoire = _json_ps("Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory")
    cpu = _json_ps("Get-CimInstance Win32_Processor | Select-Object Name")
    return {
        "systeme": nom(),
        "processeur": cpu[0].get("Name") if cpu else None,
        "coeurs": os.cpu_count(),
        "memoire_go": round(int(memoire[0]["TotalPhysicalMemory"]) / 1024**3) if memoire else None,
        "cartes_graphiques": [{"nom": c.get("Name"), "pilote": c.get("DriverVersion"), "date_pilote": str(c.get("DriverDate"))} for c in cartes],
    }


def batterie() -> dict | None:
    b = _json_ps("Get-CimInstance Win32_Battery | Select-Object EstimatedChargeRemaining,BatteryStatus")
    return {"charge_pct": b[0].get("EstimatedChargeRemaining")} if b else None


def temperatures() -> dict:
    t = _json_ps("Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature | Select-Object InstanceName,CurrentTemperature")
    zones = [{"zone": z.get("InstanceName"), "celsius": round(z["CurrentTemperature"] / 10 - 273.15, 1)} for z in t if z.get("CurrentTemperature")]
    return {"disponible": bool(zones), "zones": zones,
            "note": None if zones else "Windows ne donne pas les températures sans droits administrateur (ou la carte mère ne les publie pas). La température de la carte graphique se lit dans AMD Adrenalin."}


def sauvegarde() -> dict:
    import os

    dossier = os.environ.get("OneDrive")
    actif = bool(_powershell("Get-Process OneDrive -ErrorAction SilentlyContinue | Select-Object -First 1 Id").strip())
    return {"outil": "OneDrive", "configuree": bool(dossier), "dossier": dossier, "en_marche": actif}


def apparence() -> dict:
    texte = _powershell("(Get-ItemProperty HKCU:/Software/Microsoft/Windows/CurrentVersion/Themes/Personalize).AppsUseLightTheme").strip()
    mode = {"0": "sombre", "1": "clair"}.get(texte, "inconnu")
    return {"mode": mode, "eclairage_rgb": "piloté par le logiciel du fabricant (ex. AMD Adrenalin, logiciel de la carte mère)"}


def dossiers_temporaires() -> list:
    import os
    import tempfile
    from pathlib import Path

    return [Path(os.environ.get("TEMP") or tempfile.gettempdir())]


def dossiers_jeux() -> dict:
    import os
    from pathlib import Path

    pf86 = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
    data = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    return {"steam": [pf86 / "Steam" / "steamapps"], "epic": [data / "Epic" / "EpicGamesLauncher" / "Data" / "Manifests"]}
