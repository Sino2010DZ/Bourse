"""Les 10 sections de Sentinelle et leur état de construction.

statut : « active » (point vert), « en_preparation » (point orange), « a_construire » (point gris).
"""

from __future__ import annotations

SECTIONS: list[dict] = [
    {"id": "materiel", "nom": "Matériel PC", "icone": "🔧", "commandant": "Commandant Tech", "statut": "a_construire"},
    {"id": "achats", "nom": "Prix & Achats", "icone": "💰", "commandant": "Commandant Achats", "statut": "a_construire"},
    {"id": "bourse", "nom": "Bourse", "icone": "📈", "commandant": "Commandant Finance", "statut": "en_preparation"},
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
