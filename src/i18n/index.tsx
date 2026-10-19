import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { fr, type Messages } from './messages/fr'
import { en } from './messages/en'

// Pour ajouter une langue : créez messages/xx.ts (copie de en.ts traduite),
// puis ajoutez une ligne ici. C'est tout.
export const LANGUAGES = {
  fr: { label: 'Français', messages: fr, intl: 'fr-CH' },
  en: { label: 'English', messages: en, intl: 'en-GB' },
} satisfies Record<string, { label: string; messages: Messages; intl: string }>

export type Lang = keyof typeof LANGUAGES

type Paths<T, P extends string = ''> = {
  [K in keyof T & string]: T[K] extends string ? `${P}${K}` : Paths<T[K], `${P}${K}.`>
}[keyof T & string]
export type MessageKey = Paths<Messages>

const STORAGE_KEY = 'tg.lang'

export function translate(messages: Messages, key: MessageKey, vars?: Record<string, string | number>): string {
  let value: unknown = messages
  for (const part of key.split('.')) value = (value as Record<string, unknown>)?.[part]
  if (typeof value !== 'string') return key
  return vars ? value.replace(/\{(\w+)\}/g, (_, name: string) => String(vars[name] ?? `{${name}}`)) : value
}

export function detectLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && saved in LANGUAGES) return saved as Lang
  } catch { /* stockage indisponible */ }
  const browser = (navigator.language || 'fr').slice(0, 2)
  return browser in LANGUAGES ? (browser as Lang) : 'en'
}

interface I18nValue {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: MessageKey, vars?: Record<string, string | number>) => string
  intl: string
  formatNumber: (n: number, opts?: Intl.NumberFormatOptions) => string
  formatMoney: (n: number, currency?: string | null) => string
}

const I18nContext = createContext<I18nValue | null>(null)

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detectLang)

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
    try { localStorage.setItem(STORAGE_KEY, next) } catch { /* ignore */ }
  }, [])

  const value = useMemo<I18nValue>(() => {
    const { messages, intl } = LANGUAGES[lang]
    const formatNumber = (n: number, opts?: Intl.NumberFormatOptions) => new Intl.NumberFormat(intl, opts).format(n)
    return {
      lang,
      setLang,
      intl,
      t: (key, vars) => translate(messages, key, vars),
      formatNumber,
      formatMoney: (n, currency) =>
        currency
          ? formatNumber(n, { style: 'currency', currency, maximumFractionDigits: Math.abs(n) < 1 ? 6 : 2 })
          : formatNumber(n, { maximumFractionDigits: Math.abs(n) < 1 ? 6 : 2 }),
    }
  }, [lang, setLang])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n doit être utilisé dans <I18nProvider>')
  return ctx
}
