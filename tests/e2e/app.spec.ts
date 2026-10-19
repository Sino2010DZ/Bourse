import { expect, test } from '@playwright/test'
import { setup } from './helpers'

const DISCLAIMER = 'Informations non contractuelles, ceci n’est pas un conseil en investissement.'

test('accueil : message obligatoire visible, en français', async ({ page }) => {
  await setup(page)
  await page.goto('/')
  await expect(page.getByRole('note')).toContainText(DISCLAIMER)
  await expect(page.getByRole('note')).toBeInViewport()
  await expect(page.getByRole('heading', { name: 'Marchés' })).toBeVisible()
})

test('bouton de langue : passe en anglais et s’en souvient', async ({ page }) => {
  await setup(page)
  await page.goto('/')
  await page.getByRole('button', { name: 'English' }).first().click()
  await expect(page.getByRole('heading', { name: 'Markets' })).toBeVisible()
  await expect(page.getByRole('note')).toContainText('does not constitute investment advice')
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Markets' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('lang', 'en')
})

test('mode clair / sombre', async ({ page }) => {
  await setup(page)
  await page.emulateMedia({ colorScheme: 'light' })
  await page.goto('/')
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.getByRole('button', { name: 'Sombre' }).first().click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
})

test('bandeau cookies : refuser masque le bandeau durablement', async ({ page }) => {
  await setup(page, { consent: false })
  await page.goto('/')
  const banner = page.getByRole('dialog', { name: 'Cookies' })
  await expect(banner).toBeVisible()
  await banner.getByRole('button', { name: 'Tout refuser' }).click()
  await expect(banner).toBeHidden()
  await page.reload()
  await expect(banner).toBeHidden()
  // Peut être rouvert depuis le pied de page.
  await page.getByRole('button', { name: 'Paramètres des cookies' }).click()
  await expect(banner.getByText('Publicité')).toBeVisible()
})

test('recherche par nom et par symbole', async ({ page }) => {
  await setup(page)
  await page.goto('/')
  const search = page.locator('.watchlist').getByRole('combobox')
  await search.fill('nestle')
  await expect(page.getByRole('option').first()).toContainText('Nestlé')
  await search.fill('SAP')
  await expect(page.getByRole('option').first()).toContainText('SAP')
  await page.getByRole('option').first().click()
  await expect(page).toHaveURL(/\/s\/XETR%3ASAP/)
  await expect(page.getByRole('heading', { level: 1 })).toContainText('SAP')
})

test('watchlist gratuite : prix, couleurs et limite de 5', async ({ page }) => {
  await setup(page)
  await page.goto('/')
  const wl = page.locator('.watchlist').first()
  await wl.getByRole('combobox').fill('nestle')
  await page.getByRole('button', { name: 'Ajouter à la watchlist NESN' }).click()
  await expect(wl.locator('.wl-row')).toHaveCount(1)
  await expect(wl.locator('.wl-row').first()).toContainText('90')
  await expect(wl.locator('.change.up')).toContainText('+1,25')

  for (const q of ['apple', 'roche', 'novartis', 'nvidia']) {
    await wl.getByRole('combobox').fill(q)
    await page.getByRole('option').first().getByRole('button').click()
  }
  await expect(wl.locator('.wl-row')).toHaveCount(5)
  await expect(page.getByTestId('wl-count')).toHaveText('5 / 5')
  await expect(wl.locator('.change.down')).toBeVisible()

  await wl.getByRole('combobox').fill('tesla')
  await page.getByRole('option').first().getByRole('button').click()
  await expect(page.getByRole('alert')).toContainText('Limite du plan gratuit')
  await expect(wl.locator('.wl-row')).toHaveCount(5)

  // La watchlist reste après rechargement, et on peut retirer une ligne.
  await page.reload()
  await expect(wl.locator('.wl-row')).toHaveCount(5)
  await wl.getByRole('button', { name: /Retirer de la watchlist AAPL/ }).click()
  await expect(wl.locator('.wl-row')).toHaveCount(4)
})

test('page valeur : graphique et 5 périodes', async ({ page }) => {
  await setup(page)
  await page.goto('/s/SIX%3ANESN')
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Nestlé')
  const tabs = page.getByRole('tab')
  await expect(tabs).toHaveText(['1J', '1S', '1M', '1A', '5A'])
  await expect(page.getByRole('tab', { name: '1A' })).toHaveAttribute('aria-selected', 'true')
  await page.getByRole('tab', { name: '5A' }).click()
  await expect(page.getByRole('tab', { name: '5A' })).toHaveAttribute('aria-selected', 'true')
  const cfg = await page.locator('.chart script').textContent()
  expect(JSON.parse(cfg!)).toMatchObject({ symbol: 'SIX:NESN', interval: 'W', range: '60M', style: '1', studies: ['MASimple@tv-basicstudies'] })
  await expect(page.getByRole('heading', { name: 'Actualités' })).toBeVisible()
  await expect(page.locator('.head-quote')).toContainText('+1,25')
})

test('portefeuille et alertes : réservés au Premium', async ({ page }) => {
  await setup(page)
  await page.goto('/portfolio')
  await expect(page.getByText('Fonction réservée au plan Premium.')).toBeVisible()
  await page.goto('/alerts')
  await expect(page.getByText('Fonction réservée au plan Premium.')).toBeVisible()
})

