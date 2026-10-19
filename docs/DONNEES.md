# Les données de marché et leur licence

## Ce qui est utilisé aujourd’hui : TradingView (gratuit)

Les **graphiques**, les **prix de la watchlist**, le **bandeau défilant** et les **actualités**
sont des *widgets gratuits* de TradingView. C’est TradingView qui détient les licences des
bourses (dont la SIX suisse) et qui les paie. Leur usage est autorisé sur un site commercial,
**à condition de laisser visibles le logo et le lien TradingView**. Ne les retirez pas.

Ce qui est **interdit** : récupérer (« aspirer ») les chiffres de TradingView pour les
réutiliser ailleurs. Le site ne le fait pas.

## La limite : les calculs côté serveur

Les widgets affichent les prix, mais notre code ne peut pas les lire. Pour **calculer la valeur
du portefeuille** et **surveiller les alertes**, le serveur a besoin de sa propre source de prix.

Le code est prêt pour **EODHD** (US + SIX + Europe + cryptos, retard de 15 min) :

1. Créez un compte sur https://eodhd.com.
2. Pour les tests, le forfait personnel suffit (~20 $/mois).
3. **Avant d’ouvrir le Premium au public**, il faut une licence commerciale (forfait *Custom*
   dès ~399 $/mois). Demandez-leur par écrit l’autorisation d’afficher les cours retardés
   US, SIX, Xetra et Euronext à des abonnés payants, et si les frais SIX sont compris.
4. Dans Netlify, ajoutez la variable secrète `EODHD_API_KEY`.

Dès que la clé est là, tout s’active tout seul : prix calculés par le serveur, totaux et gains
du portefeuille, alertes surveillées chaque minute.

**Conseil** : lancez d’abord le plan Gratuit (coût des données : 0), puis activez le Premium
quand les premiers abonnés couvrent le prix de la licence.

## Le cache (pour ne pas dépasser les limites)

- Les prix serveur sont gardés **60 secondes** : en mémoire, dans la table `quote_cache`
  de Supabase, et dans le cache du réseau Netlify.
- 1 000 visiteurs qui regardent Nestlé dans la même minute = **1 seul** appel au fournisseur.
- Le site se rafraîchit automatiquement **toutes les minutes**.
