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
