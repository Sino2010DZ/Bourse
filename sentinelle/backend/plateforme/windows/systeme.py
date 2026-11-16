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
