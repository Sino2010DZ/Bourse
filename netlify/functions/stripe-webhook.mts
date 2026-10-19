import type { Config } from '@netlify/functions'
import { billingEnv, getStripe, handleStripeEvent } from '../lib/billing'
import { supabaseAdmin } from '../lib/supabaseAdmin'

// Stripe appelle cette adresse après chaque paiement, renouvellement ou résiliation.
// La signature est vérifiée : personne d'autre ne peut se donner le Premium.
export default async (req: Request) => {
  const stripe = getStripe()
  const db = supabaseAdmin()
  const secret = billingEnv().webhookSecret
  if (!stripe || !db || !secret) return new Response('billing disabled', { status: 503 })

  const signature = req.headers.get('stripe-signature')
  if (!signature) return new Response('missing signature', { status: 400 })

  let event
  try {
    event = await stripe.webhooks.constructEventAsync(await req.text(), signature, secret)
  } catch {
    return new Response('invalid signature', { status: 400 })
  }

  try {
    const result = await handleStripeEvent(event, db, stripe)
    return new Response(JSON.stringify({ received: true, result }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  } catch (err) {
    console.error('stripe-webhook', event.type, err)
    // 500 : Stripe réessaiera automatiquement plus tard.
    return new Response('error', { status: 500 })
  }
}

export const config: Config = { path: '/api/stripe-webhook' }
