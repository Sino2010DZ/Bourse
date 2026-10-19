import type { Quote } from '../../src/lib/types'
import { getSymbol } from '../../src/lib/symbols'
import { serverEnv } from './env'

export interface QuoteProvider {
  name: string
  fetchQuotes(symbols: string[]): Promise<Record<string, Quote>>
}

interface EodRealtime {
  code: string
  timestamp: number | 'NA'
  close: number | 'NA'
  previousClose: number | 'NA'
  change_p: number | 'NA'
}

const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : null)

// EODHD : cours retardés ~15 min, US + SIX + Europe + cryptos.
// Licence commerciale nécessaire pour l'affichage public (voir docs/DONNEES.md).
export function eodhdProvider(apiKey: string, fetchImpl: typeof fetch = fetch): QuoteProvider {
  return {
    name: 'eodhd',
    async fetchQuotes(symbols) {
      const byEod = new Map<string, string>()
      for (const tv of symbols) {
        const eod = getSymbol(tv)?.eod
        if (eod) byEod.set(eod, tv)
      }
      const codes = [...byEod.keys()]
      const out: Record<string, Quote> = {}
      for (let i = 0; i < codes.length; i += 20) {
        const chunk = codes.slice(i, i + 20)
        const [first, ...rest] = chunk
        const url = new URL(`https://eodhd.com/api/real-time/${encodeURIComponent(first)}`)
        url.searchParams.set('api_token', apiKey)
        url.searchParams.set('fmt', 'json')
        if (rest.length) url.searchParams.set('s', rest.join(','))
        const res = await fetchImpl(url)
        if (!res.ok) throw new Error(`EODHD ${res.status}`)
        const body = (await res.json()) as EodRealtime | EodRealtime[]
        for (const r of Array.isArray(body) ? body : [body]) {
          const tv = byEod.get(r.code)
          const price = num(r.close)
          if (!tv || price === null) continue
          const prev = num(r.previousClose)
          out[tv] = {
            symbol: tv,
            price,
            prevClose: prev,
            changePct: num(r.change_p) ?? (prev ? ((price - prev) / prev) * 100 : 0),
            time: (num(r.timestamp) ?? Date.now() / 1000) * 1000,
          }
        }
      }
      return out
    },
  }
}

// Fournisseur de démonstration : prix FICTIFS, uniquement pour tester en local.
export function demoProvider(now: () => number = Date.now): QuoteProvider {
  const hash = (s: string) => [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7)
  return {
    name: 'demo',
    async fetchQuotes(symbols) {
      const minute = Math.floor(now() / 60_000)
      const out: Record<string, Quote> = {}
      for (const tv of symbols) {
        const h = hash(tv)
        const base = 20 + (h % 480)
        const prev = base
        const price = Math.round(base * (1 + Math.sin(minute / 7 + h) * 0.03) * 100) / 100
        out[tv] = { symbol: tv, price, prevClose: prev, changePct: ((price - prev) / prev) * 100, time: minute * 60_000 }
      }
      return out
    },
  }
}

export function getProvider(): QuoteProvider | null {
  const env = serverEnv()
  if (env.eodhdKey) return eodhdProvider(env.eodhdKey)
  if (env.quotesDemo) return demoProvider()
  return null
}
