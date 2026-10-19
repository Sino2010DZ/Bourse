import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { env } from '../config'

// La clé « anon » est publique par conception : la sécurité est assurée par les
// règles RLS de la base (chaque utilisateur ne voit que ses propres lignes).
export const supabase: SupabaseClient | null =
  env.supabaseUrl && env.supabaseAnonKey ? createClient(env.supabaseUrl, env.supabaseAnonKey) : null
