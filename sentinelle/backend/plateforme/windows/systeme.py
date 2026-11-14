"""Fonctions Windows (complétées lors de la dernière phase)."""

from __future__ import annotations

import platform


def nom() -> str:
    return f"{platform.system()} {platform.release()}".strip()


def notifier(titre: str, message: str) -> bool:
    # Notifications Windows : prévues pour la phase Windows.
    return False
