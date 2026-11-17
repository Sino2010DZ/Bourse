"""Tâches automatiques (APScheduler).

- Cours de bourse : toutes les 15 minutes, du lundi au vendredi, de 9h à 22h (heure de Zurich),
  ce qui couvre la bourse suisse, Londres et New York. Aucun appel à Claude : c'est gratuit.
  Si une action bouge plus que le seuil du radar, une notification Mac est envoyée (une fois par jour et par action).
- Prix Galaxus : chaque jour à 8h, une seule lecture par produit ; notification si le prix baisse.
- Rappels : vérifiés chaque minute, notification à l'heure prévue.
- Briefing du matin à 7h30 (rangé dans l'historique + notification).
- Coup d'envoi : notification ~1 h avant les qualifications, le sprint et la course de F1.
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


async def briefing_du_matin(secretariat, base: BaseDeDonnees, journal, notifier: Notifier) -> str | None:
    """7h30 : le briefing est écrit, rangé dans l'historique des discussions, et annoncé par une notification."""
    from journal import Trace

    if not secretariat.reglages.cle_presente:
        return None
    texte = await secretariat.briefing(Trace(journal))
    if not texte:
        return None
    maintenant = datetime.now(FUSEAU)
    ident = base.creer_discussion(f"Briefing du {maintenant:%d.%m.%Y}", maintenant.isoformat(timespec="seconds"))
    base.ajouter_message(ident, "chef", texte, maintenant.isoformat(timespec="seconds"), ["Briefing"], {})
    notifier("Sentinelle — Briefing du matin", texte[:220])
    return texte


async def coup_d_envoi(f1, base: BaseDeDonnees, notifier: Notifier, maintenant: datetime | None = None) -> list[str]:
    """Une notification environ 1 heure avant les qualifications, le sprint et la course de F1 (une seule fois)."""
    try:
        course = await f1.prochaine()
    except Exception:
        return []
    if not course:
        return []
    maintenant = maintenant or datetime.now(FUSEAU)
    envoyees = []
    for seance in course["seances"]:
        if seance["nom"] not in ("Qualifications", "Sprint", "Course"):
            continue
        debut = datetime.fromisoformat(seance["debut"])
        minutes = (debut - maintenant).total_seconds() / 60
        cle = f"f1:{course['manche']}:{seance['nom']}"
        if 0 < minutes <= 75 and not base.alerte_deja_envoyee(cle):
            message = f"{seance['nom']} du {course['nom']} dans {int(minutes)} min ({debut:%H:%M}, heure de Zurich)."
            notifier("Sentinelle — Coup d'envoi F1", message)
            base.noter_alerte(cle, maintenant.isoformat(timespec="minutes"), message)
            envoyees.append(message)
    return envoyees


async def verifier_rappels(base: BaseDeDonnees, notifier: Notifier, maintenant: datetime | None = None) -> list[str]:
    """Chaque minute : notification pour les rappels arrivés à échéance (une seule fois chacun)."""
    maintenant = maintenant or datetime.now(FUSEAU)
    envoyes = []
    for r in base.rappels():
        if r["notifie"] or datetime.fromisoformat(r["echeance"]) > maintenant:
            continue
        notifier("Sentinelle — Rappel", r["texte"])
        base.marquer_rappel(r["id"], notifie=True)
        envoyes.append(r["texte"])
    return envoyes


def creer_planificateur(
    bourse: ServiceBourse, portefeuille: Portefeuille, base: BaseDeDonnees, notifier: Notifier, suivi=None,
    secretariat=None, journal=None, f1=None,
) -> AsyncIOScheduler:
    planif = AsyncIOScheduler(timezone=FUSEAU)
    planif.add_job(verifier_rappels, CronTrigger(minute="*", timezone=FUSEAU), args=[base, notifier],
                   id="rappels", max_instances=1, coalesce=True)
    if secretariat is not None and journal is not None:
        planif.add_job(briefing_du_matin, CronTrigger(hour=7, minute=30, timezone=FUSEAU),
                       args=[secretariat, base, journal, notifier], id="briefing", max_instances=1, coalesce=True)
    if f1 is not None:
        planif.add_job(coup_d_envoi, CronTrigger(minute="*/15", timezone=FUSEAU),
                       args=[f1, base, notifier], id="coup_d_envoi", max_instances=1, coalesce=True)
    if suivi is not None:
        # Prix Galaxus : une fois par jour à 8h (heure de Zurich), une requête par produit.
        planif.add_job(
            suivi.relever_tous,
            CronTrigger(hour=8, minute=0, timezone=FUSEAU),
            args=[notifier],
            id="prix_galaxus",
            max_instances=1,
            coalesce=True,
        )
        # Sentinelle fermée à 8h ? Les produits pas encore relevés aujourd'hui le sont au démarrage.
        planif.add_job(suivi.relever_si_besoin, args=[notifier], id="prix_demarrage")
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
