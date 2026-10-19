import { useEffect, useState } from 'react'
import { REFRESH_MS } from '../config'
import type { Quote } from './types'

export interface QuotesState {
  enabled: boolean
  quotes: Record<string, Quote>
  updatedAt: number | null
}

// Prix calculés côté serveur (fonction Netlify /api/quotes, avec cache).
// Si aucune source de prix n'est branchée, enabled = false et l'affichage
// se fait par les widgets TradingView.
export function useQuotes(symbols: string[]): QuotesState {
  const key = [...new Set(symbols)].sort().join(',')
  const [state, setState] = useState<QuotesState>({ enabled: false, quotes: {}, updatedAt: null })

  useEffect(() => {
    if (!key) return
    let cancelled = false
    const load = async () => {
      try {
        const res = await fetch(`/api/quotes?symbols=${encodeURIComponent(key)}`)
        if (!res.ok) throw new Error(String(res.status))
        const data = (await res.json()) as { enabled: boolean; quotes: Record<string, Quote> }
        if (!cancelled) setState({ enabled: !!data.enabled, quotes: data.quotes ?? {}, updatedAt: Date.now() })
      } catch {
        if (!cancelled) setState((s) => ({ ...s, enabled: s.enabled && Object.keys(s.quotes).length > 0 }))
      }
    }
    void load()
    const timer = window.setInterval(load, REFRESH_MS)
    const onVisible = () => document.visibilityState === 'visible' && void load()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [key])

  return state
}
