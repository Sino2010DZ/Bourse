"""Serveur local de Sentinelle.

Il tourne uniquement sur votre ordinateur (adresse 127.0.0.1) : rien n'est accessible depuis Internet.
L'interface (fenêtre Tauri ou navigateur) lui envoie vos messages, il les transmet au Grand Chef.

Lancement : python backend/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config import DOSSIER_UI, Reglages, charger_reglages
from grand_chef import Cerveau, GrandChef
from journal import Journal
from plateforme import systeme
from sections import SECTIONS

VERSION = "0.1.0"

# Origines de la fenêtre Tauri (macOS : tauri://localhost ; Windows : http(s)://tauri.localhost)
ORIGINES_TAURI = ["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"]


class MessageEntrant(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


def creer_app(reglages: Reglages | None = None, cerveau: Cerveau | None = None) -> FastAPI:
    reglages = reglages or charger_reglages()
    journal = Journal(reglages.dossier_donnees)
    chef = GrandChef(reglages, journal, cerveau)

    app = FastAPI(title="Sentinelle", version=VERSION)
    # Refuse les requêtes qui ne visent pas explicitement cet ordinateur (protection « DNS rebinding »).
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ORIGINES_TAURI + [f"http://127.0.0.1:{reglages.port}", f"http://localhost:{reglages.port}"],
        allow_methods=["GET", "POST"],
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
        }

    @app.get("/api/sections")
    def sections() -> list[dict]:
        return SECTIONS

    @app.post("/api/chat")
    async def chat(entree: MessageEntrant) -> dict:
        r = await chef.repondre(entree.message)
        return {
            "reponse": r.texte,
            "erreur": r.erreur,
            "modele": r.modele,
            "duree_ms": r.duree_ms,
            "tokens_entree": r.tokens_entree,
            "tokens_sortie": r.tokens_sortie,
            "cout_usd": r.cout_usd,
            "consommation": journal.consommation_du_jour(),
        }

    @app.get("/api/consommation")
    def consommation() -> dict:
        return journal.consommation_du_jour()

    # L'interface est aussi servie ici : http://127.0.0.1:8765 marche dans un navigateur.
    if DOSSIER_UI.exists():
        app.mount("/", StaticFiles(directory=DOSSIER_UI, html=True), name="ui")

    return app


if __name__ == "__main__":
    import uvicorn

    r = charger_reglages()
    print(f"Sentinelle en ligne sur http://127.0.0.1:{r.port}  (Ctrl+C pour arrêter)")
    uvicorn.run(creer_app(r), host="127.0.0.1", port=r.port, log_level="warning")
