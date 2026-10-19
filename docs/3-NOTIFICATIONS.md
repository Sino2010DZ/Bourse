# 3. Activer les notifications d’alertes

Les alertes sont vérifiées **chaque minute** par le serveur (fonction `check-alerts`),
qui envoie une notification sur le téléphone ou l’ordinateur du client.

## A. Créer vos clés de notification (une seule fois)

Sur un ordinateur avec Node.js, dans le dossier du projet :

```bash
npx web-push generate-vapid-keys
```

Vous obtenez une *Public Key* et une *Private Key*.

## B. Les ajouter dans Netlify

| Nom | Valeur | Secret ? |
|---|---|---|
| `VITE_VAPID_PUBLIC_KEY` | Public Key | non |
| `VAPID_PRIVATE_KEY` | Private Key | **oui** |
| `VAPID_SUBJECT` | `mailto:votre@email.com` | non |

Puis **Deploys → Trigger deploy → Deploy project**.

## C. Brancher une source de prix serveur

Le serveur doit connaître les prix pour savoir quand une alerte se déclenche.
Voir [DONNEES.md](DONNEES.md) : il faut ajouter `EODHD_API_KEY`. Sans elle,
les alertes sont enregistrées mais pas surveillées (le site l’indique clairement).

## Bon à savoir sur iPhone

Les notifications marchent sur iPhone (iOS 16.4 ou plus récent) **uniquement si l’app est
installée sur l’écran d’accueil** et ouverte depuis son icône. Le site l’explique à l’utilisateur.
