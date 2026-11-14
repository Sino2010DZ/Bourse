"""Journal de bord : chaque échange est noté dans data/journal/AAAA-MM-JJ.jsonl.

Une ligne = un échange : qui l'a traité, combien de temps, combien de tokens et quel coût.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("Europe/Zurich")


@dataclass
class Entree:
    qui: str                      # ex. « grand_chef », plus tard « finance/trader »
    demande: str
    reponse: str
    modele: str
    duree_ms: int
    tokens_entree: int = 0
    tokens_sortie: int = 0
    cout_usd: float = 0.0
    erreur: bool = False
    horodatage: str = field(default_factory=lambda: datetime.now(FUSEAU).isoformat(timespec="seconds"))


class Journal:
    def __init__(self, dossier_donnees: Path) -> None:
        self.dossier = dossier_donnees / "journal"
        self.dossier.mkdir(parents=True, exist_ok=True)

    def _fichier(self, jour: datetime | None = None) -> Path:
        jour = jour or datetime.now(FUSEAU)
        return self.dossier / f"{jour:%Y-%m-%d}.jsonl"

    def noter(self, entree: Entree) -> None:
        with self._fichier().open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entree), ensure_ascii=False) + "\n")

    def entrees_du_jour(self) -> list[dict]:
        fichier = self._fichier()
        if not fichier.exists():
            return []
        lignes = fichier.read_text(encoding="utf-8").splitlines()
        return [json.loads(l) for l in lignes if l.strip()]

    def consommation_du_jour(self) -> dict:
        entrees = self.entrees_du_jour()
        return {
            "echanges": len(entrees),
            "tokens_entree": sum(e["tokens_entree"] for e in entrees),
            "tokens_sortie": sum(e["tokens_sortie"] for e in entrees),
            "cout_usd": round(sum(e["cout_usd"] for e in entrees), 4),
        }


class Trace:
    """Suit une demande de Monsieur à travers tous les niveaux (Grand Chef, commandants, agents).

    Chaque appel à Claude est noté dans le journal, et la trace additionne tokens et coût.
    """

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.etapes: list[dict] = []

    def noter(self, qui: str, demande: str, reponse) -> None:
        entree = Entree(
            qui=qui,
            demande=demande,
            reponse=reponse.texte,
            modele=reponse.modele,
            duree_ms=reponse.duree_ms,
            tokens_entree=reponse.tokens_entree,
            tokens_sortie=reponse.tokens_sortie,
            cout_usd=reponse.cout_usd,
            erreur=reponse.erreur,
        )
        self.journal.noter(entree)
        self.etapes.append(
            {
                "qui": qui,
                "duree_ms": reponse.duree_ms,
                "tokens": reponse.tokens_entree + reponse.tokens_sortie,
                "cout_usd": reponse.cout_usd,
                "erreur": reponse.erreur,
            }
        )

    def total(self) -> dict:
        return {
            "appels": len(self.etapes),
            "tokens": sum(e["tokens"] for e in self.etapes),
            "cout_usd": round(sum(e["cout_usd"] for e in self.etapes), 6),
            "intervenants": [e["qui"] for e in self.etapes],
        }


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def maintenant_texte() -> str:
    """Ex. « samedi 14.11.2026, 18:05 (heure de Zurich) »."""
    m = datetime.now(FUSEAU)
    return f"{JOURS[m.weekday()]} {m:%d.%m.%Y, %H:%M} (heure de Zurich)"
