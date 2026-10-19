# 1. Créer la base de données (Supabase)

Supabase garde les comptes et les données de vos clients (watchlist, portefeuille, alertes).
L’offre gratuite suffit pour commencer.

## A. Créer le projet (5 minutes)

1. Allez sur **https://supabase.com** → **Start your project** → connectez-vous avec GitHub.
2. Cliquez **New project**.
   - **Name** : `tickglass`
   - **Database password** : cliquez *Generate*, puis gardez-le dans un endroit sûr.
   - **Region** : **Central EU (Frankfurt)**. C’est important : les données restent en Europe (nLPD et RGPD).
3. Cliquez **Create new project** et attendez environ 2 minutes.

## B. Créer les tables (1 minute)

1. Dans le menu de gauche : **SQL Editor** → **New query**.
2. Ouvrez le fichier `supabase/migrations/001_init.sql` de ce projet, copiez **tout** le texte et collez-le.
3. Cliquez **Run**. Le message « Success. No rows returned » doit s’afficher : c’est bon.

## C. Récupérer les deux adresses dont Netlify aura besoin

Menu **Project Settings** (roue dentée) → **API Keys** (ou **API**) :

| Ce que vous voyez dans Supabase | Nom à utiliser dans Netlify | Secret ? |
|---|---|---|
| Project URL (`https://xxxx.supabase.co`) | `VITE_SUPABASE_URL` | Non, public |
| Clé **anon** / **publishable** | `VITE_SUPABASE_ANON_KEY` | Non, public (protégé par les règles de la base) |
| Clé **service_role** / **secret** | `SUPABASE_SERVICE_ROLE_KEY` | ⚠️ **OUI, ne jamais la partager** |

## D. Régler l’adresse du site (après la mise en ligne Netlify)

Menu **Authentication** → **URL Configuration** :
- **Site URL** : `https://monsite.netlify.app` (votre adresse Netlify)
- **Redirect URLs** → *Add URL* : `https://monsite.netlify.app/**`

Les liens des e-mails (confirmation, mot de passe oublié) renverront ainsi vers votre site.

## E. Passer un compte en Premium à la main (pour tester)

En attendant Stripe : **Table Editor** → table **profiles** → trouvez la ligne du compte →
colonne **plan** : remplacez `free` par `premium` → **Save**. Rechargez le site.
