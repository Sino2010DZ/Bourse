import type { Config } from '@netlify/functions'
import { billingEnabled, billingEnv, getStripe, priceFor } from '../lib/billing'
import { jsonResponse, userFromRequest } from '../lib/auth'
import { supabaseAdmin } from '../lib/supabaseAdmin'

// GET  /api/billing           → { enabled } : le paiement est-il branché ?
// POST /api/billing/checkout  → { url } : page de paiement Stripe
// POST /api/billing/portal    → { url } : espace client (factures, résiliation)
export default async (req: Request) => {
  const url = new URL(req.url)
  const action = url.pathname.split('/').pop()
  if (req.method === 'GET') return jsonResponse({ enabled: billingEnabled() })
  if (req.method !== 'POST') return jsonResponse({ error: 'method' }, 405)

  const stripe = getStripe()
  const db = supabaseAdmin()
  if (!billingEnabled() || !stripe || !db) return jsonResponse({ error: 'billing disabled' }, 503)

  const user = await userFromRequest(req)
  if (!user) return jsonResponse({ error: 'unauthorized' }, 401)

  // L'adresse du site est déduite de la requête : rien à changer avec un nouveau domaine.
  const origin = url.origin
  const { data: profile } = await db.from('profiles').select('stripe_customer_id,locale').eq('id', user.id).maybeSingle()

  if (action === 'portal') {
    if (!profile?.stripe_customer_id) return jsonResponse({ error: 'no customer' }, 400)
    const session = await stripe.billingPortal.sessions.create({ customer: profile.stripe_customer_id, return_url: `${origin}/account` })
    return jsonResponse({ url: session.url })
  }

  if (action === 'checkout') {
    const body = (await req.json().catch(() => ({}))) as { currency?: string; interval?: string }
    const price = priceFor(body.currency ?? 'CHF', body.interval ?? 'monthly')
    if (!price) return jsonResponse({ error: 'unknown price' }, 400)

    let customer = profile?.stripe_customer_id as string | undefined
    if (!customer) {
      const created = await stripe.customers.create({ email: user.email, metadata: { user_id: user.id } })
      customer = created.id
      await db.from('profiles').update({ stripe_customer_id: customer }).eq('id', user.id)
    }
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      customer,
      client_reference_id: user.id,
      line_items: [{ price, quantity: 1 }],
      subscription_data: { metadata: { user_id: user.id } },
      allow_promotion_codes: true,
      automatic_tax: { enabled: billingEnv().automaticTax },
      ...(billingEnv().automaticTax ? { customer_update: { address: 'auto' as const } } : {}),
      locale: profile?.locale === 'en' ? 'en' : 'fr',
      success_url: `${origin}/account?checkout=success`,
      cancel_url: `${origin}/pricing`,
    })
    return jsonResponse({ url: session.url })
  }

  return jsonResponse({ error: 'not found' }, 404)
}

export const config: Config = { path: ['/api/billing', '/api/billing/checkout', '/api/billing/portal'] }
