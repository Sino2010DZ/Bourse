import { LANGUAGES, useI18n, type Lang } from '../i18n'
import { useTheme } from '../context/ThemeContext'
import { Icon } from './Icon'

const langs = Object.keys(LANGUAGES) as Lang[]

export function LangButton() {
  const { lang, setLang } = useI18n()
  const next = langs[(langs.indexOf(lang) + 1) % langs.length]
  return (
    <button className="chip-btn" onClick={() => setLang(next)} aria-label={LANGUAGES[next].label} title={LANGUAGES[next].label}>
      {next.toUpperCase()}
    </button>
  )
}

export function ThemeButton() {
  const { theme, setChoice } = useTheme()
  const { t } = useI18n()
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <button className="chip-btn" onClick={() => setChoice(next)} aria-label={t(`account.themes.${next}`)} title={t(`account.themes.${next}`)}>
      {theme === 'dark' ? <Icon name="sun" size={18} /> : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z" /></svg>}
    </button>
  )
}