test('Premium : portefeuille avec valeur totale et gains', async ({ page }) => {
  await setup(page, { premium: true })
  await page.goto('/portfolio?symbol=SIX:NESN')
  await page.getByLabel('Quantité').fill('10')
  await page.getByLabel('Prix d’achat').fill('80')
  await page.getByRole('button', { name: 'Ajouter une position' }).click()
  await expect(page.getByTestId('total-CHF')).toContainText('900')
  await expect(page.getByTestId('pnl-CHF')).toContainText('100')
  await expect(page.getByTestId('pnl-CHF')).toContainText('12,5')

  await page.locator('form').getByRole('combobox', { name: 'Recherche' }).fill('apple')
  await page.getByRole('option').first().click()
  await page.getByLabel('Quantité').fill('2')
  await page.getByLabel('Prix d’achat').fill('200')
  await page.getByRole('button', { name: 'Ajouter une position' }).click()
  await expect(page.getByTestId('pnl-USD')).toHaveClass(/down/)
  await expect(page.getByTestId('total-USD')).toContainText('300')
})

test('Premium : création d’une alerte', async ({ page }) => {
  await setup(page, { premium: true })
  await page.goto('/alerts?symbol=SIX:NESN')
  await expect(page.getByText('Cours actuel')).toContainText('90')
  await page.getByLabel('Prix cible').fill('95')
  await page.getByRole('button', { name: 'Créer l’alerte' }).click()
  await expect(page.locator('.alert-row')).toHaveCount(1)
  await expect(page.locator('.alert-row')).toContainText('Monte au-dessus de')
  await expect(page.locator('.alert-row .badge')).toHaveText('Active')
})

test('sans source de prix serveur : affichage via TradingView', async ({ page }) => {
  await setup(page, { premium: true, quotes: false })
  await page.addInitScript(() => localStorage.setItem('tg.guest.watchlist', JSON.stringify(['SIX:NESN'])))
  await page.goto('/')
  await expect(page.locator('.wl-row .tv-quote script')).toHaveCount(1)
  await page.goto('/portfolio')
  await expect(page.getByRole('heading', { name: 'Mon portefeuille' })).toBeVisible()
})

test('pages légales et tarifs', async ({ page }) => {
  await setup(page)
  await page.goto('/legal/terms')
  await expect(page.getByRole('heading', { name: 'Conditions d’utilisation' })).toBeVisible()
  await expect(page.locator('.legal')).toContainText('Pas de conseil en investissement')
  await page.goto('/legal/privacy')
  await expect(page.locator('.legal')).toContainText('nLPD')
  await page.goto('/pricing')
  await expect(page.locator('.plan.featured')).toContainText('89')
  await page.getByRole('button', { name: 'Mensuel' }).click()
  await expect(page.locator('.plan.featured')).toContainText('9.90')
})

test('comptes : message clair si Supabase n’est pas encore branché', async ({ page }) => {
  await setup(page)
  await page.goto('/signup')
  await expect(page.getByText('Les comptes ne sont pas encore configurés')).toBeVisible()
})

test('PWA : manifeste et service worker', async ({ page, request }) => {
  await setup(page)
  const manifest = await (await request.get('/manifest.webmanifest')).json()
  expect(manifest).toMatchObject({ display: 'standalone', start_url: '/' })
  expect(manifest.icons.some((i: { purpose?: string }) => i.purpose === 'maskable')).toBe(true)
  await page.goto('/')
  const active = await page.evaluate(async () => !!(await navigator.serviceWorker.ready).active)
  expect(active).toBe(true)
  expect((await request.get('/icons/apple-touch-icon.png')).ok()).toBe(true)
})

test('aucun défilement horizontal parasite', async ({ page }) => {
  await setup(page, { premium: true })
  for (const path of ['/', '/s/SIX%3ANESN', '/portfolio', '/alerts', '/pricing', '/account']) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow, path).toBeLessThanOrEqual(0)
  }
})

test('tarifs : paiement en sommeil tant que Stripe n’est pas branché', async ({ page }) => {
  await setup(page)
  await page.route('**/api/billing', (r) => r.fulfill({ json: { enabled: false } }))
  await page.goto('/pricing')
  await expect(page.getByRole('button', { name: 'Paiement en ligne bientôt disponible' })).toBeDisabled()
})

test('tarifs : avec Stripe branché, un visiteur est invité à créer un compte', async ({ page }) => {
  await setup(page)
  await page.route('**/api/billing', (r) => r.fulfill({ json: { enabled: true } }))
  await page.goto('/pricing')
  await expect(page.getByRole('link', { name: 'Créer un compte pour s’abonner' })).toBeVisible()
  await expect(page.getByText('Paiement sécurisé par Stripe')).toBeVisible()
})

test('hors ligne : un message prévient l’utilisateur', async ({ page, context }) => {
  await setup(page)
  await page.goto('/')
  await context.setOffline(true)
  await expect(page.getByRole('status')).toContainText('Hors ligne')
  await context.setOffline(false)
  await expect(page.getByRole('status')).toBeHidden()
})

test('le nom du site vient d’un seul endroit', async ({ page, request }) => {
  await setup(page)
  await page.goto('/')
  await expect(page).toHaveTitle('Tradevantage')
  expect((await (await request.get('/manifest.webmanifest')).json()).name).toBe('Tradevantage')
  await expect(page.locator('meta[property="og:image"]')).toHaveAttribute('content', '/og-image.png')
})
