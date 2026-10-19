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
