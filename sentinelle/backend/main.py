"""Serveur local de Sentinelle.

Il tourne uniquement sur votre ordinateur (adresse 127.0.0.1) : rien n'est accessible depuis Internet.
L'interface (fenêtre Tauri ou navigateur) lui envoie vos messages, il les transmet au Grand Chef.

Lancement : python backend/main.py
"""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import datetime
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cerveau import Cerveau, cerveau_claude
from commandants.achats import CommandantAchats
from commandants.finance import CommandantFinance
from config import DOSSIER_UI, Reglages, charger_reglages, cle_valide, enregistrer_cle
from grand_chef import GrandChef
from journal import FUSEAU, Journal
from outils.base_de_donnees import BaseDeDonnees
from outils.bourse import ServiceBourse, Source
from outils.galaxus import ErreurGalaxus
from outils.portefeuille import ErreurPortefeuille, Portefeuille
from outils.suivi_prix import Lecteur, SuiviPrix
from plateforme import systeme
from outils.preferences import ErreurPreferences, Preferences
from sections import AGENTS, SECTIONS, nom_agent
from agents.chargeur import agents_de_section

VERSION = "0.2.0"

# Origines de la fenêtre Tauri (macOS : tauri://localhost ; Windows : http(s)://tauri.localhost)
ORIGINES_TAURI = ["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"]


class MessageEntrant(BaseModel):
    message: str = Field(default="", max_length=8000)
    discussion_id: int | None = None
    section: str | None = Field(default=None, max_length=40)
    regenerer: bool = False   # « Régénérer » : refaire la dernière réponse


class ProduitEntrant(BaseModel):
    url: str = Field(min_length=10, max_length=500)
    nom: str | None = Field(default=None, max_length=120)
    prix: float | None = Field(default=None, gt=0, lt=1_000_000)


class PrixEntrant(BaseModel):
    prix: float = Field(gt=0, lt=1_000_000)


class CleEntrante(BaseModel):
    cle: str = Field(min_length=1, max_length=300)


