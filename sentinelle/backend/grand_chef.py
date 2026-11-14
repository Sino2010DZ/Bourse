"""Le Grand Chef (JARVIS) : reçoit les demandes de Monsieur et répond en une seule réponse.

Phase 1 : aucun commandant n'est encore en service. Le Grand Chef répond lui-même,
poliment, et n'invente jamais de données (cours, prix, résultats…).
Phase 2 et suivantes : il enverra le travail aux commandants et résumera leurs réponses.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from config import PRIX_PAR_MILLION, Reglages
from journal import Entree, Journal
from sections import SECTIONS


@dataclass
class Reponse:
    texte: str
    modele: str
    duree_ms: int
    tokens_entree: int = 0
    tokens_sortie: int = 0
    cout_usd: float = 0.0
    erreur: bool = False


# Un « cerveau » reçoit (consigne système, message, modèle, effort) et renvoie une Reponse.
# En vrai : le Claude Agent SDK. Dans les tests : une fausse version, gratuite et rapide.
Cerveau = Callable[[str, str, str, str], Awaitable[Reponse]]


def consigne_systeme() -> str:
    lignes_sections = "\n".join(
        f"- {s['icone']} {s['nom']} ({s['commandant']}) : "
        + {"active": "en service", "en_preparation": "en préparation", "a_construire": "pas encore construite"}[s["statut"]]
        for s in SECTIONS
    )
    return f"""Tu es le Grand Chef de Sentinelle, l'assistant personnel de Monsieur, dans le style de JARVIS (Iron Man).

Ton et langue :
- Réponds toujours en français, en vouvoyant, en t'adressant à lui par « Monsieur ».
- Ton calme, précis, élégant, avec une pointe d'humour britannique discret. Réponses courtes et claires.
- Écris en texte simple : pas de titres ni de tableaux Markdown (le **gras** est permis, avec parcimonie).
- Monsieur vit à Genève : prix en CHF, heure de Zurich.

Ton rôle :
- Tu diriges 10 commandants ; chacun dirige 5 agents spécialisés. Tu ne fais pas leur travail toi-même.
- État actuel des sections :
{lignes_sections}
- Si Monsieur demande quelque chose qui relève d'une section pas encore en service, dis-le simplement
  et indique que la section sera construite prochainement.

Règles absolues :
- N'invente jamais de données (cours de bourse, prix, résultats sportifs, météo…). Si tu n'as pas l'information, dis-le.
- Ne donne jamais d'ordre d'achat ou de vente d'actions : tu informes seulement.
- Ne supprime rien, n'achète rien, n'envoie aucun mail sans le bouton « Confirmer » de Monsieur."""


def _historique_en_texte(historique: list[tuple[str, str]], message: str) -> str:
    if not historique:
        return message
    morceaux = ["Voici les derniers échanges de la conversation :"]
    for demande, reponse in historique:
        morceaux.append(f"Monsieur : {demande}\nToi : {reponse}")
    morceaux.append(f"Nouveau message de Monsieur : {message}")
    return "\n\n".join(morceaux)


class GrandChef:
    MEMOIRE = 10  # nombre d'échanges gardés en mémoire pour suivre la conversation

    def __init__(self, reglages: Reglages, journal: Journal, cerveau: Cerveau | None = None) -> None:
        self.reglages = reglages
        self.journal = journal
        self.cerveau = cerveau or cerveau_claude
        self.historique: list[tuple[str, str]] = []

    async def repondre(self, message: str) -> Reponse:
        message = message.strip()
        if not message:
            return Reponse("Je vous écoute, Monsieur.", modele="aucun", duree_ms=0)

        if not self.reglages.cle_presente and self.cerveau is cerveau_claude:
            reponse = Reponse(
                "Bonjour Monsieur. Mes systèmes sont en ligne, mais il me manque ma clé API Anthropic "
                "pour réfléchir. Copiez le fichier .env.example en .env, collez-y votre clé, "
                "puis relancez Sentinelle.",
                modele="aucun",
                duree_ms=0,
                erreur=True,
            )
        else:
            prompt = _historique_en_texte(self.historique[-self.MEMOIRE:], message)
            reponse = await self.cerveau(
                consigne_systeme(), prompt, self.reglages.modele_grand_chef, self.reglages.effort_grand_chef
            )
            if not reponse.erreur:
                self.historique.append((message, reponse.texte))

        self.journal.noter(
            Entree(
                qui="grand_chef",
                demande=message,
                reponse=reponse.texte,
                modele=reponse.modele,
                duree_ms=reponse.duree_ms,
                tokens_entree=reponse.tokens_entree,
                tokens_sortie=reponse.tokens_sortie,
                cout_usd=reponse.cout_usd,
                erreur=reponse.erreur,
            )
        )
        return reponse


async def cerveau_claude(systeme: str, prompt: str, modele: str, effort: str) -> Reponse:
    """Appelle Claude via le Claude Agent SDK (aucun outil : le Grand Chef ne fait que parler)."""
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

    options = ClaudeAgentOptions(
        system_prompt=systeme,
        model=modele,
        effort=effort,
        tools=[],              # aucun outil (ni fichiers, ni terminal, ni web)
        setting_sources=[],    # n'utilise pas les réglages Claude Code de l'ordinateur
        max_turns=1,
    )
    debut = time.monotonic()
    textes: list[str] = []
    resultat: ResultMessage | None = None
    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                textes.extend(b.text for b in msg.content if isinstance(b, TextBlock))
            elif isinstance(msg, ResultMessage):
                resultat = msg
    except Exception as exc:  # connexion, clé refusée, etc.
        return Reponse(
            f"Toutes mes excuses, Monsieur : je n'arrive pas à joindre mon cerveau ({type(exc).__name__}). "
            "Vérifiez votre connexion Internet et votre clé API.",
            modele=modele,
            duree_ms=int((time.monotonic() - debut) * 1000),
            erreur=True,
        )

    duree_ms = int((time.monotonic() - debut) * 1000)
    usage = (resultat.usage if resultat else None) or {}
    entree = usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
    sortie = usage.get("output_tokens", 0)
    cout = resultat.total_cost_usd if resultat and resultat.total_cost_usd is not None else _cout_estime(modele, entree, sortie)
    texte = "".join(textes).strip() or (resultat.result if resultat and resultat.result else "")
    erreur = bool(resultat and resultat.is_error) or not texte
    if erreur:
        texte = (
            "Toutes mes excuses, Monsieur : ma réflexion a échoué. "
            "Vérifiez que votre clé API est valide et que votre compte Anthropic a du crédit."
        )
    return Reponse(texte, modele, duree_ms, entree, sortie, round(cout, 6), erreur)


def _cout_estime(modele: str, entree: int, sortie: int) -> float:
    prix_entree, prix_sortie = PRIX_PAR_MILLION.get(modele, (0.0, 0.0))
    return (entree * prix_entree + sortie * prix_sortie) / 1_000_000
