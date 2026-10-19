import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'

// Le paiement est-il branché côté serveur ? (clés Stripe présentes dans Netlify)
export function useBillingEnabled() {
  const [enabled, setEnabled] = useState(false)
  useEffect(() => {
    fetch('/api/billing')
      .then((r) => (r.ok ? r.json() : { enabled: false }))
      .then((d: { enabled?: boolean }) => setEnabled(!!d.enabled))
      .catch(() => setEnabled(false))
  }, [])
  return enabled
}

async function post(path: string, session: Session, body?: unknown): Promise<string> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = (await res.json().catch(() => ({}))) as { url?: string }
  if (!res.ok || !data.url) throw new Error(String(res.status))
  return data.url
}

export const startCheckout = (session: Session, currency: string, interval: 'monthly' | 'yearly') =>
  post('/api/billing/checkout', session, { currency, interval })

export const openPortal = (session: Session) => post('/api/billing/portal', session)
