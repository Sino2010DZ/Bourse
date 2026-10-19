// Variables secrètes : lues UNIQUEMENT côté serveur (fonctions Netlify).
// Elles ne commencent jamais par VITE_ et n'arrivent donc jamais dans le navigateur.
export const serverEnv = () => ({
  supabaseUrl: process.env.SUPABASE_URL ?? process.env.VITE_SUPABASE_URL,
  supabaseServiceKey: process.env.SUPABASE_SERVICE_ROLE_KEY,
  eodhdKey: process.env.EODHD_API_KEY,
  quotesDemo: process.env.QUOTES_DEMO === '1',
  vapidPublic: process.env.VAPID_PUBLIC_KEY ?? process.env.VITE_VAPID_PUBLIC_KEY,
  vapidPrivate: process.env.VAPID_PRIVATE_KEY,
  vapidSubject: process.env.VAPID_SUBJECT ?? 'mailto:contact@example.com',
})
