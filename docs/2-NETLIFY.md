# 2. Mettre le site en ligne sur Netlify (gratuit)

Votre site sera à l’adresse **https://monsite.netlify.app** (vous choisirez le nom).
Le code est déjà prêt pour un vrai nom de domaine plus tard, sans rien casser.

## A. Créer le compte et connecter GitHub

1. Allez sur **https://app.netlify.com** → **Sign up** → **Continue with GitHub**.
2. Cliquez **Add new project** (parfois appelé *Add new site*) → **Import an existing project**.
3. Choisissez **GitHub**, autorisez Netlify, puis sélectionnez le dépôt **Bourse**.

## B. Réglages de construction

Netlify lit tout seul le fichier `netlify.toml` du projet. Vérifiez simplement :
- **Branch to deploy** : `main`
- **Build command** : `npm run build:netlify`
- **Publish directory** : `dist`

## C. Ajouter les variables (avant le premier déploiement)

Sur la même page, cliquez **Add environment variables** (ou après coup :
**Project configuration → Environment variables → Add a variable**) :

| Nom | Valeur | Secret ? |
|---|---|---|
| `VITE_SUPABASE_URL` | Project URL de Supabase | non |
| `VITE_SUPABASE_ANON_KEY` | clé anon / publishable | non |
| `SUPABASE_SERVICE_ROLE_KEY` | clé service_role / secret | **oui** : cochez *Contains secret values* |

Les noms qui commencent par `VITE_` sont visibles dans le navigateur, et c’est normal.
**Tous les autres restent sur le serveur.** Un contrôle automatique bloque la mise en ligne
si une clé secrète se retrouvait par erreur dans le site public.

## D. Lancer

Cliquez **Deploy**. Après 1 à 2 minutes, le statut passe à **Published**.

## E. Choisir le nom de l’adresse

**Project configuration → General → Project details → Change project name** →
tapez par exemple `tickglass` → votre site devient **https://tickglass.netlify.app**.

👉 Retournez ensuite dans Supabase, étape **D** du guide 1, pour indiquer cette adresse.

## F. Installer l’app sur votre iPhone

1. Ouvrez l’adresse dans **Safari**.
2. Touchez **Partager** (le carré avec la flèche) → **Sur l’écran d’accueil** → **Ajouter**.
3. L’icône Tickglass apparaît comme une vraie app.

Sur PC ou Mac (Chrome, Edge), une petite icône « Installer » apparaît dans la barre d’adresse.

## Et après ?

Chaque fois que le code est modifié sur GitHub (branche `main`), Netlify remet le site à jour
tout seul. Si un déploiement échoue, l’ancienne version reste en ligne : rien ne casse.
