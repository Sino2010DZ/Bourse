"""Code propre à chaque système. Le reste de Sentinelle appelle seulement `systeme()`.

Chaque système (mac/, windows/) fournit exactement les mêmes fonctions :
- nom() -> str : nom lisible du système
- notifier(titre, message) -> bool : notification native
"""

from __future__ import annotations

import sys
from types import ModuleType


def systeme() -> ModuleType:
    if sys.platform == "darwin":
        from plateforme.mac import systeme as module
    elif sys.platform.startswith("win"):
        from plateforme.windows import systeme as module
    else:  # Linux : utilisé seulement pour les tests
        from plateforme.windows import systeme as module
    return module
