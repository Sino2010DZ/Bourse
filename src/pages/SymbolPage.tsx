import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useI18n, type MessageKey } from '../i18n'
import { useTheme } from '../context/ThemeContext'
import { useData } from '../context/DataContext'
import { TradingViewWidget } from '../components/TradingViewWidget'
import { Watchlist, Change } from '../components/Watchlist'
import { Icon } from '../components/Icon'
import { AdSlot } from '../components/AdSlot'
import { displayTicker, getSymbol } from '../lib/symbols'
import { useQuotes } from '../lib/useQuotes'

// Périodes du graphique : intervalle des bougies + plage affichée.
export const PERIODS = {
  d1: { interval: '5', range: '1D' },
  w1: { interval: '30', range: '5D' },
  m1: { interval: '60', range: '1M' },
  y1: { interval: 'D', range: '12M' },
  y5: { interval: 'W', range: '60M' },
} as const
type Period = keyof typeof PERIODS

export function SymbolPage() {
  const { symbol = '' } = useParams()
  const tv = decodeURIComponent(symbol).toUpperCase()
  const info = getSymbol(tv)
  const { t, lang, formatMoney } = useI18n()
  const { theme } = useTheme()
  const { watchlist, addWatch, removeWatch, watchLimit } = useData()
  const [period, setPeriod] = useState<Period>('y1')
  const [msg, setMsg] = useState<string | null>(null)
  const { quotes } = useQuotes(info ? [tv] : [])
  const q = quotes[tv]

  if (!info) return <div className="page"><p>{t('notFound')}</p></div>

  const inList = watchlist.includes(tv)
  const toggle = async () => {
    if (inList) return removeWatch(tv)
    const r = await addWatch(tv)
    setMsg(r === 'limit' ? t('watchlist.limitReached', { limit: watchLimit }) : null)
  }

  return (
    <div className="page symbol-page">
      <div className="symbol-layout">
        <div className="symbol-side"><Watchlist compact current={tv} /></div>
        <div className="symbol-main">
          <div className="symbol-head">
            <Link to="/" className="icon-btn back" aria-label={t('common.back')}><Icon name="back" /></Link>
            <div>
              <h1>{info.name} <span className="muted ticker">{displayTicker(tv)}</span></h1>
              <p className="muted small">{tv.split(':')[0]} · {t(`search.types.${info.type}`)} · {info.currency}</p>
            </div>
            {q && (
              <div className="head-quote">
                <span className="price big">{formatMoney(q.price, info.currency === 'GBX' ? null : info.currency)}</span>
                <Change pct={q.changePct} />
              </div>
            )}
          </div>

          <div className="actions symbol-actions">
            <button className={`btn ${inList ? '' : 'btn-primary'}`} onClick={() => void toggle()}>
              <Icon name={inList ? 'check' : 'plus'} size={18} /> {inList ? t('watchlist.added') : t('watchlist.add')}
            </button>
            <Link className="btn" to={`/alerts?symbol=${encodeURIComponent(tv)}`}><Icon name="bell" size={18} /> {t('symbol.setAlert')}</Link>
            <Link className="btn" to={`/portfolio?symbol=${encodeURIComponent(tv)}`}><Icon name="portfolio" size={18} /> {t('symbol.addPosition')}</Link>
          </div>
          {msg && <p className="notice warn" role="alert">{msg} <Link to="/pricing">{t('common.upgrade')}</Link></p>}

          <section className="card glass chart-card">
            <div className="segmented" role="tablist" aria-label={t('symbol.periodsLabel')}>
              {(Object.keys(PERIODS) as Period[]).map((p) => (
                <button key={p} role="tab" aria-selected={period === p} className={period === p ? 'on' : ''} onClick={() => setPeriod(p)}>
                  {t(`symbol.periods.${p}` as MessageKey)}
                </button>
              ))}
            </div>
            <TradingViewWidget widget="advanced-chart" className="chart"
              config={{
                autosize: true,
                symbol: tv,
                interval: PERIODS[period].interval,
                range: PERIODS[period].range,
                timezone: 'Europe/Zurich',
                theme,
                style: '1',
                locale: lang,
                backgroundColor: 'rgba(0,0,0,0)',
                gridColor: theme === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
                hide_side_toolbar: true,
                hide_top_toolbar: false,
                allow_symbol_change: false,
                save_image: false,
                calendar: false,
                withdateranges: false,
                studies: ['MASimple@tv-basicstudies'],
                support_host: 'https://www.tradingview.com',
              }} />
            <p className="muted small">{t('symbol.indicators')} · {t('watchlist.delayed')}</p>
          </section>

          <div className="grid-2">
            <section className="card glass">
              <h2>{t('symbol.overview')}</h2>
              <TradingViewWidget widget="symbol-info" height={190}
                config={{ symbol: tv, width: '100%', locale: lang, colorTheme: theme, isTransparent: true }} />
            </section>
            <section className="card glass">
              <h2>{t('symbol.news')}</h2>
              <TradingViewWidget widget="timeline" height={420}
                config={{ feedMode: 'symbol', symbol: tv, isTransparent: true, displayMode: 'regular', width: '100%', height: '100%', colorTheme: theme, locale: lang }} />
            </section>
          </div>
          <AdSlot slot={import.meta.env.VITE_ADSENSE_SLOT_SYMBOL} />
        </div>
      </div>
    </div>
  )
}
