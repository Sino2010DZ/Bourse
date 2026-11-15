"""Suivi des prix Galaxus : ajouter un produit, relever son prix, garder l'historique, prévenir des baisses.

Rien n'est jamais acheté : Sentinelle ne fait que lire les prix et ouvrir la page Galaxus sur demande.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Callable, Protocol

from journal import FUSEAU
from outils.base_de_donnees import BaseDeDonnees
from outils.galaxus import ErreurGalaxus, FicheProduit, LecteurGalaxus, valider_lien

Notifier = Callable[[str, str], bool]


class Lecteur(Protocol):
    def lire(self, url: str) -> FicheProduit: ...


def _maintenant() -> datetime:
    return datetime.now(FUSEAU)


class SuiviPrix:
    def __init__(self, base: BaseDeDonnees, lecteur: Lecteur | None = None) -> None:
        self.base = base
        self.lecteur = lecteur or LecteurGalaxus()

    # ------------------------------------------------------------ lecture

    def fiche(self, ident: int) -> dict | None:
        p = self.base.produit(ident)
        if p is None:
            return None
        historique = self.base.historique_prix(ident)
        prix = [h["prix"] for h in historique]
        actuel = prix[-1] if prix else None
        precedent = prix[-2] if len(prix) >= 2 else None
        return {
            **p,
            "prix": actuel,
            "prix_precedent": precedent,
            "variation": None if actuel is None or precedent is None else round(actuel - precedent, 2),
            "prix_min": min(prix) if prix else None,
            "prix_max": max(prix) if prix else None,
            "premier_prix": prix[0] if prix else None,
            "dernier_releve": historique[-1]["horodatage"] if historique else None,
            "nb_releves": len(historique),
            "historique": historique,
        }

    def liste(self) -> list[dict]:
        return [self.fiche(p["id"]) for p in self.base.produits()]

    # ------------------------------------------------------------ actions

    async def ajouter(self, url: str, nom: str | None = None, prix: float | None = None) -> dict:
        lien, galaxus_id = valider_lien(url)
        if self.base.produit_par_galaxus_id(galaxus_id):
            raise ErreurGalaxus("deja_suivi", "Ce produit est déjà suivi.")
        nom_lien = lien.rstrip("/").rsplit("/", 1)[-1].rsplit("-", 1)[0].replace("-", " ").strip().capitalize()
        ident = self.base.ajouter_produit(galaxus_id, lien, (nom or "").strip()[:120] or nom_lien or "Produit Galaxus", _maintenant().isoformat(timespec="seconds"))
        if prix is not None:
            self.saisir(ident, prix)
            if nom:
                return self.fiche(ident)
        await self.relever(ident, garder_nom=bool(nom))
        return self.fiche(ident)

    def saisir(self, ident: int, prix: float) -> dict:
        """Prix noté à la main par Monsieur (si Galaxus refuse la lecture automatique)."""
        if not 0 < prix < 1_000_000:
            raise ValueError("Le prix doit être un nombre positif.")
        self.base.noter_prix(ident, _maintenant().isoformat(timespec="microseconds"), round(prix, 2), "manuel")
        return self.fiche(ident)

    async def relever(self, ident: int, garder_nom: bool = True) -> dict:
        """Lit le prix actuel sur Galaxus. Renvoie {ok, message, prix}."""
        p = self.base.produit(ident)
        if p is None:
            raise KeyError(ident)
        try:
            fiche = await asyncio.to_thread(self.lecteur.lire, p["url"])
        except ErreurGalaxus as e:
            self.base.modifier_produit(ident, statut=e.raison, message=str(e))
            return {"ok": False, "message": str(e), "prix": None}
        champs = {"statut": "ok", "message": ""}
        if not garder_nom or p["nom"] in ("", "Produit Galaxus"):
            champs["nom"] = fiche.nom
        self.base.modifier_produit(ident, **champs)
        self.base.noter_prix(ident, _maintenant().isoformat(timespec="microseconds"), fiche.prix, "auto")
        return {"ok": True, "message": "", "prix": fiche.prix}

    def supprimer(self, ident: int) -> None:
        self.base.supprimer_produit(ident)
        self.base.supprimer_alertes(f"prix:{ident}:")

    # ------------------------------------------------------------ alertes

    def verifier_baisse(self, ident: int, notifier: Notifier) -> str | None:
        """Si le dernier prix est plus bas que le précédent : notification (une seule fois par nouveau prix)."""
        f = self.fiche(ident)
        if not f or f["variation"] is None or f["variation"] >= 0:
            return None
        cle = f"prix:{ident}:{f['prix']:.2f}"
        if self.base.alerte_deja_envoyee(cle):
            return None
        baisse_pct = (1 - f["prix"] / f["prix_precedent"]) * 100
        message = (
            f"{f['nom']} : {f['prix']:.2f} CHF au lieu de {f['prix_precedent']:.2f} CHF "
            f"(−{abs(f['variation']):.2f} CHF, −{baisse_pct:.1f} %)."
        )
        if f["prix"] <= f["prix_min"]:
            message += " Plus bas prix jamais vu."
        notifier("Sentinelle — Baisse de prix Galaxus", message)
        self.base.noter_alerte(cle, _maintenant().isoformat(timespec="minutes"), message)
        return message

    async def relever_tous(self, notifier: Notifier) -> list[str]:
        alertes = []
        for p in self.base.produits():
            await self.relever(p["id"])
            message = self.verifier_baisse(p["id"], notifier)
            if message:
                alertes.append(message)
        return alertes

    async def relever_si_besoin(self, notifier: Notifier) -> list[str]:
        """Relève seulement les produits sans lecture automatique aujourd'hui (et seulement après 8h)."""
        maintenant = _maintenant()
        if maintenant.hour < 8:
            return []
        jour = maintenant.date().isoformat()
        alertes = []
        for p in self.base.produits():
            deja = any(h["source"] == "auto" and h["horodatage"].startswith(jour) for h in self.base.historique_prix(p["id"]))
            if deja or p["statut"] == "introuvable":
                continue
            await self.relever(p["id"])
            message = self.verifier_baisse(p["id"], notifier)
            if message:
                alertes.append(message)
        return alertes
