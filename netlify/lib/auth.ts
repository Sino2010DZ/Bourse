import type { User } from '@supabase/supabase-js'
import { supabaseAdmin } from './supabaseAdmin'

// Retrouve l'utilisateur connecté à partir de son jeton (en-tête Authorization).
export async function userFromRequest(req: Request): Promise<User | null> {
  const db = supabaseAdmin()
  const token = req.headers.get('authorization')?.replace(/^Bearer\s+/i, '')
  if (!db || !token) return null
  const { data, error } = await db.auth.getUser(token)
  return error ? null : data.user
}

export const jsonResponse = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } })
