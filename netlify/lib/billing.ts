import Stripe from 'stripe'
import type { SupabaseClient } from '@supabase/supabase-js'

// Paiements Stripe. Tout reste désactivé tant que STRIPE_SECRET_KEY et les
// identifiants de prix ne sont pas renseignés dans Netlify.

export type Interval = 'monthly' | 'yearly'
export type Currency = 'CHF' | 'EUR'

export function billingEnv() {
  return {
    secretKey: process.env.STRIPE_SECRET_KEY,
    webhookSecret: process.env.STRIPE_WEBHOOK_SECRET,
    automaticTax: process.env.STRIPE_AUTOMATIC_TAX === '1',
    prices: {
      CHF: { monthly: process.env.STRIPE_PRICE_CHF_MONTHLY, yearly: process.env.STRIPE_PRICE_CHF_YEARLY },
      EUR: { monthly: process.env.STRIPE_PRICE_EUR_MONTHLY, yearly: process.env.STRIPE_PRICE_EUR_YEARLY },
    } as Record<Currency, Record<Interval, string | undefined>>,
  }
}

let stripe: Stripe | null | undefined
export function getStripe(): Stripe | null {
  if (stripe !== undefined) return stripe
  const { secretKey } = billingEnv()
  stripe = secretKey ? new Stripe(secretKey) : null
  return stripe
}

export function priceFor(currency: string, interval: string): string | null {
  const { prices } = billingEnv()
  if (currency !== 'CHF' && currency !== 'EUR') return null
  if (interval !== 'monthly' && interval !== 'yearly') return null
  return prices[currency][interval] ?? null
}

export function billingEnabled(): boolean {
  const env = billingEnv()
  return !!env.secretKey && !!env.webhookSecret && Object.values(env.prices).some((p) => p.monthly || p.yearly)
}

// Un abonnement « actif », « en essai » ou « paiement en retard » (Stripe réessaie
// pendant quelques jours) donne accès au Premium. Sinon : retour au Gratuit.
const PREMIUM_STATUSES = new Set<Stripe.Subscription.Status>(['active', 'trialing', 'past_due'])

export function planFromSubscription(sub: Pick<Stripe.Subscription, 'status' | 'items' | 'cancel_at'>) {
  const premium = PREMIUM_STATUSES.has(sub.status)
  const ends = sub.items?.data?.map((i) => i.current_period_end).filter(Boolean) ?? []
  const periodEnd = ends.length ? Math.max(...ends) : null
  return {
    plan: premium ? ('premium' as const) : ('free' as const),
    plan_renews_at: premium && periodEnd ? new Date(periodEnd * 1000).toISOString() : null,
  }
}

// Met à jour le plan d'un client après un événement Stripe.
export async function syncSubscription(db: SupabaseClient, sub: Stripe.Subscription) {
  const customerId = typeof sub.customer === 'string' ? sub.customer : sub.customer.id
  const userId = sub.metadata?.user_id
  const update = { ...planFromSubscription(sub), stripe_customer_id: customerId, stripe_subscription_id: sub.id }
  const query = db.from('profiles').update(update)
  const { error } = userId ? await query.eq('id', userId) : await query.eq('stripe_customer_id', customerId)
  if (error) throw new Error(`profiles update: ${error.message}`)
  return update
}

export async function handleStripeEvent(event: Stripe.Event, db: SupabaseClient, stripeClient: Stripe) {
  switch (event.type) {
    case 'checkout.session.completed': {
      const session = event.data.object
      if (session.mode !== 'subscription' || !session.subscription) return 'ignored'
      const subId = typeof session.subscription === 'string' ? session.subscription : session.subscription.id
      const sub = await stripeClient.subscriptions.retrieve(subId)
      // Le compte est identifié par client_reference_id, posé à la création du paiement.
      if (!sub.metadata?.user_id && session.client_reference_id) sub.metadata = { ...sub.metadata, user_id: session.client_reference_id }
      await syncSubscription(db, sub)
      return 'synced'
    }
    case 'customer.subscription.created':
    case 'customer.subscription.updated':
    case 'customer.subscription.deleted':
    case 'customer.subscription.paused':
    case 'customer.subscription.resumed':
      await syncSubscription(db, event.data.object)
      return 'synced'
    default:
      return 'ignored'
  }
}
