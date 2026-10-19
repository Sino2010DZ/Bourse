// Réglages généraux de l'application.
// Le nom du site se change dans src/brand.ts.
export { APP_NAME } from './brand'

export type Plan = 'free' | 'premium'

// Attention : la limite de 5 est aussi écrite dans supabase/migrations/001_init.sql
export const PLAN_LIMITS = {
  free: { watchlist: 5, alerts: false, portfolio: false, ads: true },
  premium: { watchlist: Infinity, alerts: true, portfolio: true, ads: false },
} as const

export const PRICES = {
  CHF: { monthly: 9.9, yearly: 89 },
  EUR: { monthly: 9.9, yearly: 89 },
} as const

// Rafraîchissement automatique des prix (1 minute)
export const REFRESH_MS = 60_000

export const env = {
  supabaseUrl: import.meta.env.VITE_SUPABASE_URL as string | undefined,
  supabaseAnonKey: import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined,
  vapidPublicKey: import.meta.env.VITE_VAPID_PUBLIC_KEY as string | undefined,
  adsenseClient: import.meta.env.VITE_ADSENSE_CLIENT as string | undefined,
  // Débloque Premium en mode invité, uniquement pour les tests locaux.
  testHooks: import.meta.env.DEV || import.meta.env.VITE_E2E === '1',
}

// À compléter avant l'ouverture au public (utilisé dans les pages légales).
export const LEGAL = {
  owner: '[Votre nom ou raison sociale]',
  address: '[Adresse postale, NPA Ville, Suisse]',
  email: '[contact@votredomaine.com]',
  court: '[Ville du for juridique, ex. Genève]',
  updated: '2026-10-19',
}
