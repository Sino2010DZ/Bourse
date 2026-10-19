import type { Config } from '@netlify/functions'
import { supabaseAdmin } from '../lib/supabaseAdmin'
import { userFromRequest } from '../lib/auth'
import { getStripe } from '../lib/billing'

// Droit à l'effacement (nLPD / RGPD) : résilie l'abonnement éventuel, puis
// supprime le compte de l'utilisateur connecté et, par cascade, toutes ses données.
export default async (req: Request) => {
  if (req.method !== 'POST') return new Response('Method not allowed', { status: 405 })
  const db = supabaseAdmin()
  const user = await userFromRequest(req)
  if (!db || !user) return new Response('Unauthorized', { status: 401 })

  const { data: profile } = await db.from('profiles').select('stripe_subscription_id').eq('id', user.id).maybeSingle()
  const stripe = getStripe()
  if (stripe && profile?.stripe_subscription_id) {
    try {
      await stripe.subscriptions.cancel(profile.stripe_subscription_id)
    } catch (err) {
      console.error('delete-account: résiliation Stripe', err)
    }
  }

  const { error } = await db.auth.admin.deleteUser(user.id)
  if (error) {
    console.error('delete-account', error)
    return new Response('Error', { status: 500 })
  }
  return new Response(null, { status: 204 })
}

export const config: Config = { path: '/api/delete-account' }
