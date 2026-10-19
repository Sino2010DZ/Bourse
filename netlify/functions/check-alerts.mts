import type { Config } from '@netlify/functions'
import webpush from 'web-push'
import { getProvider } from '../lib/providers'
import { getQuotes } from '../lib/quoteCache'
import { supabaseAdmin } from '../lib/supabaseAdmin'
import { serverEnv } from '../lib/env'
import { shouldTrigger } from '../../src/lib/alerts'
import { displayTicker } from '../../src/lib/symbols'
import type { AlertDirection } from '../../src/lib/types'

interface AlertRow { id: string; user_id: string; symbol: string; direction: AlertDirection; target: number }
interface SubRow { id: string; user_id: string; endpoint: string; p256dh: string; auth: string }

const TEXT = {
  fr: { above: 'a dépassé', below: 'est passé sous' },
  en: { above: 'rose above', below: 'fell below' },
}

// Tourne automatiquement chaque minute : vérifie les alertes actives et
// envoie une notification quand le prix cible est atteint.
export default async () => {
  const env = serverEnv()
  const db = supabaseAdmin()
  const provider = getProvider()
  if (!db || !provider || !env.vapidPrivate || !env.vapidPublic) {
    console.log('check-alerts: configuration incomplète, rien à faire')
    return
  }
  webpush.setVapidDetails(env.vapidSubject, env.vapidPublic, env.vapidPrivate)

  const { data: alerts } = await db.from('price_alerts').select('id,user_id,symbol,direction,target').eq('active', true).limit(5000)
  if (!alerts?.length) return

  const quotes = await getQuotes([...new Set(alerts.map((a) => a.symbol as string))], provider, db)
  const hits = (alerts as AlertRow[]).filter((a) => quotes[a.symbol] && shouldTrigger(a.direction, Number(a.target), quotes[a.symbol].price))
  if (!hits.length) return

  const userIds = [...new Set(hits.map((h) => h.user_id))]
  const [{ data: subs }, { data: profiles }] = await Promise.all([
    db.from('push_subscriptions').select('id,user_id,endpoint,p256dh,auth').in('user_id', userIds),
    db.from('profiles').select('id,locale').in('id', userIds),
  ])
  const localeOf = new Map((profiles ?? []).map((p) => [p.id as string, p.locale === 'en' ? 'en' : 'fr'] as const))

  for (const alert of hits) {
    const price = quotes[alert.symbol].price
    // On désactive d'abord : une alerte ne sonne qu'une fois.
    const { data: updated } = await db.from('price_alerts')
      .update({ active: false, triggered_at: new Date().toISOString(), triggered_price: price })
      .eq('id', alert.id).eq('active', true).select('id')
    if (!updated?.length) continue

    const words = TEXT[localeOf.get(alert.user_id) ?? 'fr']
    const payload = JSON.stringify({
      title: `${displayTicker(alert.symbol)} ${words[alert.direction]} ${alert.target}`,
      body: `${displayTicker(alert.symbol)} : ${price}`,
      url: `/s/${encodeURIComponent(alert.symbol)}`,
      tag: alert.id,
    })
    for (const sub of (subs ?? []) as SubRow[]) {
      if (sub.user_id !== alert.user_id) continue
      try {
        await webpush.sendNotification({ endpoint: sub.endpoint, keys: { p256dh: sub.p256dh, auth: sub.auth } }, payload)
      } catch (err) {
        const code = (err as { statusCode?: number }).statusCode
        // Appareil désinscrit : on l'oublie.
        if (code === 404 || code === 410) await db.from('push_subscriptions').delete().eq('id', sub.id)
        else console.error('push', code, err)
      }
    }
  }
  console.log(`check-alerts: ${hits.length} alerte(s) déclenchée(s)`)
}

export const config: Config = { schedule: '* * * * *' }
