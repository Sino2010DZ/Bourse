import type { SupabaseClient } from '@supabase/supabase-js'
import type { Quote } from '../../src/lib/types'
import type { QuoteProvider } from './providers'

export const QUOTE_TTL_MS = 60_000

// Cache à deux niveaux : mémoire de la fonction + table Supabase « quote_cache »
// (partagée entre toutes les instances). On n'interroge le fournisseur que pour
// les symboles absents ou plus vieux qu'une minute.
const memory = new Map<string, { quote: Quote; fetchedAt: number }>()

export function clearMemoryCache() {
  memory.clear()
}

export async function getQuotes(
  symbols: string[],
  provider: QuoteProvider,
  db: SupabaseClient | null,
  now = Date.now(),
): Promise<Record<string, Quote>> {
  const result: Record<string, Quote> = {}
  let missing: string[] = []

  for (const s of symbols) {
    const hit = memory.get(s)
    if (hit && now - hit.fetchedAt < QUOTE_TTL_MS) result[s] = hit.quote
    else missing.push(s)
  }

  if (missing.length && db) {
    const { data } = await db.from('quote_cache').select('symbol,price,change_pct,prev_close,quote_time,fetched_at').in('symbol', missing)
    for (const row of data ?? []) {
      const fetchedAt = new Date(row.fetched_at as string).getTime()
      if (now - fetchedAt >= QUOTE_TTL_MS) continue
      const quote: Quote = {
        symbol: row.symbol as string,
        price: Number(row.price),
        changePct: Number(row.change_pct),
        prevClose: row.prev_close === null ? null : Number(row.prev_close),
        time: new Date(row.quote_time as string).getTime(),
      }
      result[quote.symbol] = quote
      memory.set(quote.symbol, { quote, fetchedAt })
    }
    missing = missing.filter((s) => !result[s])
  }

  if (missing.length) {
    const fresh = await provider.fetchQuotes(missing)
    const rows = Object.values(fresh).map((q) => {
      result[q.symbol] = q
      memory.set(q.symbol, { quote: q, fetchedAt: now })
      return {
        symbol: q.symbol, price: q.price, change_pct: q.changePct, prev_close: q.prevClose,
        quote_time: new Date(q.time).toISOString(), fetched_at: new Date(now).toISOString(),
      }
    })
    if (rows.length && db) await db.from('quote_cache').upsert(rows)
  }

  return result
}
