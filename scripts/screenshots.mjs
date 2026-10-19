// Captures d'écran du site (avec les vrais widgets TradingView).
import { chromium, devices } from '@playwright/test'

const base = process.env.BASE_URL ?? 'http://localhost:4173'
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined })
const shots = [
  { name: 'ordinateur-valeur-sombre', ctx: { viewport: { width: 1440, height: 900 } }, theme: 'dark', path: '/s/SIX%3ANESN' },
  { name: 'ordinateur-accueil-clair', ctx: { viewport: { width: 1440, height: 900 } }, theme: 'light', path: '/' },
  { name: 'iphone-accueil-sombre', ctx: devices['iPhone 13'], theme: 'dark', path: '/' },
  { name: 'iphone-valeur-clair', ctx: devices['iPhone 13'], theme: 'light', path: '/s/NASDAQ%3AAAPL' },
]
for (const s of shots) {
  const ctx = await browser.newContext({ ...s.ctx, locale: 'fr-CH' })
  const page = await ctx.newPage()
  await page.addInitScript((theme) => {
    localStorage.setItem('tg.theme', theme)
    localStorage.setItem('tg.consent', JSON.stringify({ ads: false, date: '2026-10-19', version: 1 }))
    localStorage.setItem('tg.guest.watchlist', JSON.stringify(['SIX:NESN', 'SIX:UBSG', 'NASDAQ:AAPL', 'XETR:SAP', 'BINANCE:BTCUSDT']))
  }, s.theme)
  await page.goto(base + s.path)
  await page.waitForTimeout(9000)
  await page.screenshot({ path: `docs/captures/${s.name}.png` })
  await ctx.close()
}
await browser.close()
console.log('Captures prêtes dans docs/captures/')
