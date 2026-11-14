"""Le « cerveau » : un seul endroit qui appelle Claude via le Claude Agent SDK.

Grand Chef, commandants et agents passent tous par ici. Dans les tests, on le remplace
par un faux cerveau (gratuit, instantané) grâce au type `Cerveau`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from config import PRIX_PAR_MILLION


@dataclass
class Demande:
    qui: str                       # ex. « grand_chef », « bourse/commandant », « bourse/trader »
    systeme: str                   # consigne permanente (rôle)
    prompt: str                    # la question du moment
    modele: str
    effort: str = "low"
    outils: list[Any] = field(default_factory=list)   # outils @tool du SDK (Grand Chef seulement)
    format_json: dict | None = None                   # schéma JSON si on veut une réponse structurée
    tours_max: int = 1


@dataclass
class Reponse:
    texte: str
    modele: str
    duree_ms: int
    tokens_entree: int = 0
    tokens_sortie: int = 0
    cout_usd: float = 0.0
    erreur: bool = False
    donnees: Any = None            # réponse structurée (si format_json)


Cerveau = Callable[[Demande], Awaitable[Reponse]]

NOM_SERVEUR_OUTILS = "sentinelle"


async def cerveau_claude(d: Demande) -> Reponse:
    """Appelle Claude. Aucun outil intégré (fichiers, terminal, web) : seulement nos propres outils."""
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        create_sdk_mcp_server,
        query,
    )

    options = ClaudeAgentOptions(
        system_prompt=d.systeme,
        model=d.modele,
        effort=d.effort,
        tools=[],              # pas d'outils Claude Code (ni fichiers, ni terminal, ni web)
        setting_sources=[],    # n'utilise pas les réglages Claude Code de l'ordinateur
        max_turns=d.tours_max,
    )
    if d.outils:
        options.mcp_servers = {NOM_SERVEUR_OUTILS: create_sdk_mcp_server(NOM_SERVEUR_OUTILS, tools=d.outils)}
        options.allowed_tools = [f"mcp__{NOM_SERVEUR_OUTILS}__{o.name}" for o in d.outils]
    if d.format_json:
        options.output_format = {"type": "json_schema", "schema": d.format_json}

    debut = time.monotonic()
    textes: list[str] = []
    resultat: ResultMessage | None = None
    try:
        async for msg in query(prompt=d.prompt, options=options):
            if isinstance(msg, AssistantMessage):
                textes = [b.text for b in msg.content if isinstance(b, TextBlock)] or textes
            elif isinstance(msg, ResultMessage):
                resultat = msg
    except Exception as exc:  # connexion, clé refusée, etc.
        return Reponse(
            f"Toutes mes excuses, Monsieur : je n'arrive pas à joindre mon cerveau ({type(exc).__name__}). "
            "Vérifiez votre connexion Internet et votre clé API.",
            modele=d.modele,
            duree_ms=int((time.monotonic() - debut) * 1000),
            erreur=True,
        )

    duree_ms = int((time.monotonic() - debut) * 1000)
    usage = (resultat.usage if resultat else None) or {}
    entree = sum(usage.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    sortie = usage.get("output_tokens", 0)
    if resultat and resultat.total_cost_usd is not None:
        cout = resultat.total_cost_usd
    else:
        cout = cout_estime(d.modele, entree, sortie)

    # Texte final : le dernier message texte (après d'éventuels appels d'outils).
    texte = (resultat.result if resultat and resultat.result else "".join(textes)).strip()
    donnees = resultat.structured_output if resultat else None
    erreur = bool(resultat is None or resultat.is_error) or not (texte or donnees)
    if erreur:
        texte = (
            "Toutes mes excuses, Monsieur : ma réflexion a échoué. "
            "Vérifiez que votre clé API est valide et que votre compte Anthropic a du crédit."
        )
    return Reponse(texte, d.modele, duree_ms, entree, sortie, round(cout, 6), erreur, donnees)


def cout_estime(modele: str, entree: int, sortie: int) -> float:
    prix_entree, prix_sortie = PRIX_PAR_MILLION.get(modele, (0.0, 0.0))
    return (entree * prix_entree + sortie * prix_sortie) / 1_000_000