def creer_app(
    reglages: Reglages | None = None,
    cerveau: Cerveau | None = None,
    source_bourse: Source | None = None,
    planificateur: bool = True,
    lecteur_galaxus: Lecteur | None = None,
) -> FastAPI:
    reglages = reglages or charger_reglages()
    cerveau = cerveau or cerveau_claude
    journal = Journal(reglages.dossier_donnees)
    base = BaseDeDonnees(reglages.dossier_donnees)
    portefeuille = Portefeuille(reglages.dossier_donnees)
    preferences = Preferences(reglages.dossier_donnees)
    bourse = ServiceBourse(source_bourse)
    suivi = SuiviPrix(base, lecteur_galaxus)
    commandants = {
        "achats": CommandantAchats(reglages, cerveau, suivi, base),
        "bourse": CommandantFinance(reglages, cerveau, bourse, portefeuille),
    }
    chef = GrandChef(reglages, journal, cerveau, commandants)

    @asynccontextmanager
    async def cycle_de_vie(app: FastAPI):
        planif = None
        if planificateur:
            from planificateur import creer_planificateur

            planif = creer_planificateur(bourse, portefeuille, base, systeme().notifier, suivi)
            planif.start()
        yield
        if planif:
            planif.shutdown(wait=False)

    app = FastAPI(title="Sentinelle", version=VERSION, lifespan=cycle_de_vie)
    # Refuse les requêtes qui ne visent pas explicitement cet ordinateur (protection « DNS rebinding »).
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ORIGINES_TAURI + [f"http://127.0.0.1:{reglages.port}", f"http://localhost:{reglages.port}"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/sante")
    def sante() -> dict:
        return {
            "statut": "en_ligne",
            "version": VERSION,
            "systeme": systeme().nom(),
            "cle_api": reglages.cle_presente,
            "modele_grand_chef": reglages.modele_grand_chef,
            "modele_agents": reglages.modele_agents,
        }

    @app.post("/api/cle")
    def definir_cle(entree: CleEntrante) -> dict:
        """Enregistre la clé API collée dans l'interface (au premier lancement de l'app)."""
        nonlocal reglages
        cle = entree.cle.strip()
        if not cle_valide(cle):
            raise HTTPException(status_code=422, detail="Cette clé ne ressemble pas à une clé Anthropic (elle commence par sk-ant-).")
        enregistrer_cle(cle, reglages.dossier_donnees)
        reglages = replace(reglages, cle_api=cle)
        chef.reglages = reglages
        for c in commandants.values():
            c.reglages = reglages
        return {"cle_api": True}

    @app.get("/api/sections")
    def sections() -> list[dict]:
        return SECTIONS

    @app.post("/api/chat")
    async def chat(entree: MessageEntrant) -> dict:
        maintenant = datetime.now(FUSEAU).isoformat(timespec="seconds")
        discussion_id = entree.discussion_id
        if discussion_id is not None and base.discussion(discussion_id) is None:
            raise HTTPException(status_code=404, detail="Discussion introuvable.")

        if entree.regenerer:
            if discussion_id is None:
                raise HTTPException(status_code=422, detail="Rien à régénérer.")
            questions = [m for m in base.discussion(discussion_id)["messages"] if m["role"] == "moi"]
            if not questions:
                raise HTTPException(status_code=422, detail="Rien à régénérer.")
            base.supprimer_dernier_message_chef(discussion_id)
            message = questions[-1]["texte"]
        else:
            message = entree.message.strip()
            if not message:
                raise HTTPException(status_code=422, detail="Message vide.")
            if discussion_id is None:
                discussion_id = base.creer_discussion(message, maintenant)
            base.ajouter_message(discussion_id, "moi", message, maintenant)

        res = await chef.repondre(message, historique=base.echanges(discussion_id), section=entree.section)
        r, total = res.reponse, res.trace.total()
        agents = list(dict.fromkeys(n for n in map(nom_agent, total["intervenants"]) if n))
        meta = {"duree_ms": r.duree_ms, "tokens": total["tokens"], "cout_usd": total["cout_usd"], "erreur": r.erreur}
        message_id = base.ajouter_message(
            discussion_id, "chef", r.texte, datetime.now(FUSEAU).isoformat(timespec="seconds"), agents, meta
        )
        return {
            "reponse": r.texte,
            "erreur": r.erreur,
            "modele": r.modele,
            "duree_ms": r.duree_ms,
            "tokens": total["tokens"],
            "cout_usd": total["cout_usd"],
            "intervenants": total["intervenants"],
            "agents": agents,
            "discussion_id": discussion_id,
            "message_id": message_id,
            "consommation": consommation(),
        }

    @app.get("/api/discussions")
    def liste_discussions(q: str = "") -> list[dict]:
        return base.discussions(q[:100])

    @app.get("/api/discussions/{ident}")
    def lire_discussion(ident: int) -> dict:
        d = base.discussion(ident)
        if d is None:
            raise HTTPException(status_code=404, detail="Discussion introuvable.")
        return d

    @app.get("/api/preferences")
    def lire_preferences() -> dict:
        return preferences.lire()

    @app.put("/api/preferences")
    def modifier_preferences(donnees: dict) -> dict:
        try:
            return preferences.modifier(donnees)
        except ErreurPreferences as e:
            raise HTTPException(status_code=422, detail=str(e)) from None

    @app.get("/api/agents")
    def agents_50() -> list[dict]:
        resultat = []
        for s in SECTIONS:
            actifs = {a.id for a in agents_de_section(s["id"])}
            for ident, nom in AGENTS[s["id"]]:
                resultat.append({"section": s["id"], "id": ident, "nom": nom, "actif": ident in actifs})
        return resultat

    @app.get("/api/bourse/graphique")
    async def graphique(ticker: str, periode: str = "1M") -> dict:
        if ticker not in portefeuille.tickers():
            raise HTTPException(status_code=404, detail="Action absente du portefeuille.")
        try:
            return await bourse.graphique(ticker, periode)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from None

    @app.get("/api/consommation")
    def consommation() -> dict:
        return {**journal.consommation_du_jour(), "budget_jour_usd": preferences.lire()["budget_jour_usd"]}

    @app.get("/api/bourse/mes-actions")
    async def mes_actions() -> dict:
        return await bourse.positions(portefeuille.lire())

    @app.get("/api/portefeuille")
    def lire_portefeuille() -> dict:
        return portefeuille.lire()

    @app.put("/api/portefeuille")
    def modifier_portefeuille(donnees: dict) -> dict:
        try:
            return portefeuille.enregistrer(donnees)
        except ErreurPortefeuille as e:
            raise HTTPException(status_code=422, detail=str(e)) from None

    # ------------------------------------------------------------ Prix & Achats (Galaxus)

    def _fiche_ou_404(ident: int) -> dict:
        f = suivi.fiche(ident)
        if f is None:
            raise HTTPException(status_code=404, detail="Produit introuvable.")
        return f

    @app.get("/api/produits")
    def produits() -> list[dict]:
        return suivi.liste()

    @app.post("/api/produits", status_code=201)
    async def ajouter_produit(entree: ProduitEntrant) -> dict:
        try:
            return await suivi.ajouter(entree.url, entree.nom, entree.prix)
        except ErreurGalaxus as e:
            raise HTTPException(status_code=422, detail=str(e)) from None

    @app.post("/api/produits/{ident}/prix")
    def saisir_prix(ident: int, entree: PrixEntrant) -> dict:
        _fiche_ou_404(ident)
        suivi.saisir(ident, entree.prix)
        alerte = suivi.verifier_baisse(ident, systeme().notifier)
        return {**suivi.fiche(ident), "alerte": alerte}

    @app.post("/api/produits/{ident}/relever")
    async def relever_prix(ident: int) -> dict:
        _fiche_ou_404(ident)
        resultat = await suivi.relever(ident)
        alerte = suivi.verifier_baisse(ident, systeme().notifier) if resultat["ok"] else None
        return {**suivi.fiche(ident), "releve": resultat, "alerte": alerte}

    @app.delete("/api/produits/{ident}")
    def supprimer_produit(ident: int, confirmer: bool = False) -> dict:
        _fiche_ou_404(ident)
        if not confirmer:   # règle de sécurité : jamais de suppression sans le bouton « Confirmer »
            raise HTTPException(status_code=409, detail="Confirmation requise.")
        suivi.supprimer(ident)
        return {"supprime": ident}

    @app.post("/api/produits/{ident}/ouvrir")
    def ouvrir_produit(ident: int) -> dict:
        """Ouvre la page Galaxus du produit dans le navigateur (aucun achat n'est fait)."""
        f = _fiche_ou_404(ident)
        return {"ouvert": systeme().ouvrir_lien(f["url"])}

    @app.get("/api/alertes")
    def alertes() -> list[dict]:
        return base.dernieres_alertes()

    # L'interface est aussi servie ici : http://127.0.0.1:8765 marche dans un navigateur.
    if DOSSIER_UI.exists():
        app.mount("/", StaticFiles(directory=DOSSIER_UI, html=True), name="ui")

    return app


if __name__ == "__main__":
    import uvicorn

    r = charger_reglages()
    print(f"Sentinelle en ligne sur http://127.0.0.1:{r.port}  (Ctrl+C pour arrêter)")
    uvicorn.run(creer_app(r), host="127.0.0.1", port=r.port, log_level="warning")
