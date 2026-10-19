# 4. Plus tard : vrai nom de domaine, Stripe, AdSense

## Brancher le nom de domaine (sans rien casser)

1. Achetez le domaine (ex. `tickglass.com`) chez un registraire (Infomaniak, OVH, Namecheap…).
2. Netlify : **Domain management → Add a domain** → suivez les instructions (DNS).
   Le certificat HTTPS est automatique et gratuit.
3. Supabase : **Authentication → URL Configuration** → remplacez la *Site URL* par
   `https://tickglass.com` et ajoutez `https://tickglass.com/**` aux *Redirect URLs*.

Rien à changer dans le code : il utilise toujours l’adresse sur laquelle il est ouvert.
L’ancienne adresse `.netlify.app` redirigera vers la nouvelle.

## Paiements Stripe (prochaine étape de développement)

Déjà prêt dans le code : les plans, les limites, la colonne `stripe_customer_id`,
la page Premium et les prix (CHF/EUR 9.90 par mois, 89 par an). Il restera à ajouter
la page de paiement Stripe et la fonction qui passe le compte en Premium après paiement.

## Publicité AdSense

Déjà prêt : l’emplacement publicitaire (plan gratuit uniquement) et le bandeau cookies.
Une fois le domaine validé par Google, ajoutez dans Netlify `VITE_ADSENSE_CLIENT`
(`ca-pub-…`), `VITE_ADSENSE_SLOT_HOME` et `VITE_ADSENSE_SLOT_SYMBOL`. La publicité ne
s’affiche qu’aux utilisateurs qui ont accepté les cookies publicitaires.

## Avant l’ouverture au public

- Remplir vos coordonnées dans `LEGAL` (fichier `src/config.ts`).
- Faire relire les CGU et la politique de confidentialité par un juriste.
- Vérifier que le nom choisi n’est pas déjà une marque déposée (Swissreg, EUIPO).
