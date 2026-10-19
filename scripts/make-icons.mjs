// Génère les icônes PNG de l'app à partir de public/logo.svg (via Chromium).
import { chromium } from '@playwright/test'
import { readFileSync } from 'node:fs'

const svg = readFileSync('public/logo.svg', 'utf8')
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined })
const page = await browser.newPage()
const jobs = [
  // [fichier, taille, marge, fond plein] — iOS et « maskable » veulent un fond plein.
  ['icon-192.png', 192, 0, false], ['icon-512.png', 512, 0, false], ['apple-touch-icon.png', 180, 0, true],
  ['icon-maskable-512.png', 512, 0.12, true], ['badge-72.png', 72, 0, false],
]
for (const [name, size, pad, solid] of jobs) {
  const inner = Math.round(size * (1 - pad * 2))
  await page.setViewportSize({ width: size, height: size })
  await page.setContent(`<body style="margin:0;background:${solid ? '#4a52ff' : 'transparent'};display:grid;place-items:center;width:${size}px;height:${size}px">
    <div style="width:${inner}px;height:${inner}px">${svg.replace('<svg ', `<svg width="${inner}" height="${inner}" `)}</div></body>`)
  await page.screenshot({ path: `public/icons/${name}`, omitBackground: !solid })
}
await browser.close()
console.log('Icônes générées')

// Image d'aperçu pour le partage du lien (WhatsApp, LinkedIn, X…).
{
  const { APP_NAME } = await import('../src/brand.ts').catch(() => ({ APP_NAME: 'Tradevantage' }))
  const b = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined })
  const p = await b.newPage({ viewport: { width: 1200, height: 630 } })
  await p.setContent(`<body style="margin:0;width:1200px;height:630px;display:flex;align-items:center;gap:56px;padding:0 96px;box-sizing:border-box;
    font-family:-apple-system,Segoe UI,Inter,Arial,sans-serif;color:#fff;background:radial-gradient(circle at 15% 20%,#3b6cff 0,transparent 55%),radial-gradient(circle at 85% 70%,#7a3cff 0,transparent 55%),radial-gradient(circle at 50% 110%,#14c8a8 0,transparent 50%),#0b1020">
    <div style="width:220px;height:220px;flex:none">${svg.replace('<svg ', '<svg width="220" height="220" ')}</div>
    <div><div style="font-size:96px;font-weight:800;letter-spacing:-3px">${APP_NAME}</div>
    <div style="font-size:36px;opacity:.85;margin-top:8px">Actions · ETF · Cryptos</div>
    <div style="font-size:28px;opacity:.65;margin-top:6px">USA · Suisse · Europe</div></div></body>`)
  await p.screenshot({ path: 'public/og-image.png' })
  await b.close()
}
