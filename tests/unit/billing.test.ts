import { afterEach, describe, expect, it, vi } from 'vitest'
import Stripe from 'stripe'
import type { SupabaseClient } from '@supabase/supabase-js'
import { handleStripeEvent, planFromSubscription, priceFor } from '../../netlify/lib/billing'
import billingHandler from '../../netlify/functions/billing.mts'
import webhookHandler from '../../netlify/functions/stripe-webhook.mts'

const sub = (status: Stripe.Subscription.Status, end = 1_800_000_000, metadata: Record<string, string> = { user_id: 'u1' }) =>
  ({ id: 'sub_1', status, customer: 'cus_1', metadata, cancel_at: null, items: { data: [{ current_period_end: end }] } }) as unknown as Stripe.Subscription

// Fausse base : enregistre les mises à jour demandées.
function fakeDb() {
  const updates: { values: Record<string, unknown>; col: string; val: string }[] = []
  const db = {
    from: () => ({
      update: (values: Record<string, unknown>) => ({
        eq: async (col: string, val: string) => { updates.push({ values, col, val }); return { error: null } },
      }),
    }),
  } as unknown as SupabaseClient
  return { db, updates }
}

describe('plan selon l’abonnement Stripe', () => {
  it('actif, en essai ou paiement en retard → Premium', () => {
    for (const s of ['active', 'trialing', 'past_due'] as const) expect(planFromSubscription(sub(s)).plan).toBe('premium')
    expect(planFromSubscription(sub('active')).plan_renews_at).toBe(new Date(1_800_000_000_000).toISOString())
  })
  it('résilié, impayé ou incomplet → Gratuit', () => {
    for (const s of ['canceled', 'unpaid', 'incomplete', 'incomplete_expired', 'paused'] as const) {
      expect(planFromSubscription(sub(s))).toEqual({ plan: 'free', plan_renews_at: null })
    }
  })
})

describe('événements Stripe', () => {
  it('abonnement mis à jour → profil mis à jour', async () => {
    const { db, updates } = fakeDb()
    const event = { type: 'customer.subscription.updated', data: { object: sub('active') } } as unknown as Stripe.Event
    expect(await handleStripeEvent(event, db, {} as Stripe)).toBe('synced')
    expect(updates[0]).toMatchObject({ col: 'id', val: 'u1', values: { plan: 'premium', stripe_customer_id: 'cus_1', stripe_subscription_id: 'sub_1' } })
  })
  it('abonnement supprimé → retour au Gratuit', async () => {
    const { db, updates } = fakeDb()
    await handleStripeEvent({ type: 'customer.subscription.deleted', data: { object: sub('canceled') } } as unknown as Stripe.Event, db, {} as Stripe)
    expect(updates[0].values.plan).toBe('free')
  })
  it('paiement terminé : retrouve le compte grâce à client_reference_id', async () => {
    const { db, updates } = fakeDb()
    const stripe = { subscriptions: { retrieve: vi.fn(async () => sub('active', 1_800_000_000, {})) } } as unknown as Stripe
    const event = { type: 'checkout.session.completed', data: { object: { mode: 'subscription', subscription: 'sub_1', client_reference_id: 'u9' } } } as unknown as Stripe.Event
    await handleStripeEvent(event, db, stripe)
    expect(updates[0]).toMatchObject({ col: 'id', val: 'u9', values: { plan: 'premium' } })
  })
  it('sans identifiant de compte : retrouve par client Stripe', async () => {
    const { db, updates } = fakeDb()
    await handleStripeEvent({ type: 'customer.subscription.created', data: { object: sub('active', 1, {}) } } as unknown as Stripe.Event, db, {} as Stripe)
    expect(updates[0]).toMatchObject({ col: 'stripe_customer_id', val: 'cus_1' })
  })
  it('ignore les autres événements', async () => {
    const { db, updates } = fakeDb()
    expect(await handleStripeEvent({ type: 'invoice.created', data: { object: {} } } as unknown as Stripe.Event, db, {} as Stripe)).toBe('ignored')
    expect(updates).toHaveLength(0)
  })
})

describe('fonctions de paiement', () => {
  const saved = { ...process.env }
  afterEach(() => { process.env = { ...saved }; vi.resetModules() })

  it('sans clés Stripe : paiement désactivé, sans erreur', async () => {
    const res = await billingHandler(new Request('http://x/api/billing'))
    expect(await res.json()).toEqual({ enabled: false })
    const post = await billingHandler(new Request('http://x/api/billing/checkout', { method: 'POST' }))
    expect(post.status).toBe(503)
  })

  it('prix : seulement CHF / EUR, mensuel / annuel', () => {
    process.env.STRIPE_PRICE_CHF_MONTHLY = 'price_chf_m'
    expect(priceFor('CHF', 'monthly')).toBe('price_chf_m')
    expect(priceFor('USD', 'monthly')).toBeNull()
    expect(priceFor('CHF', 'weekly')).toBeNull()
  })

  it('webhook : refuse une fausse signature (personne ne peut se donner le Premium)', async () => {
    process.env.STRIPE_SECRET_KEY = 'sk_test_x'
    process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test_secret'
    process.env.SUPABASE_URL = 'http://localhost:54321'
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'service'
    const { default: handler } = await import('../../netlify/functions/stripe-webhook.mts')
    const payload = JSON.stringify({ id: 'evt_1', object: 'event', type: 'customer.subscription.updated', data: { object: sub('active') } })
    const forged = await handler(new Request('http://x/api/stripe-webhook', { method: 'POST', body: payload, headers: { 'stripe-signature': 't=1,v1=faux' } }))
    expect(forged.status).toBe(400)
    const unsigned = await handler(new Request('http://x/api/stripe-webhook', { method: 'POST', body: payload }))
    expect(unsigned.status).toBe(400)
  })

  it('webhook : accepte une vraie signature Stripe', async () => {
    process.env.STRIPE_SECRET_KEY = 'sk_test_x'
    process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test_secret'
    process.env.SUPABASE_URL = 'http://localhost:54321'
    process.env.SUPABASE_SERVICE_ROLE_KEY = 'service'
    const { default: handler } = await import('../../netlify/functions/stripe-webhook.mts')
    const payload = JSON.stringify({ id: 'evt_2', object: 'event', type: 'invoice.created', data: { object: {} } })
    const header = await new Stripe('sk_test_x').webhooks.generateTestHeaderStringAsync({ payload, secret: 'whsec_test_secret' })
    const res = await handler(new Request('http://x/api/stripe-webhook', { method: 'POST', body: payload, headers: { 'stripe-signature': header } }))
    expect(res.status).toBe(200)
    expect(await res.json()).toEqual({ received: true, result: 'ignored' })
    expect(webhookHandler).toBeTypeOf('function')
  })
})
