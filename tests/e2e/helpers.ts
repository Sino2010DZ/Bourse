import type { Page } from '@playwright/test'

// Prix fictifs renvoyés à la place du serveur, pour des tests reproductibles.
export const PRICES: Record<string, { price: number; changePct: number }> = {
  'SIX:NESN': { price: 90, changePct: 1.25 },
  'NASDAQ:AAPL': { price: 150, changePct: -0.8 },
  'SIX:ROG': { price: 270, changePct: 0 },
}

export async function mockQuotes(page: Page, enabled = true) {
  await page.route('**/api/quotes**', async (route) => {
    const symbols = (new URL(route.request().url()).searchParams.get('symbols') ?? '').split(',')
    const quotes = Object.fromEntries(symbols.filter((s) => PRICES[s]).map((s) => [s, { symbol: s, ...PRICES[s], prevClose: null, time: Date.now() }]))
    await route.fulfill({ json: enabled ? { enabled: true, quotes } : { enabled: false, quotes: {} } })
  })
}

// Ignore les widgets TradingView pour des tests rapides et sans réseau.
export async function blockTradingView(page: Page) {
  await page.route(/tradingview/, (route) => route.abort())
}

export async function setup(page: Page, opts: { premium?: boolean; consent?: boolean; quotes?: boolean; allFree?: boolean } = {}) {
  await blockTradingView(page)
  await mockQuotes(page, opts.quotes ?? true)
  await page.addInitScript(({ premium, consent, allFree }) => {
    if (!allFree) localStorage.setItem('tg.premiumMode', '1')
    if (premium) localStorage.setItem('tg.devPremium', '1')
    if (consent) localStorage.setItem('tg.consent', JSON.stringify({ ads: false, date: new Date().toISOString(), version: 1 }))
  }, { premium: !!opts.premium, consent: opts.consent ?? true, allFree: !!opts.allFree })
}
