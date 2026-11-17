"""Courrier Gmail en LECTURE SEULE (IMAP + mot de passe d'application).

- La boîte est ouverte en lecture seule et les messages sont lus avec PEEK : rien n'est marqué comme lu.
- Seuls l'expéditeur, l'objet et la date sont lus (pas le contenu des messages).
- Sentinelle n'envoie, ne déplace et ne supprime jamais aucun mail.
"""

from __future__ import annotations

import asyncio
import email.header
import email.utils
import imaplib
from typing import Callable

SERVEUR = "imap.gmail.com"


def _decoder(valeur: str | None) -> str:
    if not valeur:
        return ""
    morceaux = []
    for texte, encodage in email.header.decode_header(valeur):
        morceaux.append(texte.decode(encodage or "utf-8", errors="replace") if isinstance(texte, bytes) else texte)
    return "".join(morceaux).strip()


def lire_entetes(adresse: str, mot_de_passe: str, nombre: int = 30, fabrique=imaplib.IMAP4_SSL) -> list[dict]:
    boite = fabrique(SERVEUR)
    try:
        boite.login(adresse, mot_de_passe)
        boite.select("INBOX", readonly=True)
        _, donnees = boite.search(None, "UNSEEN")
        ids = (donnees[0] or b"").split()[-nombre:]
        messages = []
        for ident in reversed(ids):
            _, brut = boite.fetch(ident, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            entete = email.message_from_bytes(brut[0][1])
            nom, adr = email.utils.parseaddr(_decoder(entete.get("From")))
            messages.append({
                "de": nom or adr,
                "adresse": adr,
                "objet": _decoder(entete.get("Subject")) or "(sans objet)",
                "date": entete.get("Date", ""),
            })
        return messages
    finally:
        try:
            boite.logout()
        except Exception:
            pass


class ServiceCourrier:
    def __init__(self, identifiants: Callable[[], tuple[str, str] | None], lecteur=lire_entetes) -> None:
        self.identifiants = identifiants
        self.lecteur = lecteur

    async def non_lus(self) -> dict:
        ids = self.identifiants()
        if not ids:
            return {"connecte": False, "info": "Gmail non connecté : Monsieur peut l'ajouter dans Réglages › Comptes."}
        try:
            messages = await asyncio.to_thread(self.lecteur, ids[0], ids[1])
        except imaplib.IMAP4.error:
            return {"connecte": True, "erreur": "Gmail refuse la connexion : vérifiez le mot de passe d'application."}
        return {"connecte": True, "non_lus": messages, "nombre": len(messages)}
