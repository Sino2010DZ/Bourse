import { Link, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useI18n } from '../i18n'
import { useData } from '../context/DataContext'
import { useTheme } from '../context/ThemeContext'
import { useQuotes } from '../lib/useQuotes'
import { displayTicker, getSymbol, SUGGESTIONS } from '../lib/symbols'
import { Icon } from './Icon'
import { SymbolSearch } from './SymbolSearch'
import { TradingViewWidget } from './TradingViewWidget'
import type { Quote } from '../lib/types'

export const symbolPath = (tv: string) => `/s/${encodeURIComponent(tv)}`

export function Change({ pct }: { pct: number }) {
  const { formatNumber } = useI18n()
  const cls = pct > 0 ? 'up' : pct < 0 ? 'down' : 'flat'
  return <span className={`change ${cls}`}>{pct > 0 ? '+' : ''}{formatNumber(pct, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} %</span>
}

export function PriceCell({ symbol, quote }: { symbol: string; quote?: Quote }) {
  const { formatMoney, lang } = useI18n()
  const { theme } = useTheme()
  if (quote) {
    return (
      <span className="price-cell">
        <span className="price">{formatMoney(quote.price, getSymbol(symbol)?.currency === 'GBX' ? null : getSymbol(symbol)?.currency)}</span>
        <Change pct={quote.changePct} />
      </span>
    )
  }
  // Sans prix serveur : TradingView affiche le cours et la variation (vert/rouge).
  return (
    <TradingViewWidget widget="single-quote" className="tv-quote" height={62} attribution={false}
      config={{ symbol, width: '100%', isTransparent: true, colorTheme: theme, locale: lang }} />
  )
}

export function Watchlist({ compact = false, current }: { compact?: boolean; current?: string }) {
  const { t, intl } = useI18n()
  const { watchlist, watchLimit, addWatch, removeWatch, loading } = useData()
  const { quotes, updatedAt } = useQuotes(watchlist)
  const [message, setMessage] = useState<string | null>(null)
  const navigate = useNavigate()

  const add = async (tv: string) => {
    const r = await addWatch(tv)
    setMessage(r === 'limit' ? t('watchlist.limitReached', { limit: watchLimit }) : r === 'error' ? t('common.error') : null)
  }

  const suggestions = SUGGESTIONS.filter((s) => !watchlist.includes(s)).slice(0, 6)
  const limitLabel = Number.isFinite(watchLimit) ? t('watchlist.count', { count: watchlist.length, limit: watchLimit }) : String(watchlist.length)

  return (
    <section className={`card glass watchlist ${compact ? 'compact' : ''}`} aria-labelledby="wl-title">
      <div className="card-head">
        <h2 id="wl-title">{t('watchlist.title')}</h2>
        <span className="muted small" data-testid="wl-count">{limitLabel}</span>
      </div>

      {!compact && (
        <SymbolSearch onSelect={(s) => navigate(symbolPath(s.tv))} onAdd={(s) => void add(s.tv)} isAdded={(tv) => watchlist.includes(tv)} />
      )}

      {message && (
        <p className="notice warn" role="alert">
          {message} {message.includes(String(watchLimit)) && <Link to="/pricing">{t('common.upgrade')}</Link>}
        </p>
      )}

      {loading ? <p className="muted">{t('common.loading')}</p> : watchlist.length === 0 ? (
        <div className="empty">
          <p>{t('watchlist.empty')}</p>
          <p className="muted small">{t('watchlist.emptyHint')}</p>
        </div>
      ) : (
        <ul className="wl-list">
          {watchlist.map((tv) => {
            const info = getSymbol(tv)
            const quote = quotes[tv]
            const removeBtn = !compact && (
              <button className="icon-btn" aria-label={`${t('watchlist.remove')} ${displayTicker(tv)}`} onClick={() => void removeWatch(tv)}>
                <Icon name="trash" size={18} />
              </button>
            )
            if (!quote) {
              // Sans prix serveur : le widget TradingView affiche nom, cours et variation.
              return (
                <li key={tv} className={`wl-row widget ${current === tv ? 'current' : ''}`}>
                  <Link to={symbolPath(tv)} className="wl-overlay" aria-label={info?.name ?? tv} />
                  <PriceCell symbol={tv} />
                  {removeBtn}
                </li>
              )
            }
            return (
              <li key={tv} className={`wl-row ${current === tv ? 'current' : ''}`}>
                <Link to={symbolPath(tv)} className="wl-main" aria-label={info?.name ?? tv}>
                  <span className="sym">{displayTicker(tv)}</span>
                  <span className="name">{info?.name ?? tv}</span>
                </Link>
                <div className="wl-price" onClick={() => navigate(symbolPath(tv))}>
                  <PriceCell symbol={tv} quote={quote} />
                </div>
                {removeBtn}
              </li>
            )
          })}
        </ul>
      )}

      {!compact && suggestions.length > 0 && (
        <div className="suggest">
          <h3 className="muted small">{t('watchlist.suggestions')}</h3>
          <div className="chips">
            {suggestions.map((s) => (
              <button key={s} className="chip" onClick={() => void add(s)}>
                <Icon name="plus" size={14} /> {getSymbol(s)?.name ?? s}
              </button>
            ))}
          </div>
        </div>
      )}

      <p className="muted small delayed">
        {t('watchlist.delayed')}
        {updatedAt && ` · ${t('watchlist.updated', { time: new Date(updatedAt).toLocaleTimeString(intl, { hour: '2-digit', minute: '2-digit' }) })}`}
      </p>
    </section>
  )
}
