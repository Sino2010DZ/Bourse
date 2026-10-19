import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { demoProvider, eodhdProvider, type QuoteProvider } from '../../netlify/lib/providers'
import { clearMemoryCache, getQuotes, QUOTE_TTL_MS } from '../../netlify/lib/quoteCache'
import quotesHandler from '../../netlify/functions/quotes.mts'

describe('fournisseur EODHD', () => {
  it('traduit les symboles, regroupe les appels et lit la réponse', async () => {
    const calls: URL[] = []
    const fetchMock = vi.fn(async (url: URL) => {
      calls.push(url)
      return new Response(JSON.stringify([
        { code: 'NESN.SW', timestamp: 1_700_000_000, close: 90.5, previousClose: 90, change_p: 0.5556 },
        { code: 'AAPL.US', timestamp: 1_700_000_000, close: 'NA', previousClose: 'NA', change_p: 'NA' },
      ]))
    })
    const p = eodhdProvider('SECRET', fetchMock as unknown as typeof fetch)
    const out = await p.fetchQuotes(['SIX:NESN', 'NASDAQ:AAPL'])
    expect(calls).toHaveLength(1)
    expect(calls[0].pathname).toBe('/api/real-time/NESN.SW')
    expect(calls[0].searchParams.get('s')).toBe('AAPL.US')
    expect(out['SIX:NESN']).toMatchObject({ price: 90.5, prevClose: 90, changePct: 0.5556, time: 1_700_000_000_000 })
    expect(out['NASDAQ:AAPL']).toBeUndefined() // valeur « NA » ignorée
  })

  it('découpe en paquets de 20', async () => {
    const fetchMock = vi.fn(async () => new Response('[]'))
    const p = eodhdProvider('K', fetchMock as unknown as typeof fetch)
    const syms = Array.from({ length: 45 }, (_, i) => `SIX:S${i}`)
    await p.fetchQuotes(syms)
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('remonte une erreur HTTP', async () => {
    const p = eodhdProvider('K', (async () => new Response('', { status: 429 })) as unknown as typeof fetch)
    await expect(p.fetchQuotes(['SIX:NESN'])).rejects.toThrow('429')
  })
})

describe('cache des prix', () => {
  beforeEach(() => clearMemoryCache())

  it('n’appelle le fournisseur qu’une fois par minute', async () => {
    const inner = demoProvider(() => 0)
    const provider: QuoteProvider = { name: 'spy', fetchQuotes: vi.fn(inner.fetchQuotes) }
    await getQuotes(['SIX:NESN'], provider, null, 1_000)
    await getQuotes(['SIX:NESN'], provider, null, 1_000 + QUOTE_TTL_MS - 1)
    expect(provider.fetchQuotes).toHaveBeenCalledTimes(1)
    await getQuotes(['SIX:NESN'], provider, null, 1_000 + QUOTE_TTL_MS)
    expect(provider.fetchQuotes).toHaveBeenCalledTimes(2)
  })

  it('ne redemande que les symboles manquants', async () => {
    const fetchQuotes = vi.fn(demoProvider(() => 0).fetchQuotes)
    const provider: QuoteProvider = { name: 'spy', fetchQuotes }
    await getQuotes(['SIX:NESN'], provider, null, 0)
    await getQuotes(['SIX:NESN', 'SIX:ROG'], provider, null, 10)
    expect(fetchQuotes.mock.calls[1][0]).toEqual(['SIX:ROG'])
  })
})

describe('fonction /api/quotes', () => {
  const saved = { ...process.env }
  beforeEach(() => { delete process.env.EODHD_API_KEY; delete process.env.QUOTES_DEMO; clearMemoryCache() })
  afterEach(() => { process.env = { ...saved } })

  const call = async (qs: string) => {
    const res = await quotesHandler(new Request(`http://x/api/quotes?${qs}`))
    return { status: res.status, body: await res.json(), cache: res.headers.get('netlify-cdn-cache-control') }
  }

  it('refuse les symboles invalides', async () => {
    expect((await call('symbols=<script>')).status).toBe(400)
  })
  it('sans fournisseur : désactivé, sans erreur', async () => {
    expect((await call('symbols=SIX:NESN')).body).toEqual({ enabled: false, quotes: {} })
  })
  it('en démo : renvoie des prix et active le cache CDN', async () => {
    process.env.QUOTES_DEMO = '1'
    const r = await call('symbols=SIX:NESN,NASDAQ:AAPL')
    expect(r.body.enabled).toBe(true)
    expect(Object.keys(r.body.quotes).sort()).toEqual(['NASDAQ:AAPL', 'SIX:NESN'])
    expect(r.cache).toContain('s-maxage=60')
  })
  it('la clé secrète n’apparaît jamais dans la réponse', async () => {
    process.env.EODHD_API_KEY = 'TOP-SECRET-KEY'
    globalThis.fetch = (async () => new Response('', { status: 500 })) as typeof fetch
    const res = await quotesHandler(new Request('http://x/api/quotes?symbols=SIX:NESN'))
    expect(await res.text()).not.toContain('TOP-SECRET-KEY')
  })
})
