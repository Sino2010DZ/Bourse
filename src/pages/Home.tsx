import { useI18n } from '../i18n'
import { useTheme } from '../context/ThemeContext'
import { Watchlist } from '../components/Watchlist'
import { TradingViewWidget } from '../components/TradingViewWidget'
import { AdSlot } from '../components/AdSlot'
import { TICKER_TAPE, getSymbol } from '../lib/symbols'

export function Home() {
  const { t, lang } = useI18n()
  const { theme } = useTheme()
  return (
    <div className="page">
      <div className="hero">
        <h1>{t('nav.markets')}</h1>
        <p className="muted">{t('app.tagline')}</p>
      </div>
      <TradingViewWidget widget="ticker-tape" className="tape glass" attribution={false}
        config={{
          symbols: TICKER_TAPE.map((s) => ({ proName: s, title: getSymbol(s)?.name ?? s })),
          showSymbolLogo: true, isTransparent: true, displayMode: 'adaptive', colorTheme: theme, locale: lang,
        }} />
      <Watchlist />
      <AdSlot slot={import.meta.env.VITE_ADSENSE_SLOT_HOME} />
    </div>
  )
}
