"""Les 10 sections de Sentinelle et leur état de construction.

statut : « active » (point vert), « en_preparation » (point orange), « a_construire » (point gris).
"""

from __future__ import annotations

SECTIONS: list[dict] = [
    {"id": "materiel", "nom": "Matériel PC", "icone": "🔧", "commandant": "Commandant Tech", "statut": "a_construire"},
    {"id": "achats", "nom": "Prix & Achats", "icone": "💰", "commandant": "Commandant Achats", "statut": "active"},
    {"id": "bourse", "nom": "Bourse", "icone": "📈", "commandant": "Commandant Finance", "statut": "active"},
    {"id": "renseignement", "nom": "Renseignement", "icone": "🌐", "commandant": "Commandant Veille", "statut": "a_construire"},
    {"id": "sport", "nom": "Sport", "icone": "🏁", "commandant": "Commandant Stade", "statut": "a_construire"},
    {"id": "divertissement", "nom": "Divertissement", "icone": "🎬", "commandant": "Commandant Détente", "statut": "a_construire"},
    {"id": "jeux", "nom": "Jeux vidéo", "icone": "🎮", "commandant": "Commandant Gaming", "statut": "a_construire"},
    {"id": "entretien", "nom": "Entretien", "icone": "🧹", "commandant": "Commandant Maintenance", "statut": "a_construire"},
    {"id": "organisation", "nom": "Organisation", "icone": "📅", "commandant": "Commandant Secrétariat", "statut": "a_construire"},
    {"id": "creation", "nom": "Création", "icone": "🚀", "commandant": "Commandant Atelier", "statut": "a_construire"},
]


def sections_actives() -> list[dict]:
    return [s for s in SECTIONS if s["statut"] == "active"]


# Les 50 agents (5 par section), dans l'ordre de SENTINELLE.md.
# Un agent est « actif » quand sa fiche .md existe dans agents/<section>/.
AGENTS: dict[str, list[tuple[str, str]]] = {
    "materiel": [("conseiller", "Conseiller"), ("compatibilite", "Compatibilité"), ("testeur", "Testeur"), ("pilotes", "Pilotes"), ("performance", "Performance")],
    "achats": [("chasseur", "Chasseur"), ("historien", "Historien"), ("alarme", "Alarme"), ("comparateur", "Comparateur"), ("black_friday", "Black Friday")],
    "bourse": [("trader", "Trader"), ("journaliste", "Journaliste"), ("comptable", "Comptable"), ("analyste", "Analyste"), ("radar", "Radar")],
    "renseignement": [("eclaireur", "Éclaireur"), ("resumeur", "Résumeur"), ("verificateur", "Vérificateur"), ("traducteur", "Traducteur"), ("archiviste", "Archiviste")],
    "sport": [("stand_f1", "Stand F1"), ("courtside", "Courtside"), ("tribune", "Tribune"), ("coup_d_envoi", "Coup d'envoi"), ("statisticien", "Statisticien")],
    "divertissement": [("dj", "DJ"), ("decouvreur", "Découvreur"), ("critique", "Critique"), ("sorties", "Sorties"), ("geneve_sorties", "Genève Sorties")],
    "jeux": [("promo", "Promo"), ("patch", "Patch"), ("mods", "Mods"), ("coach", "Coach"), ("launcher", "Launcher")],
    "entretien": [("rangeur", "Rangeur"), ("nettoyeur", "Nettoyeur"), ("sauvegarde", "Sauvegarde"), ("thermometre", "Thermomètre"), ("eclairagiste", "Éclairagiste")],
    "organisation": [("agenda", "Agenda"), ("rappels", "Rappels"), ("courrier", "Courrier"), ("meteo", "Météo"), ("briefing", "Briefing")],
    "creation": [("codeur", "Codeur"), ("designer", "Designer"), ("idees", "Idées"), ("debugueur", "Débugueur"), ("chef_de_projet", "Chef de projet")],
}


def nom_agent(qui: str) -> str | None:
    """« bourse/trader » -> « Trader » (None pour le Grand Chef et les commandants)."""
    section, _, ident = qui.partition("/")
    return dict(AGENTS.get(section, [])).get(ident)
