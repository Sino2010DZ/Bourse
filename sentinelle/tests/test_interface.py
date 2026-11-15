"""Tests de l'interface « 20 thèmes » : discussions, préférences, agents, graphique, thèmes."""

import json
import re
from pathlib import Path

import pytest

UI = Path(__file__).resolve().parent.parent / "app" / "ui"
CLES = ["fond", "panneau", "surface", "relief", "texte", "texte2", "texte3", "ligne", "accent", "surAccent", "accentTexte"]
OPTIONS = {
    "police": {"serif", "inter", "manrope", "plex", "grotesk", "mono", "source"},
    "messages": {"plat", "bulles"},
    "saisie": {"boite", "pilule", "flottante"},
    "droite": {"cartes", "liste"},
    "gauche": {"complet", "icones"},
}

# ---------------------------------------------------------------- discussions


def test_historique_des_discussions(client):
    r1 = client.post("/api/chat", json={"message": "Bonjour"}).json()
    d = r1["discussion_id"]
    client.post("/api/chat", json={"message": "Merci", "discussion_id": d})
    client.post("/api/chat", json={"message": "Autre sujet"})
    liste = client.get("/api/discussions").json()
    assert [x["titre"] for x in liste] == ["Autre sujet", "Bonjour"]
    messages = client.get(f"/api/discussions/{d}").json()["messages"]
    assert [m["role"] for m in messages] == ["moi", "chef", "moi", "chef"]
    assert [x["titre"] for x in client.get("/api/discussions", params={"q": "merci"}).json()] == ["Bonjour"]


def test_regenerer_remplace_la_derniere_reponse(client, cerveau):
    d = client.post("/api/chat", json={"message": "Bonjour"}).json()["discussion_id"]
    r = client.post("/api/chat", json={"discussion_id": d, "regenerer": True}).json()
    assert r["reponse"] == "Bonjour Monsieur."
    messages = client.get(f"/api/discussions/{d}").json()["messages"]
    assert [m["role"] for m in messages] == ["moi", "chef"]
    assert cerveau.par("grand_chef")[1].prompt.endswith("Nouveau message de Monsieur : Bonjour")


def test_agents_consultes_en_pastilles(client):
    r = client.post("/api/chat", json={"message": "Comment vont mes actions ?"}).json()
    assert sorted(r["agents"]) == ["Comptable", "Trader"]
    d = client.get(f"/api/discussions/{r['discussion_id']}").json()
    assert sorted(d["messages"][1]["agents"]) == ["Comptable", "Trader"]


def test_section_choisie_transmise_au_grand_chef(client, cerveau):
    client.post("/api/chat", json={"message": "Bonjour", "section": "bourse"})
    assert "section Bourse (Commandant Finance)" in cerveau.par("grand_chef")[0].prompt


# ---------------------------------------------------------------- préférences, agents, graphique


def test_preferences(client):
    assert client.get("/api/preferences").json()["theme"] == "nuit-or"
    p = client.put("/api/preferences", json={"theme": "papier", "auto": True}).json()
    assert p["theme"] == "papier" and p["auto"] is True
    assert client.get("/api/preferences").json()["theme"] == "papier"
    assert client.put("/api/preferences", json={"theme": "../etc"}).status_code == 422


def test_cinquante_agents(client):
    agents = client.get("/api/agents").json()
    assert len(agents) == 50
    actifs = sorted(a["nom"] for a in agents if a["actif"])
    assert actifs == ["Alarme", "Analyste", "Chasseur", "Comptable", "Historien", "Journaliste", "Radar", "Trader"]


@pytest.mark.parametrize("periode", ["1J", "1S", "1M", "1A"])
def test_graphique_bourse(client, periode):
    g = client.get("/api/bourse/graphique", params={"ticker": "AMD", "periode": periode}).json()
    assert g["periode"] == periode and len(g["points"]) >= 2
    assert client.get("/api/bourse/graphique", params={"ticker": "TSLA", "periode": periode}).status_code == 404


# ---------------------------------------------------------------- thèmes


def _themes():
    index = json.loads((UI / "themes" / "index.json").read_text(encoding="utf-8"))
    return {t: json.loads((UI / "themes" / f"{t}.json").read_text(encoding="utf-8")) for t in index["themes"]}


def _luminance(h):
    r, g, b = (int(h.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contraste(a, b):
    la, lb = sorted([_luminance(a), _luminance(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_vingt_themes_complets():
    themes = _themes()
    assert len(themes) == 20
    for nom, t in themes.items():
        assert sorted(t["couleurs"]) == sorted(CLES), nom
        for option, valeurs in OPTIONS.items():
            assert t[option] in valeurs, (nom, option)
        assert isinstance(t["bandeau"], bool)


@pytest.mark.parametrize("nom", list(_themes()))
def test_texte_lisible(nom):
    """Contraste minimal (norme d'accessibilité WCAG AA) : 4,5 pour le texte, 3 pour les éléments graphiques."""
    c = _themes()[nom]["couleurs"]
    for texte in ("texte", "texte2"):
        for fond in ("fond", "panneau", "surface", "relief"):
            assert contraste(c[texte], c[fond]) >= 4.5, (texte, fond)
    for texte in ("texte3", "accentTexte"):
        for fond in ("fond", "panneau", "surface"):
            assert contraste(c[texte], c[fond]) >= 4.5, (texte, fond)
    assert contraste(c["surAccent"], c["accent"]) >= 4.4   # icônes et boutons posés sur l'accent
    assert contraste(c["accent"], c["fond"]) >= 3.0        # graphiques et points


def test_aucune_couleur_en_dur_hors_des_themes():
    motif = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(")
    fautes = []
    for fichier in list(UI.glob("*.css")) + list(UI.glob("*.js")) + list(UI.glob("*.html")):
        for n, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
            if motif.search(ligne):
                fautes.append(f"{fichier.name}:{n}: {ligne.strip()}")
    assert not fautes, "\n".join(fautes)


def test_tache_de_fond_pour_les_longues_questions(client):
    """L'interface lance une tâche puis demande si elle est finie (évite « Load failed » après 60 s)."""
    import time

    r = client.post("/api/chat/tache", json={"message": "Comment vont mes actions ?"}).json()
    assert r["discussion_id"]
    fin = time.monotonic() + 60       # large marge : les machines de GitHub sont parfois lentes
    while time.monotonic() < fin:
        etat = client.get(f"/api/chat/tache/{r['tache']}").json()
        if etat["statut"] != "en_cours":
            break
        time.sleep(0.1)
    assert etat["statut"] == "fini"
    assert etat["resultat"]["reponse"].startswith("Monsieur, Compte rendu du Commandant Finance")
    assert client.get("/api/chat/tache/inconnue").status_code == 404
    assert client.post("/api/chat/tache", json={"message": "  "}).status_code == 422
