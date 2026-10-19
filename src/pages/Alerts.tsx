import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { useData } from '../context/DataContext'
import { useAuth } from '../context/AuthContext'
import { PLAN_LIMITS } from '../config'
import { PremiumGate } from '../components/PremiumGate'
import { SymbolSearch } from '../components/SymbolSearch'
import { Icon } from '../components/Icon'
import { symbolPath } from '../components/Watchlist'
import { useQuotes } from '../lib/useQuotes'
import { displayTicker, getSymbol } from '../lib/symbols'
import { enablePush, getPushStatus, type PushStatus } from '../lib/push'
import type { AlertDirection } from '../lib/types'

export function NotificationsControl() {
  const { t } = useI18n()
  const { user } = useAuth()
  const [status, setStatus] = useState<PushStatus | null>(null)
  useEffect(() => { void getPushStatus().then(setStatus) }, [])
  if (!status || status === 'unconfigured') return null
  if (!user) return <p className="notice">{t('common.loginFirst')} <Link to="/login">{t('auth.login')}</Link></p>
  if (status === 'on') return <p className="notice ok"><Icon name="check" size={16} /> {t('alerts.notificationsOn')}</p>
  if (status === 'denied') return <p className="notice warn">{t('alerts.notificationsDenied')}</p>
  if (status === 'ios-install') return <p className="notice">{t('alerts.iosHint')}</p>
  if (status === 'unsupported') return <p className="notice">{t('alerts.notificationsUnsupported')}</p>
  return (
    <button className="btn btn-primary" onClick={() => void enablePush().then(setStatus)}>
      <Icon name="bell" size={18} /> {t('alerts.enableNotifications')}
    </button>
  )
}

export function Alerts() {
  const { t, formatMoney, intl } = useI18n()
  const { plan } = useAuth()
  const { alerts, addAlert, removeAlert } = useData()
  const [params] = useSearchParams()
  const initial = params.get('symbol')
  const [symbol, setSymbol] = useState<string | null>(initial && getSymbol(initial) ? initial : null)
  const [direction, setDirection] = useState<AlertDirection>('above')
  const [target, setTarget] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { enabled, quotes } = useQuotes([...alerts.map((a) => a.symbol), ...(symbol ? [symbol] : [])])

  if (!PLAN_LIMITS[plan].alerts) return <div className="page"><h1>{t('alerts.title')}</h1><PremiumGate /></div>

  const money = (n: number, sym: string) => {
    const c = getSymbol(sym)?.currency
    return formatMoney(n, c === 'GBX' ? null : c)
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const value = Number(target.replace(',', '.'))
    if (!symbol) return setError(t('portfolio.chooseSymbol'))
    if (!(value > 0)) return setError(t('alerts.invalid'))
    const r = await addAlert({ symbol, direction, target: value })
    if (r !== 'ok') return setError(t('common.error'))
    setError(null); setTarget('')
  }

  return (
    <div className="page">
      <h1>{t('alerts.title')}</h1>
      <NotificationsControl />
      {!enabled && <p className="notice">{t('alerts.serverInactive')}</p>}

      <section className="card glass">
        <h2>{t('alerts.create')}</h2>
        <form className="form" onSubmit={submit}>
          {symbol ? (
            <div className="picked">
              <span className="sym">{displayTicker(symbol)}</span> <span>{getSymbol(symbol)?.name}</span>
              {quotes[symbol] && <span className="muted small">{t('alerts.current', { price: money(quotes[symbol].price, symbol) })}</span>}
              <button type="button" className="icon-btn" aria-label={t('common.remove')} onClick={() => setSymbol(null)}><Icon name="close" size={16} /></button>
            </div>
          ) : <SymbolSearch onSelect={(s) => setSymbol(s.tv)} />}
          <div className="form-row">
            <label>{t('alerts.when')}
              <select value={direction} onChange={(e) => setDirection(e.target.value as AlertDirection)}>
                <option value="above">{t('alerts.above')}</option>
                <option value="below">{t('alerts.below')}</option>
              </select>
            </label>
            <label>{t('alerts.target')}<input inputMode="decimal" value={target} onChange={(e) => setTarget(e.target.value)} required /></label>
          </div>
          {error && <p className="notice warn" role="alert">{error}</p>}
          <button className="btn btn-primary" type="submit"><Icon name="bell" size={18} /> {t('alerts.create')}</button>
        </form>
      </section>

      <section className="card glass">
        {alerts.length === 0 ? <p className="muted">{t('alerts.empty')}</p> : (
          <ul className="alert-list">
            {alerts.map((a) => (
              <li key={a.id} className="alert-row">
                <Link to={symbolPath(a.symbol)} className="sym">{displayTicker(a.symbol)}</Link>
                <span>{t(a.direction === 'above' ? 'alerts.above' : 'alerts.below')} <strong>{money(a.target, a.symbol)}</strong></span>
                <span className={`badge ${a.active ? 'on' : ''}`}>
                  {a.active ? t('alerts.active') : t('alerts.triggered', { date: a.triggered_at ? new Date(a.triggered_at).toLocaleString(intl) : '' })}
                </span>
                <button className="icon-btn" aria-label={t('common.delete')} onClick={() => void removeAlert(a.id)}><Icon name="trash" size={18} /></button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
