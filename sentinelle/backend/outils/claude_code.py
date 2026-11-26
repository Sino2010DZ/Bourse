"""Le Codeur pilote Claude Code sur un projet de Monsieur — UNIQUEMENT après le bouton « Confirmer ».

Garde-fous :
- seulement dans un dossier de projet choisi dans Réglages › Projets ;
- outils limités à lire / chercher / écrire / modifier des fichiers : pas de terminal, pas d'Internet ;
- chaque chemin est vérifié (rien en dehors du projet) ;
- avant chaque modification, l'original est copié dans une sauvegarde : « Annuler les modifications » le remet ;
- budget maximum par chantier (1 $ par défaut).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

OUTILS = ["Read", "Write", "Edit", "Glob", "Grep"]
ECRITURE = {"Write", "Edit"}


@dataclass
class Chantier:
    projet: Path
    sauvegarde: Path
    modifies: list[str] = field(default_factory=list)   # fichiers existants modifiés (originaux sauvegardés)
    crees: list[str] = field(default_factory=list)      # nouveaux fichiers
    refus: list[str] = field(default_factory=list)

    def chemin_autorise(self, brut: str | None) -> Path | None:
        if not brut:
            return self.projet
        chemin = Path(brut)
        if not chemin.is_absolute():
            chemin = self.projet / chemin
        try:
            chemin = chemin.resolve()
        except OSError:
            return None
        racine = self.projet.resolve()
        return chemin if chemin == racine or racine in chemin.parents else None

    def avant_outil(self, outil: str, entree: dict) -> str | None:
        """Renvoie une raison de refus, ou None si l'outil peut s'exécuter (après sauvegarde éventuelle)."""
        brut = entree.get("file_path") or entree.get("path") or entree.get("notebook_path")
        chemin = self.chemin_autorise(brut)
        if chemin is None:
            self.refus.append(str(brut))
            return "Interdit : Sentinelle n'autorise que les fichiers du projet choisi."
        if outil in ECRITURE and chemin.is_file():
            relatif = chemin.relative_to(self.projet.resolve()).as_posix()
            if relatif not in self.modifies and relatif not in self.crees:
                copie = self.sauvegarde / relatif
                copie.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(chemin, copie)
                self.modifies.append(relatif)
        elif outil in ECRITURE:
            relatif = chemin.relative_to(self.projet.resolve()).as_posix()
            if relatif not in self.crees and relatif not in self.modifies:
                self.crees.append(relatif)
        return None


def consigne_systeme() -> str:
    return (
        "Tu travailles pour Monsieur, qui débute en programmation, sur son projet (dossier courant). "
        "Fais exactement la modification demandée, proprement, sans toucher au reste. Tu n'as ni terminal ni Internet. "
        "Termine par un court résumé en français : fichiers modifiés et ce qui a changé, puis comment vérifier."
    )


async def executer_chantier(projet: str, consigne: str, sauvegarde: Path, modele: str,
                            budget_usd: float = 1.0, requete=None) -> dict:
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, HookMatcher, ResultMessage, TextBlock

    if requete is None:
        from claude_agent_sdk import query as requete

    chantier = Chantier(Path(projet).expanduser(), sauvegarde)
    if not chantier.projet.is_dir():
        raise ValueError("le dossier du projet n'existe plus")

    async def garde(entree, _id, _contexte):
        raison = chantier.avant_outil(entree.get("tool_name", ""), entree.get("tool_input") or {})
        if raison:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                           "permissionDecisionReason": raison}}
        return {}

    options = ClaudeAgentOptions(
        cwd=str(chantier.projet),
        tools=OUTILS,
        allowed_tools=OUTILS,
        permission_mode="acceptEdits",
        setting_sources=[],                 # n'utilise aucun réglage qui donnerait plus de droits
        system_prompt={"type": "preset", "preset": "claude_code", "append": consigne_systeme()},
        model=modele,
        max_turns=40,
        max_budget_usd=budget_usd,
        hooks={"PreToolUse": [HookMatcher(matcher="|".join(OUTILS), hooks=[garde])]},
    )
    textes, resultat = [], None
    async for msg in requete(prompt=consigne, options=options):
        if isinstance(msg, AssistantMessage):
            textes = [b.text for b in msg.content if isinstance(b, TextBlock)] or textes
        elif isinstance(msg, ResultMessage):
            resultat = msg
    resume = (resultat.result if resultat and resultat.result else "\n".join(textes)).strip()
    return {
        "resume": resume or "(pas de résumé)",
        "modifies": chantier.modifies,
        "crees": chantier.crees,
        "refus": chantier.refus,
        "cout_usd": round(resultat.total_cost_usd or 0, 4) if resultat else 0,
        "erreur": bool(resultat is None or resultat.is_error),
    }


def restaurer(projet: str, sauvegarde: Path, modifies: list[str], crees: list[str]) -> str:
    """« Annuler les modifications » : remet les originaux et retire les fichiers créés par le chantier."""
    base = Path(projet).expanduser().resolve()
    remis, retires = 0, 0
    for relatif in modifies:
        copie = sauvegarde / relatif
        cible = (base / relatif).resolve()
        if copie.is_file() and base in cible.parents:
            shutil.copy2(copie, cible)
            remis += 1
    for relatif in crees:
        cible = (base / relatif).resolve()
        if cible.is_file() and base in cible.parents:
            cible.unlink()
            retires += 1
    return f"{remis} fichiers remis dans leur état d'origine, {retires} fichiers créés retirés."
