import { defineConfig, devices } from '@playwright/test'

const executablePath = process.env.CHROMIUM_PATH || undefined

export default defineConfig({
  testDir: 'tests/e2e',
  timeout: 30_000,
  fullyParallel: true,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:4173',
    locale: 'fr-CH',
    launchOptions: { executablePath },
  },
  projects: [
    { name: 'ordinateur', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 }, launchOptions: { executablePath } } },
    {
      name: 'iphone',
      use: { ...devices['iPhone 13'], browserName: 'chromium', launchOptions: { executablePath } },
    },
  ],
  webServer: {
    // Version de test : identique au site, avec le mode Premium « invité » activable.
    command: 'VITE_E2E=1 npx vite build --outDir dist-e2e && npx vite preview --outDir dist-e2e --port 4173 --strictPort',
    url: 'http://localhost:4173',
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
