import type { Config } from '@netlify/functions'
import { getProvider } from '../lib/providers'
import { getQuotes } from '../lib/quoteCache'
import { supabaseAdmin } from '../lib/supabaseAdmin'
import { isValidTvSymbol } from '../../src/lib/symbols'

const MAX_SYMBOLS = 60

const json = (body: unknown, status = 200, cache = true) =>
  new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      // Le CDN de Netlify garde la réponse 60 s : moins d'appels, moins de coûts.
      'Cache-Control': cache ? 'public, max-age=30' : 'no-store',
      'Netlify-CDN-Cache-Control': cache ? 'public, s-maxage=60, stale-while-revalidate=30' : 'no-store',
    },
  })

export default async (req: Request) => {
  const raw = new URL(req.url).searchParams.get('symbols') ?? ''
  const symbols = [...new Set(raw.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean))]
  if (symbols.length > MAX_SYMBOLS || symbols.some((s) => !isValidTvSymbol(s))) {
    return json({ error: 'invalid symbols' }, 400, false)
  }

  const provider = getProvider()
  if (!provider || symbols.length === 0) return json({ enabled: !!provider, quotes: {} })

  try {
    const quotes = await getQuotes(symbols, provider, supabaseAdmin())
    return json({ enabled: true, provider: provider.name, quotes })
  } catch (err) {
    console.error('quotes', err)
    return json({ enabled: true, quotes: {}, error: 'provider unavailable' }, 502, false)
  }
}

export const config: Config = { path: '/api/quotes' }
