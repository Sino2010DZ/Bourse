import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n, type MessageKey } from '../i18n'
import { useAuth } from '../context/AuthContext'
import { PRICES } from '../config'
import { Icon } from '../components/Icon'
import { startCheckout, useBillingEnabled } from '../lib/billing'

type Cur = keyof typeof PRICES

export function Pricing() {
  const { t, formatMoney } = useI18n()
  const { plan, user, session } = useAuth()
  const billing = useBillingEnabled()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(false)

  const subscribe = async () => {
    if (!session) return
    setBusy(true)
    setError(false)
    try {
      window.location.href = await startCheckout(session, cur, yearly ? 'yearly' : 'monthly')
    } catch {
      setError(true)
      setBusy(false)
    }
  }
  const [yearly, setYearly] = useState(true)
  const [cur, setCur] = useState<Cur>('CHF')
  const price = yearly ? PRICES[cur].yearly : PRICES[cur].monthly
  const savePct = Math.round((1 - PRICES[cur].yearly / (PRICES[cur].monthly * 12)) * 100)

  const features = (keys: MessageKey[]) => (
    <ul className="features">{keys.map((k) => <li key={k}><Icon name="check" size={16} /> {t(k)}</li>)}</ul>
  )

  return (
    <div className="page">
      <div className="hero">
        <h1>{t('pricing.title')}</h1>
        <p className="muted">{t('pricing.subtitle')}</p>
      </div>
      <div className="pricing-switches">
        <div className="segmented">
          <button className={!yearly ? 'on' : ''} onClick={() => setYearly(false)}>{t('pricing.monthly')}</button>
          <button className={yearly ? 'on' : ''} onClick={() => setYearly(true)}>{t('pricing.yearly')} <span className="save">{t('pricing.save', { pct: savePct })}</span></button>
        </div>
        <div className="segmented">
          {(Object.keys(PRICES) as Cur[]).map((c) => <button key={c} className={cur === c ? 'on' : ''} onClick={() => setCur(c)}>{c}</button>)}
        </div>
      </div>
      <div className="plans">
        <section className="card glass plan">
          <h2>{t('common.free')}</h2>
          <p className="plan-price">{formatMoney(0, cur)}</p>
          {features(['pricing.freeF1', 'pricing.freeF2', 'pricing.freeF3'])}
          {plan === 'free' && <span className="badge">{t('pricing.current')}</span>}
        </section>
        <section className="card glass plan featured">
          <h2>{t('common.premium')}</h2>
          <p className="plan-price">{formatMoney(price, cur)} <small>{yearly ? t('pricing.perYear') : t('pricing.perMonth')}</small></p>
          {features(['pricing.premiumF1', 'pricing.premiumF2', 'pricing.premiumF3', 'pricing.premiumF4'])}
          {plan === 'premium' ? <span className="badge on">{t('pricing.current')}</span>
            : !billing ? <button className="btn btn-primary" disabled>{t('pricing.soon')}</button>
            : !user ? <Link className="btn btn-primary" to="/signup">{t('pricing.loginToSubscribe')}</Link>
            : <button className="btn btn-primary" disabled={busy} onClick={() => void subscribe()}>{t('pricing.subscribe')}</button>}
          {billing && <p className="muted small">{t('pricing.secure')}</p>}
          {error && <p className="notice warn" role="alert">{t('common.error')}</p>}
        </section>
      </div>
    </div>
  )
}
