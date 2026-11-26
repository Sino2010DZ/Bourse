"""Le Codeur pilote Claude Code sur un projet de Monsieur — UNIQUEMENT après le bouton « Confirmer ».

Garde-fous :
- seulement dans un dossier de projet choisi dans Réglages › Projets ;
- outils limités à lire / chercher / écrire / modifier des fichiers : pas de terminal, pas d'Internet ;
- chaque chemin est vérifié (rien en dehors du projet) ;
- avant chaque modification, l'original est copié dans une sauvegarde : « Annuler les modifications » le remet ;
- budget maximum par chantier (1 $ par défaut).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath

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

    def enregistrer(self) -> None:
        """Note au fur et à mesure ce qui a été touché : permet d'annuler même si Sentinelle s'arrête en route."""
        self.sauvegarde.mkdir(parents=True, exist_ok=True)
        (self.sauvegarde / "chantier.json").write_text(
            json.dumps({"modifies": self.modifies, "crees": self.crees}, ensure_ascii=False), encoding="utf-8")

    def avant_outil(self, outil: str, entree: dict) -> str | None:
        """Renvoie une raison de refus, ou None si l'outil peut s'exécuter (après sauvegarde éventuelle)."""
        # Les motifs de recherche (Glob, Grep) ne doivent pas viser l'extérieur du projet.
        for cle in ("pattern", "glob"):
            motif = entree.get(cle) if outil in ("Glob", "Grep") else None
            if motif and (PurePosixPath(motif).is_absolute() or PureWindowsPath(motif).is_absolute()
                          or PureWindowsPath(motif).drive or ".." in PurePosixPath(motif.replace("\\", "/")).parts):
                self.refus.append(str(motif))
                return "Interdit : la recherche doit rester dans le projet choisi."
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
                self.enregistrer()
        elif outil in ECRITURE:
            relatif = chemin.relative_to(self.projet.resolve()).as_posix()
            if relatif not in self.crees and relatif not in self.modifies:
                self.crees.append(relatif)
                self.enregistrer()
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
    textes, resultat, incident = [], None, None
    try:
        async for msg in requete(prompt=consigne, options=options):
            if isinstance(msg, AssistantMessage):
                textes = [b.text for b in msg.content if isinstance(b, TextBlock)] or textes
            elif isinstance(msg, ResultMessage):
                resultat = msg
    except Exception as exc:   # on garde la liste des fichiers touchés pour pouvoir annuler
        incident = f"Claude Code s'est arrêté ({type(exc).__name__})."
    resume = (resultat.result if resultat and resultat.result else "\n".join(textes)).strip()
    if incident:
        resume = f"{incident} {resume}".strip()
    return {
        "resume": resume or "(pas de résumé)",
        "modifies": chantier.modifies,
        "crees": chantier.crees,
        "refus": chantier.refus,
        "cout_usd": round(resultat.total_cost_usd or 0, 4) if resultat else 0,
        "erreur": bool(incident or resultat is None or resultat.is_error),
    }


def lire_chantier(sauvegarde: Path) -> dict:
    """Relit la liste des fichiers touchés par un chantier interrompu."""
    try:
        return json.loads((sauvegarde / "chantier.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"modifies": [], "crees": []}


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
