"""Tâches automatiques (APScheduler).

- Cours de bourse : toutes les 15 minutes, du lundi au vendredi, de 9h à 22h (heure de Zurich),
  ce qui couvre la bourse suisse, Londres et New York. Aucun appel à Claude : c'est gratuit.
  Si une action bouge plus que le seuil du radar, une notification Mac est envoyée (une fois par jour et par action).
- Prix Galaxus (8h) et briefing du matin (7h30) : ajoutés avec leurs sections.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from journal import FUSEAU
from outils.base_de_donnees import BaseDeDonnees
from outils.bourse import ServiceBourse
from outils.portefeuille import Portefeuille

Notifier = Callable[[str, str], bool]


async def releve_bourse(bourse: ServiceBourse, portefeuille: Portefeuille, base: BaseDeDonnees, notifier: Notifier) -> list[str]:
    """Relève les cours, les enregistre et prévient en cas de gros mouvement. Renvoie les alertes envoyées."""
    pf = portefeuille.lire()
    noms = {p["ticker"]: p["nom"] for p in pf["positions"]}
    tickers = list(dict.fromkeys(list(noms) + pf["radar"]))
    maintenant = datetime.now(FUSEAU).isoformat(timespec="minutes")
    alertes = []
    for f in await bourse.fiches(tickers, forcer=True):
        if not f.get("disponible"):
            continue
        base.noter_cours(f["ticker"], maintenant, f["prix"], f["variation_jour_pct"])
        variation = f["variation_jour_pct"]
        if variation is None or abs(variation) < pf["seuil_radar_pct"]:
            continue
        cle = f"radar:{f['ticker']}:{f['date']}"
        if base.alerte_deja_envoyee(cle):
            continue
        nom = noms.get(f["ticker"], f["ticker"])
        sens = "monte" if variation > 0 else "baisse"
        message = f"{nom} {sens} de {abs(variation):.1f} % aujourd'hui (cours : {f['prix']:g})."
        notifier("Sentinelle — Radar bourse", message)
        base.noter_alerte(cle, maintenant, message)
        alertes.append(message)
    return alertes


def creer_planificateur(bourse: ServiceBourse, portefeuille: Portefeuille, base: BaseDeDonnees, notifier: Notifier) -> AsyncIOScheduler:
    planif = AsyncIOScheduler(timezone=FUSEAU)
    planif.add_job(
        releve_bourse,
        CronTrigger(day_of_week="mon-fri", hour="9-21", minute="*/15", timezone=FUSEAU),
        args=[bourse, portefeuille, base, notifier],
        id="cours_bourse",
        max_instances=1,
        coalesce=True,
    )
    # Un premier relevé au démarrage, pour que la carte « Mes actions » soit prête tout de suite.
    planif.add_job(releve_bourse, args=[bourse, portefeuille, base, notifier], id="cours_demarrage")
    return planif
