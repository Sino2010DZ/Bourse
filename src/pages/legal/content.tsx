import type { ReactNode } from 'react'
import { APP_NAME, LEGAL } from '../../config'
import type { Lang } from '../../i18n'

// Textes juridiques de base (droit suisse nLPD + RGPD européen).
// À faire relire par un juriste avant le lancement commercial.

const { owner, address, email, court } = LEGAL

const termsFr = (
  <>
    <h2>1. Objet</h2>
    <p>{APP_NAME} (le « Service ») est une plateforme de suivi des marchés financiers éditée par {owner}, {address} (« nous »). Les présentes conditions régissent l’utilisation du Service.</p>
    <h2>2. Pas de conseil en investissement</h2>
    <p><strong>Informations non contractuelles, ceci n’est pas un conseil en investissement.</strong> Le Service fournit des informations à titre purement indicatif. Il ne constitue ni une recommandation, ni une offre, ni une sollicitation d’achat ou de vente d’un instrument financier. Vous êtes seul responsable de vos décisions d’investissement. Investir comporte des risques, y compris la perte du capital.</p>
    <h2>3. Données de marché</h2>
    <p>Les cours, graphiques et actualités sont fournis par des tiers (notamment TradingView) et peuvent être retardés d’environ 15 minutes, incomplets ou erronés. Nous ne garantissons ni leur exactitude, ni leur disponibilité. Les alertes de prix sont envoyées sans garantie de délai ni de réception.</p>
    <h2>4. Compte</h2>
    <p>Vous devez fournir une adresse e-mail valide et garder votre mot de passe confidentiel. Vous pouvez supprimer votre compte à tout moment depuis la page Compte.</p>
    <h2>5. Plans et abonnement</h2>
    <p>Le plan Gratuit est limité (watchlist de 5 valeurs, sans alertes ni portefeuille) et affiche de la publicité. Le plan Premium est payant, mensuel ou annuel, renouvelé automatiquement et résiliable à tout moment pour la fin de la période en cours. Les prix sont indiqués TTC sur la page Premium.</p>
    <h2>6. Utilisation acceptable</h2>
    <p>Il est interdit d’extraire les données de manière automatisée, de revendre l’accès au Service ou de perturber son fonctionnement.</p>
    <h2>7. Responsabilité</h2>
    <p>Dans les limites permises par la loi, notre responsabilité est exclue pour tout dommage résultant de l’utilisation du Service ou des informations qu’il contient, en particulier les pertes financières.</p>
    <h2>8. Modifications</h2>
    <p>Nous pouvons modifier ces conditions. Les changements importants vous seront signalés.</p>
    <h2>9. Droit applicable</h2>
    <p>Droit suisse. For juridique : {court}, sous réserve des dispositions impératives protégeant les consommateurs.</p>
    <h2>10. Contact</h2>
    <p>{email}</p>
  </>
)

const termsEn = (
  <>
    <h2>1. Purpose</h2>
    <p>{APP_NAME} (the “Service”) is a market-tracking platform published by {owner}, {address} (“we”). These terms govern your use of the Service.</p>
    <h2>2. No investment advice</h2>
    <p><strong>Information is non-binding and does not constitute investment advice.</strong> The Service is for information only. Nothing on it is a recommendation, offer or solicitation to buy or sell any financial instrument. You are solely responsible for your investment decisions. Investing involves risk, including loss of capital.</p>
    <h2>3. Market data</h2>
    <p>Prices, charts and news are provided by third parties (including TradingView) and may be delayed by about 15 minutes, incomplete or inaccurate. We do not guarantee their accuracy or availability. Price alerts are sent without any guarantee of timing or delivery.</p>
    <h2>4. Account</h2>
    <p>You must provide a valid email address and keep your password confidential. You can delete your account at any time from the Account page.</p>
    <h2>5. Plans and subscription</h2>
    <p>The Free plan is limited (5-symbol watchlist, no alerts or portfolio) and shows ads. The Premium plan is paid monthly or yearly, renews automatically and can be cancelled at any time, effective at the end of the current period. Prices include VAT and are shown on the Premium page.</p>
    <h2>6. Acceptable use</h2>
    <p>Automated extraction of data, reselling access to the Service, or disrupting it is prohibited.</p>
    <h2>7. Liability</h2>
    <p>To the extent permitted by law, we accept no liability for any damage resulting from use of the Service or its information, in particular financial losses.</p>
    <h2>8. Changes</h2>
    <p>We may update these terms. Material changes will be notified to you.</p>
    <h2>9. Governing law</h2>
    <p>Swiss law. Place of jurisdiction: {court}, subject to mandatory consumer protection rules.</p>
    <h2>10. Contact</h2>
    <p>{email}</p>
  </>
)

