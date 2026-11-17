"""Agenda en lecture seule, depuis le lien iCal secret de Monsieur (Google, Outlook ou iCloud).

Le lien ne permet que de LIRE : Sentinelle ne peut ni créer, ni modifier, ni supprimer de rendez-vous.
"""

from __future__ import annotations

import asyncio
import time
import urllib.request
from datetime import date, datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

ZURICH = ZoneInfo("Europe/Zurich")


def telecharger_ical(lien: str) -> bytes:
    requete = urllib.request.Request(lien, headers={"User-Agent": "Sentinelle/0.6 (agenda personnel)"})
    for essai in range(3):
        try:
            with urllib.request.urlopen(requete, timeout=20) as r:
                return r.read(10_000_000)
        except OSError:
            if essai == 2:
                raise
            time.sleep(1.5 * (essai + 1))
    return b""


def evenements(contenu: bytes, debut: datetime, fin: datetime) -> list[dict]:
    """Rendez-vous entre debut et fin (rendez-vous répétés compris), à l'heure de Zurich."""
    import icalendar
    import recurring_ical_events

    calendrier = icalendar.Calendar.from_ical(contenu)
    resultat = []
    for ev in recurring_ical_events.of(calendrier).between(debut, fin):
        d = ev.get("DTSTART").dt
        f = ev.get("DTEND").dt if ev.get("DTEND") else None
        journee = isinstance(d, date) and not isinstance(d, datetime)
        if not journee:
            d = (d if d.tzinfo else d.replace(tzinfo=ZURICH)).astimezone(ZURICH)
            f = (f if f.tzinfo else f.replace(tzinfo=ZURICH)).astimezone(ZURICH) if isinstance(f, datetime) else None
        resultat.append({
            "titre": str(ev.get("SUMMARY", "(sans titre)")),
            "debut": d.isoformat(),
            "fin": f.isoformat() if f else None,
            "toute_la_journee": journee,
            "lieu": str(ev.get("LOCATION")) if ev.get("LOCATION") else None,
        })
    return sorted(resultat, key=lambda e: e["debut"])


class ServiceAgenda:
    def __init__(self, lien: Callable[[], str | None], telecharger: Callable[[str], bytes] | None = None) -> None:
        self.lien = lien
        self.telecharger = telecharger or telecharger_ical
        self._cache: tuple[float, str, bytes] | None = None

    async def prochains(self, jours: int = 7) -> dict:
        lien = self.lien()
        if not lien:
            return {"connecte": False, "info": "Agenda non connecté : Monsieur peut coller son lien iCal secret dans Réglages › Comptes."}
        if self._cache and self._cache[1] == lien and time.monotonic() - self._cache[0] < 600:
            contenu = self._cache[2]
        else:
            contenu = await asyncio.to_thread(self.telecharger, lien)
            self._cache = (time.monotonic(), lien, contenu)
        maintenant = datetime.now(ZURICH)
        debut = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
        return {"connecte": True, "evenements": await asyncio.to_thread(evenements, contenu, debut, debut + timedelta(days=jours))}
