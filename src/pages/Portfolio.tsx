import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { useData } from '../context/DataContext'
import { useAuth } from '../context/AuthContext'
import { PLAN_LIMITS } from '../config'
import { PremiumGate } from '../components/PremiumGate'
import { SymbolSearch } from '../components/SymbolSearch'
import { PriceCell, Change, symbolPath } from '../components/Watchlist'
import { Icon } from '../components/Icon'
import { useQuotes } from '../lib/useQuotes'
import { computePortfolio } from '../lib/portfolio'
import { displayTicker, getSymbol } from '../lib/symbols'

const CURRENCIES = ['CHF', 'EUR', 'USD', 'GBP', 'GBX']

export function Portfolio() {
  const { t, formatMoney, formatNumber } = useI18n()
  const { plan } = useAuth()
  const { positions, addPosition, removePosition } = useData()
  const [params] = useSearchParams()
  const initial = params.get('symbol')
  const [symbol, setSymbol] = useState<string | null>(initial && getSymbol(initial) ? initial : null)
  const [quantity, setQuantity] = useState('')
  const [buyPrice, setBuyPrice] = useState('')
  const [currency, setCurrency] = useState(getSymbol(initial ?? '')?.currency ?? 'CHF')
  const [date, setDate] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { enabled, quotes } = useQuotes(positions.map((p) => p.symbol))

  if (!PLAN_LIMITS[plan].portfolio) {
    return <div className="page"><h1>{t('portfolio.title')}</h1><PremiumGate /></div>
  }

  const { rows, totals } = computePortfolio(positions, quotes)
  const money = (n: number | null, cur: string) => (n === null ? '—' : formatMoney(n, cur === 'GBX' ? null : cur))

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const q = Number(quantity.replace(',', '.'))
    const p = Number(buyPrice.replace(',', '.'))
    if (!symbol) return setError(t('portfolio.chooseSymbol'))
    if (!(q > 0) || !(p >= 0) || !buyPrice) return setError(t('portfolio.invalid'))
    const r = await addPosition({ symbol, quantity: q, buy_price: p, currency, bought_at: date || null })
    if (r !== 'ok') return setError(t('common.error'))
    setError(null); setQuantity(''); setBuyPrice(''); setDate(''); setSymbol(null)
  }

  return (
    <div className="page">
      <h1>{t('portfolio.title')}</h1>

      {!enabled && positions.length > 0 && <p className="notice">{t('portfolio.noQuotes')}</p>}

      {totals.length > 0 && (
        <section className="totals" aria-label={t('portfolio.totalsByCurrency')}>
          {totals.map((tot) => (
            <div key={tot.currency} className="card glass total-card">
              <span className="muted small">{t('portfolio.total')} {tot.currency}</span>
              <span className="price big" data-testid={`total-${tot.currency}`}>{money(tot.value ?? tot.cost, tot.currency)}</span>
              <span className="muted small">{t('portfolio.cost')} : {money(tot.cost, tot.currency)}</span>
              {tot.pnl !== null && (
                <span className={`change ${tot.pnl >= 0 ? 'up' : 'down'}`} data-testid={`pnl-${tot.currency}`}>
                  {tot.pnl >= 0 ? '+' : ''}{money(tot.pnl, tot.currency)} ({formatNumber(tot.pnlPct ?? 0, { maximumFractionDigits: 2 })} %)
                </span>
              )}
            </div>
          ))}
        </section>
      )}

      <section className="card glass">
        {rows.length === 0 ? <p className="muted">{t('portfolio.empty')}</p> : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>{t('portfolio.symbol')}</th><th>{t('portfolio.quantity')}</th><th>{t('portfolio.buyPrice')}</th>
                  <th>{t('portfolio.price')}</th><th>{t('portfolio.value')}</th><th>{t('portfolio.pnl')}</th><th />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.position.id}>
                    <td><Link to={symbolPath(r.position.symbol)} className="sym">{displayTicker(r.position.symbol)}</Link>
                      <div className="muted small">{getSymbol(r.position.symbol)?.name}</div></td>
                    <td>{formatNumber(r.position.quantity)}</td>
                    <td>{money(r.position.buy_price, r.position.currency)}</td>
                    <td className="price-td">{r.price === null ? <PriceCell symbol={r.position.symbol} /> : money(r.price, r.position.currency)}</td>
                    <td>{money(r.value, r.position.currency)}</td>
                    <td>{r.pnl === null ? '—' : <><span className={r.pnl >= 0 ? 'up' : 'down'}>{money(r.pnl, r.position.currency)}</span> <Change pct={r.pnlPct ?? 0} /></>}</td>
                    <td><button className="icon-btn" aria-label={t('common.delete')}
                      onClick={() => confirm(t('portfolio.deleteConfirm')) && void removePosition(r.position.id)}><Icon name="trash" size={18} /></button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card glass">
        <h2>{t('portfolio.add')}</h2>
        <form className="form" onSubmit={submit}>
          {symbol ? (
            <div className="picked">
              <span className="sym">{displayTicker(symbol)}</span> <span>{getSymbol(symbol)?.name}</span>
              <button type="button" className="icon-btn" aria-label={t('common.remove')} onClick={() => setSymbol(null)}><Icon name="close" size={16} /></button>
            </div>
          ) : (
            <SymbolSearch onSelect={(s) => { setSymbol(s.tv); setCurrency(s.currency) }} />
          )}
          <div className="form-row">
            <label>{t('portfolio.quantity')}<input inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} required /></label>
            <label>{t('portfolio.buyPrice')}<input inputMode="decimal" value={buyPrice} onChange={(e) => setBuyPrice(e.target.value)} required /></label>
          </div>
          <div className="form-row">
            <label>{t('portfolio.currency')}
              <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
                {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <label>{t('portfolio.date')}<input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></label>
          </div>
          {error && <p className="notice warn" role="alert">{error}</p>}
          <button className="btn btn-primary" type="submit"><Icon name="plus" size={18} /> {t('portfolio.add')}</button>
        </form>
      </section>
    </div>
  )
}
