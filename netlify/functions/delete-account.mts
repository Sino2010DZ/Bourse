import type { Config } from '@netlify/functions'
import { supabaseAdmin } from '../lib/supabaseAdmin'

// Droit à l'effacement (nLPD / RGPD) : supprime le compte de l'utilisateur
// connecté et, par cascade, toutes ses données.
export default async (req: Request) => {
  if (req.method !== 'POST') return new Response('Method not allowed', { status: 405 })
  const db = supabaseAdmin()
  const token = req.headers.get('authorization')?.replace(/^Bearer\s+/i, '')
  if (!db || !token) return new Response('Unauthorized', { status: 401 })

  const { data, error } = await db.auth.getUser(token)
  if (error || !data.user) return new Response('Unauthorized', { status: 401 })

  const { error: delError } = await db.auth.admin.deleteUser(data.user.id)
  if (delError) {
    console.error('delete-account', delError)
    return new Response('Error', { status: 500 })
  }
  return new Response(null, { status: 204 })
}

export const config: Config = { path: '/api/delete-account' }
