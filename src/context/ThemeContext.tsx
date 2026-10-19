import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type ThemeChoice = 'system' | 'light' | 'dark'
type Resolved = 'light' | 'dark'

const KEY = 'tg.theme'
const ThemeContext = createContext<{ choice: ThemeChoice; theme: Resolved; setChoice: (c: ThemeChoice) => void } | null>(null)

function systemTheme(): Resolved {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [choice, setChoiceState] = useState<ThemeChoice>(() => {
    try { return (localStorage.getItem(KEY) as ThemeChoice) || 'system' } catch { return 'system' }
  })
  const [system, setSystem] = useState<Resolved>(systemTheme)

  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)')
    const onChange = () => setSystem(systemTheme())
    mq?.addEventListener('change', onChange)
    return () => mq?.removeEventListener('change', onChange)
  }, [])

  const theme: Resolved = choice === 'system' ? system : choice

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#0b1020' : '#eef2fb')
  }, [theme])

  const value = useMemo(() => ({
    choice,
    theme,
    setChoice: (c: ThemeChoice) => {
      setChoiceState(c)
      try { localStorage.setItem(KEY, c) } catch { /* ignore */ }
    },
  }), [choice, theme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme doit être utilisé dans <ThemeProvider>')
  return ctx
}
