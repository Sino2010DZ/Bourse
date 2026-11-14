# Projet Sentinelle — armée de 50 agents IA

## Objectif
Une application de bureau (Mac d'abord, Windows ensuite) où je parle à un seul agent, le **Grand Chef**.
Il dirige **10 commandants**, et chaque commandant dirige **5 agents** spécialisés (une fonction par agent).

## Règles techniques
- Langage : Python, avec le **Claude Agent SDK**.
- Hiérarchie sur 3 niveaux : Grand Chef → commandant de section → agents. C'est le programme qui fait le lien entre chaque niveau.
- Un seul code pour Mac et Windows. Application avec **Tauri**, design **Liquid Glass** épuré.
- Version **macOS en premier** (je n'ai qu'un Mac pour l'instant). Les agents marqués 🍎/🪟 ont une version par système.
- Cours de bourse via **Yahoo Finance** (pas de scraping de TradingView).
- Liens d'achat : **Galaxus** (Suisse, prix en CHF).
- Langue de l'interface et des réponses : français. Ton : comme JARVIS (« Monsieur… »).
- Construire **une section à la fois**. Ordre : Grand Chef + section Bourse, puis les autres.
- Le code propre à chaque système va dans `backend/plateforme/mac/` et `backend/plateforme/windows/`
  (nommé `plateforme` et non `platform` pour ne pas masquer le module `platform` de Python).

## Organisation

### 👑 Grand Chef (JARVIS)
Reçoit toutes mes demandes, envoie le travail aux bons commandants (plusieurs en même temps si besoin), puis me donne une seule réponse claire.

### 🔧 1. Matériel PC — Commandant Tech
- Conseiller : choisit les meilleures pièces (config actuelle : GPU Radeon RX 9070 XT, RAM DDR4).
- Compatibilité : vérifie que les pièces vont ensemble.
- Testeur : lit les tests et les avis.
- Pilotes 🍎/🪟 : mises à jour macOS / pilotes AMD.
- Performance 🍎/🪟 : batterie et énergie / réglages de la carte graphique.

### 💰 2. Prix & Achats — Commandant Achats
- Chasseur : relève chaque jour le prix des produits suivis sur Galaxus.
- Historien : trace les courbes de prix.
- Alarme : prévient quand un prix baisse.
- Comparateur : compare avec d'autres sites suisses.
- Black Friday : repère les grosses promos.

### 📈 3. Bourse — Commandant Finance
- Trader : suit les cours de mes actions (AMD, ETF SPDR US Tech, Aston Martin).
- Journaliste : résume les actus qui peuvent faire bouger mes actions.
- Comptable : calcule gains et pertes du portefeuille.
- Analyste : lit les graphiques et les tendances.
- Radar : repère les actions qui bougent fort.

### 🌐 4. Renseignement — Commandant Veille
- Éclaireur : fait les recherches web pour les autres agents.
- Résumeur : résume les longues pages en 3 phrases.
- Vérificateur : contrôle que les infos sont vraies.
- Traducteur : traduit en français.
- Archiviste : garde les trouvailles importantes.

### 🏁 5. Sport — Commandant Stade
- Stand F1 : résultats et calendrier.
- Courtside : matchs NBA.
- Tribune : football.
- Coup d'envoi : alerte avant chaque course ou match.
- Statisticien : classements et stats.

### 🎬 6. Divertissement — Commandant Détente
- DJ : gère mes playlists Spotify.
- Découvreur : trouve de la nouvelle musique.
- Critique : dit si un film ou une série vaut le coup.
- Sorties : nouveaux films et séries.
- Genève Sorties : concerts et événements à Genève.

### 🎮 7. Jeux vidéo — Commandant Gaming
- Promo : jeux en solde.
- Patch : résume les mises à jour des jeux.
- Mods : trouve des mods (Forza…).
- Coach : astuces et guides.
- Launcher 🍎/🪟 : Steam / Steam, Epic, app Xbox.

### 🧹 8. Entretien — Commandant Maintenance
- Rangeur : trie mes fichiers.
- Nettoyeur 🍎/🪟 : caches du Mac / fichiers temporaires Windows.
- Sauvegarde 🍎/🪟 : Time Machine / OneDrive.
- Thermomètre 🍎/🪟 : température de l'ordinateur.
- Éclairagiste 🍎/🪟 : thème et fond d'écran / LED RGB.

### 📅 9. Organisation — Commandant Secrétariat
- Agenda 🍎/🪟 : Calendrier Apple / Google.
- Rappels 🍎/🪟 : Rappels Apple / Outlook.
- Courrier : trie mes mails Gmail.
- Météo : météo de Genève.
- Briefing : résumé du matin.

### 🚀 10. Création — Commandant Atelier
- Codeur : pilote Claude Code pour mes projets.
- Designer : crée des designs style Liquid Glass.
- Idées : propose de nouveaux projets.
- Débugueur : trouve les bugs.
- Chef de projet : suit l'avancement de mes projets.

## Règles de sécurité
- Ne jamais supprimer un fichier, acheter quelque chose ou envoyer un mail sans me demander d'abord.
- Les agents Bourse informent, ils ne passent jamais d'ordre d'achat ou de vente.
