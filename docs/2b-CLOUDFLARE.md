# Héberger sur Cloudflare Pages (gratuit)

Le projet est prêt pour Cloudflare Pages : `wrangler.toml`, `public/_headers` et le dossier
`functions/` (les petites fonctions serveur, mêmes que pour Netlify).

## Option A — Relier à GitHub (mise à jour automatique à chaque modification)
1. https://dash.cloudflare.com → **Workers & Pages** → **Create** → onglet **Pages** → **Connect to Git**.
2. Choisissez le dépôt **Bourse**, branche `main`.
3. Réglages de construction :
   - Framework preset : **None**
   - Build command : `npm run build`
   - Build output directory : `dist`
4. **Save and Deploy**. Adresse : `https://tradevantage.pages.dev` (ou proche).

## Variables (plus tard, quand vous branchez Supabase, Stripe, etc.)
Projet → **Settings → Variables and Secrets** : mêmes noms que dans `.env.example`.
Choisissez le type **Secret** pour les clés secrètes (service_role, Stripe, EODHD, VAPID privée).
Les variables qui commencent par `VITE_` doivent aussi être présentes au moment de la construction.

## Ce qui diffère de Netlify
- Les alertes vérifiées chaque minute (`check-alerts`) ont besoin d’un petit « Worker » planifié
  séparé sur Cloudflare : à ajouter le jour où Supabase et une source de prix sont branchés.
- Nom de domaine : projet → **Custom domains** → **Set up a domain**. Rien à changer dans le code.
