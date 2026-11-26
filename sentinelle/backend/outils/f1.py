"""Formule 1 : calendrier, résultats et classements via l'API publique Jolpica (sans clé)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Callable
from zoneinfo import ZoneInfo

from outils.web_public import lire_json

BASE = "https://api.jolpi.ca/ergast/f1"
ZURICH = ZoneInfo("Europe/Zurich")
SEANCES = {
    "FirstPractice": "Essais libres 1", "SecondPractice": "Essais libres 2", "ThirdPractice": "Essais libres 3",
    "SprintQualifying": "Qualifications sprint", "Sprint": "Sprint", "Qualifying": "Qualifications",
}


def _heure(seance: dict) -> datetime | None:
    if not seance.get("date"):
        return None
    texte = f"{seance['date']}T{seance.get('time', '00:00:00Z')}".replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(texte).astimezone(ZURICH)
    except ValueError:
        return None


def seances_course(course: dict) -> list[dict]:
    """Toutes les séances d'un week-end, à l'heure de Zurich, dans l'ordre."""
    seances = []
    for cle, nom in SEANCES.items():
        if cle in course:
            h = _heure(course[cle])
            if h:
                seances.append({"nom": nom, "debut": h.isoformat()})
    h = _heure(course)
    if h:
        seances.append({"nom": "Course", "debut": h.isoformat()})
    return sorted(seances, key=lambda s: s["debut"])


def prochaine_course(calendrier: dict, maintenant: datetime | None = None) -> dict | None:
    maintenant = maintenant or datetime.now(timezone.utc)
    for course in calendrier["MRData"]["RaceTable"]["Races"]:
        h = _heure(course)
        if h and h >= maintenant - timedelta(hours=2):   # une course en cours compte encore
            lieu = course["Circuit"]["Location"]
            return {
                "manche": int(course["round"]),
                "nom": course["raceName"],
                "circuit": course["Circuit"]["circuitName"],
                "lieu": f"{lieu.get('locality', '')}, {lieu.get('country', '')}".strip(", "),
                "depart": h.isoformat(),
                "seances": seances_course(course),
            }
    return None


def resultats(brut: dict) -> dict | None:
    courses = brut["MRData"]["RaceTable"]["Races"]
    if not courses:
        return None
    c = courses[-1]
    return {
        "nom": c["raceName"],
        "date": c["date"],
        "classement": [
            {
                "position": int(r["position"]),
                "pilote": f"{r['Driver']['givenName']} {r['Driver']['familyName']}",
                "equipe": r["Constructor"]["name"],
                "points": float(r["points"]),
                "statut": r.get("status", ""),
            }
            for r in c.get("Results", [])[:10]
        ],
    }


def classement_pilotes(brut: dict) -> list[dict]:
    listes = brut["MRData"]["StandingsTable"]["StandingsLists"]
    if not listes:
        return []
    return [
        {
            "position": int(p.get("position") or p.get("positionText") or 0),
            "pilote": f"{p['Driver']['givenName']} {p['Driver']['familyName']}",
            "equipe": p["Constructors"][0]["name"] if p.get("Constructors") else "",
            "points": float(p["points"]),
            "victoires": int(p["wins"]),
        }
        for p in listes[0]["DriverStandings"][:10]
    ]


def classement_equipes(brut: dict) -> list[dict]:
    listes = brut["MRData"]["StandingsTable"]["StandingsLists"]
    if not listes:
        return []
    return [
        {"position": int(p.get("position") or 0), "equipe": p["Constructor"]["name"], "points": float(p["points"]), "victoires": int(p["wins"])}
        for p in listes[0]["ConstructorStandings"][:10]
    ]


class ServiceF1:
    def __init__(self, lecteur: Callable[[str], dict] | None = None) -> None:
        self.lecteur = lecteur or (lambda url: lire_json(url, duree_cache=60 * 60))

    async def _lire(self, chemin: str) -> dict:
        return await asyncio.to_thread(self.lecteur, f"{BASE}/{chemin}")

    async def prochaine(self, maintenant: datetime | None = None) -> dict | None:
        return prochaine_course(await self._lire("current.json"), maintenant)

    async def dernier_resultat(self) -> dict | None:
        return resultats(await self._lire("current/last/results.json"))

    async def classements(self) -> dict:
        return {
            "pilotes": classement_pilotes(await self._lire("current/driverstandings.json")),
            "equipes": classement_equipes(await self._lire("current/constructorstandings.json")),
        }
