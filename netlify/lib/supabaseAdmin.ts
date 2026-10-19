import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { serverEnv } from './env'

let client: SupabaseClient | null | undefined

// Client « administrateur » (clé service_role) : contourne les règles RLS,
// donc à n'utiliser que dans les fonctions serveur.
export function supabaseAdmin(): SupabaseClient | null {
  if (client !== undefined) return client
  const { supabaseUrl, supabaseServiceKey } = serverEnv()
  client = supabaseUrl && supabaseServiceKey
    ? createClient(supabaseUrl, supabaseServiceKey, { auth: { persistSession: false, autoRefreshToken: false } })
    : null
  return client
}