const privacyFr = (
  <>
    <h2>1. Responsable du traitement</h2>
    <p>{owner}, {address}, {email}. Cette politique respecte la loi fédérale suisse sur la protection des données (nLPD) et, pour les utilisateurs de l’Union européenne, le RGPD.</p>
    <h2>2. Données traitées</h2>
    <ul>
      <li>Compte : adresse e-mail, mot de passe (chiffré, jamais lisible par nous), date d’inscription, plan.</li>
      <li>Contenu : watchlist, positions du portefeuille, alertes de prix.</li>
      <li>Notifications : identifiant technique de votre appareil, si vous les activez.</li>
      <li>Préférences : langue, thème, choix cookies (stockés sur votre appareil).</li>
      <li>Paiement (plan Premium) : traité par Stripe ; nous ne voyons jamais votre numéro de carte.</li>
    </ul>
    <h2>3. Finalités et bases légales</h2>
    <p>Fournir le Service (exécution du contrat), envoyer les alertes demandées, sécuriser le Service (intérêt légitime), afficher de la publicité personnalisée uniquement avec votre consentement.</p>
    <h2>4. Sous-traitants et transferts</h2>
    <ul>
      <li>Supabase (base de données et comptes, région UE).</li>
      <li>Netlify (hébergement du site, États-Unis : clauses contractuelles types).</li>
      <li>TradingView (graphiques et données intégrés : TradingView reçoit votre adresse IP lorsque les widgets se chargent).</li>
      <li>Google AdSense (publicité, plan gratuit, seulement après consentement).</li>
      <li>Stripe (paiements).</li>
    </ul>
    <h2>5. Cookies et stockage local</h2>
    <p>Nécessaires : session de connexion, langue, thème, choix cookies. Publicité : cookies Google AdSense, uniquement si vous les acceptez. Vous pouvez changer d’avis à tout moment via « Paramètres des cookies » en bas de page.</p>
    <h2>6. Durée de conservation</h2>
    <p>Tant que votre compte existe. À la suppression du compte, vos données sont effacées, sauf obligation légale de conservation (ex. factures : 10 ans).</p>
    <h2>7. Vos droits</h2>
    <p>Accès, rectification, effacement, portabilité, opposition et retrait du consentement : écrivez à {email}. Vous pouvez aussi saisir le Préposé fédéral à la protection des données (PFPDT) ou l’autorité de votre pays dans l’UE.</p>
  </>
)

const privacyEn = (
  <>
    <h2>1. Controller</h2>
    <p>{owner}, {address}, {email}. This policy follows the Swiss Federal Act on Data Protection (FADP) and, for users in the European Union, the GDPR.</p>
    <h2>2. Data we process</h2>
    <ul>
      <li>Account: email address, password (hashed, never readable by us), sign-up date, plan.</li>
      <li>Content: watchlist, portfolio positions, price alerts.</li>
      <li>Notifications: a technical identifier for your device, if you enable them.</li>
      <li>Preferences: language, theme, cookie choices (stored on your device).</li>
      <li>Payment (Premium plan): processed by Stripe; we never see your card number.</li>
    </ul>
    <h2>3. Purposes and legal bases</h2>
    <p>Providing the Service (contract), sending the alerts you request, securing the Service (legitimate interest), showing personalised ads only with your consent.</p>
    <h2>4. Processors and transfers</h2>
    <ul>
      <li>Supabase (database and accounts, EU region).</li>
      <li>Netlify (website hosting, United States: standard contractual clauses).</li>
      <li>TradingView (embedded charts and data: TradingView receives your IP address when widgets load).</li>
      <li>Google AdSense (ads, free plan, only after consent).</li>
      <li>Stripe (payments).</li>
    </ul>
    <h2>5. Cookies and local storage</h2>
    <p>Necessary: login session, language, theme, cookie choices. Advertising: Google AdSense cookies, only if you accept them. You can change your mind at any time via “Cookie settings” at the bottom of the page.</p>
    <h2>6. Retention</h2>
    <p>As long as your account exists. When you delete your account, your data is erased unless the law requires us to keep it (e.g. invoices: 10 years).</p>
    <h2>7. Your rights</h2>
    <p>Access, rectification, erasure, portability, objection and withdrawal of consent: write to {email}. You may also contact the Swiss Federal Data Protection and Information Commissioner (FDPIC) or your EU supervisory authority.</p>
  </>
)

// Une langue sans texte juridique traduit retombe sur l'anglais.
export const LEGAL_CONTENT: Record<'terms' | 'privacy', Partial<Record<Lang, ReactNode>> & { en: ReactNode }> = {
  terms: { fr: termsFr, en: termsEn },
  privacy: { fr: privacyFr, en: privacyEn },
}
