# Tradevantage — suivi de bourse (PWA)

Plateforme web de suivi des marchés : actions et ETF (États-Unis, Suisse SIX, Europe) et cryptos.
Un seul site pour PC, Mac et iPhone, installable comme une vraie app.

> **Informations non contractuelles, ceci n’est pas un conseil en investissement.**

## Tout est gratuit pour l’instant

Toutes les fonctions sont ouvertes à tout le monde (watchlist illimitée, portefeuille,
alertes), sans publicité ni page Premium. Le code du Premium payant est gardé « en pause ».

**Pour vendre le Premium plus tard**, deux interrupteurs :
1. `ALL_FEATURES_FREE = false` dans `src/config.ts` ;
2. dans Supabase : **Table Editor → app_settings → all_features_free = false**.

## Ce qui est prêt

| Fonction | État |
|---|---|
| Graphique en bougies 1J / 1S / 1M / 1A / 5A, moyenne mobile, volume | ✅ (TradingView) |
| Watchlist avec recherche, suggestions, prix et variation vert/rouge | ✅ |
| Limite de 5 valeurs en Gratuit, illimité en Premium | ✅ (vérifié aussi par la base) |
| Actualités de chaque valeur | ✅ (TradingView) |
| Comptes e-mail + mot de passe, mot de passe oublié, suppression du compte | ✅ (Supabase) |
| Portefeuille (Premium) : valeur, gains et pertes par devise | ✅ * |
| Alertes de prix par notification (Premium) | ✅ * |
| Français / anglais, prêt pour d’autres langues | ✅ |
| Mode clair / sombre, design « verre » | ✅ |
| App installable (PWA), iPhone compris | ✅ |
| Message d’avertissement, CGU, confidentialité, bandeau cookies | ✅ |
| Paiement Stripe (abonnement mensuel / annuel, espace client) | ✅ codé, s’active avec les clés |
| Publicité AdSense (plan gratuit, après consentement) | ✅ codé, s’active avec le domaine |
| Tests automatiques sur GitHub à chaque modification | ✅ |

\* Le calcul des gains et la surveillance des alertes ont besoin d’une source de prix
**côté serveur** (voir [docs/DONNEES.md](docs/DONNEES.md)). Sans elle, les prix restent
affichés par TradingView, mais les totaux et les alertes attendent.

## Guides (en français simple)

1. [Créer la base de données Supabase](docs/1-SUPABASE.md)
2. [Mettre le site en ligne sur Netlify](docs/2-NETLIFY.md)
3. [Activer les notifications d’alertes](docs/3-NOTIFICATIONS.md)
4. [Les données de marché et leur licence](docs/DONNEES.md)
5. [Plus tard : nom de domaine, Stripe, AdSense](docs/4-PLUS-TARD.md)
6. [E-mails de connexion en français et anglais](docs/5-EMAILS.md)
7. [Mail prêt à envoyer à EODHD (licence des données)](docs/MAIL-EODHD.md)

## Pour les développeurs

```bash
npm install
npm run dev          # site en local sur http://localhost:5173
npm test             # tests unitaires + base de données (RLS)
npm run test:e2e     # tests dans un vrai navigateur (ordinateur + iPhone)
npm run build:netlify  # construction + vérification qu’aucune clé secrète ne fuit
```

Structure :

```
src/                 le site (React)
  i18n/messages/     les textes, une langue par fichier
  pages/             les écrans
  components/        les morceaux réutilisables (widgets, recherche, watchlist…)
  lib/symbols.ts     le catalogue des valeurs proposées
  config.ts          nom du site, limites des plans, prix, infos légales
netlify/functions/   le serveur (prix en cache, alertes chaque minute, paiements, suppression de compte)
supabase/migrations/ la structure de la base de données et ses règles de sécurité
tests/               tests automatiques
```

**Changer le nom du site** : une seule ligne, dans `src/brand.ts`.
