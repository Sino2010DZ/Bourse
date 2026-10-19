import { readJson, writeJson } from './storage'

export interface Consent { ads: boolean; date: string; version: number }

const KEY = 'tg.consent'
export const CONSENT_VERSION = 1
export const CONSENT_EVENT = 'tg-consent-change'
export const OPEN_CONSENT_EVENT = 'tg-consent-open'

export function getConsent(): Consent | null {
  const c = readJson<Consent | null>(KEY, null)
  return c && c.version === CONSENT_VERSION ? c : null
}

export function setConsent(ads: boolean) {
  writeJson(KEY, { ads, date: new Date().toISOString(), version: CONSENT_VERSION } satisfies Consent)
  window.dispatchEvent(new Event(CONSENT_EVENT))
}

export function openConsentSettings() {
  window.dispatchEvent(new Event(OPEN_CONSENT_EVENT))
}
