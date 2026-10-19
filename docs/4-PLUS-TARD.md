# 4. Plus tard : vrai nom de domaine, Stripe, AdSense

## Brancher le nom de domaine (sans rien casser)

1. Achetez le domaine (ex. `tradevantage.ch`) chez un registraire (Infomaniak, OVH, Namecheap…).
2. Netlify : **Domain management → Add a domain** → suivez les instructions (DNS).
   Le certificat HTTPS est automatique et gratuit.
3. Supabase : **Authentication → URL Configuration** → remplacez la *Site URL* par
   `https://tradevantage.ch` et ajoutez `https://tradevantage.ch/**` aux *Redirect URLs*.

Rien à changer dans le code : il utilise toujours l’adresse sur laquelle il est ouvert.
L’ancienne adresse `.netlify.app` redirigera vers la nouvelle.

## Paiements Stripe (le code est prêt, il dort)

Tout est déjà codé : page de paiement, passage automatique en Premium, retour au Gratuit
en cas de résiliation ou d’impayé, espace client (factures, carte, résiliation).
Tant que les clés ne sont pas dans Netlify, le bouton affiche « Paiement bientôt disponible ».

### A. Créer le compte et les prix
1. https://dashboard.stripe.com → créez le compte (Suisse) et activez-le (pièce d’identité, IBAN).
2. **Catalogue de produits → Ajouter un produit** : nom « Premium ».
   Ajoutez **4 prix récurrents** : CHF 9.90 / mois, CHF 89 / an, EUR 9.90 / mois, EUR 89 / an.
3. Copiez l’identifiant de chaque prix (il commence par `price_…`).

### B. Le « webhook » (Stripe prévient le site après chaque paiement)
**Développeurs → Webhooks → Ajouter une destination** :
- URL : `https://votresite/api/stripe-webhook`
- Événements : `checkout.session.completed`, `customer.subscription.created`,
  `customer.subscription.updated`, `customer.subscription.deleted`,
  `customer.subscription.paused`, `customer.subscription.resumed`
- Copiez la **clé de signature** (`whsec_…`).

### C. L’espace client
**Paramètres → Billing → Customer portal** → activez : annuler l’abonnement,
mettre à jour la carte, voir les factures.

### D. Les variables dans Netlify
| Nom | Valeur | Secret ? |
|---|---|---|
| `STRIPE_SECRET_KEY` | `sk_live_…` (Développeurs → Clés API) | **oui** |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` | **oui** |
| `STRIPE_PRICE_CHF_MONTHLY` | `price_…` | non |
| `STRIPE_PRICE_CHF_YEARLY` | `price_…` | non |
| `STRIPE_PRICE_EUR_MONTHLY` | `price_…` | non |
| `STRIPE_PRICE_EUR_YEARLY` | `price_…` | non |
| `STRIPE_AUTOMATIC_TAX` | `1` seulement si vous activez Stripe Tax (TVA) | non |

Redéployez : le bouton « S’abonner » apparaît.

💡 **Testez d’abord en mode Test** (clés `sk_test_…`) avec la carte `4242 4242 4242 4242`,
n’importe quelle date future et n’importe quel code.

💡 **TVA** : en Suisse, elle n’est obligatoire qu’au-delà de CHF 100 000 de chiffre d’affaires
annuel. Pour les clients européens, renseignez-vous (guichet OSS). Parlez-en à une fiduciaire.

## Publicité AdSense

Déjà prêt : l’emplacement publicitaire (plan gratuit uniquement) et le bandeau cookies.
Une fois le domaine validé par Google, ajoutez dans Netlify `VITE_ADSENSE_CLIENT`
(`ca-pub-…`), `VITE_ADSENSE_SLOT_HOME` et `VITE_ADSENSE_SLOT_SYMBOL`. La publicité ne
s’affiche qu’aux utilisateurs qui ont accepté les cookies publicitaires.

## Avant l’ouverture au public

- Remplir vos coordonnées dans `LEGAL` (fichier `src/config.ts`).
- Faire relire les CGU et la politique de confidentialité par un juriste.
- Vérifier que le nom choisi n’est pas déjà une marque déposée (Swissreg, EUIPO).
