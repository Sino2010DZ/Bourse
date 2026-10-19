import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useI18n, LANGUAGES, type Lang } from '../i18n'
import { useAuth } from '../context/AuthContext'
import { useTheme, type ThemeChoice } from '../context/ThemeContext'
import { useInstallPrompt } from '../components/InstallBanner'
import { NotificationsControl } from './Alerts'
import { isStandalone } from '../lib/push'
import { openConsentSettings } from '../lib/consent'
import { supabase } from '../lib/supabase'
import { premiumModeActive } from '../config'
import { openPortal } from '../lib/billing'

export function Account() {
  const { t, lang, setLang, intl } = useI18n()
  const { user, plan, configured, signOut, session, renewsAt, hasBilling, refreshPlan } = useAuth()
  const [params, setParams] = useSearchParams()
  const [waiting, setWaiting] = useState(params.get('checkout') === 'success')

  // Retour de Stripe : on attend que le serveur ait reçu la confirmation de paiement.
  useEffect(() => {
    if (!waiting) return
    if (plan === 'premium') {
      setWaiting(false)
      setParams({}, { replace: true })
      return
    }
    const timer = window.setInterval(() => void refreshPlan(), 2000)
    const stop = window.setTimeout(() => setWaiting(false), 60_000)
    return () => { window.clearInterval(timer); window.clearTimeout(stop) }
  }, [waiting, plan, refreshPlan, setParams])

  const manage = async () => {
    if (!session) return
    try { window.location.href = await openPortal(session) } catch { alert(t('common.error')) }
  }
  const { choice, setChoice } = useTheme()
  const install = useInstallPrompt()

  const deleteAccount = async () => {
    if (!session || !confirm(t('account.deleteConfirm'))) return
    const res = await fetch('/api/delete-account', { method: 'POST', headers: { Authorization: `Bearer ${session.access_token}` } })
    if (res.ok) await supabase?.auth.signOut()
    else alert(t('common.error'))
  }

  return (
    <div className="page">
      <h1>{t('account.title')}</h1>

      <section className="card glass">
        {user ? (
          <>
            <p><strong>{user.email}</strong></p>
            {premiumModeActive() && <p>{t('account.plan')} : <span className={`badge ${plan === 'premium' ? 'on' : ''}`}>{plan === 'premium' ? t('common.premium') : t('common.free')}</span>
              {plan === 'free' && <> · <Link to="/pricing">{t('common.upgrade')}</Link></>}</p>}
            {waiting && <p className="notice">{t('pricing.success')}</p>}
            {plan === 'premium' && params.get('checkout') === null && renewsAt && (
              <p className="muted small">{t('pricing.renews', { date: new Date(renewsAt).toLocaleDateString(intl) })}</p>
            )}
            <div className="actions">
              {hasBilling && <button className="btn" onClick={() => void manage()}>{t('pricing.manage')}</button>}
              <button className="btn" onClick={() => void signOut()}>{t('auth.logout')}</button>
            </div>
          </>
        ) : (
          <>
            <p>{t('account.plan')} : <span className="badge">{premiumModeActive() && plan === 'premium' ? t('common.premium') : t('account.guest')}</span></p>
            <p className="muted small">{t('auth.guestNote')}</p>
            {configured ? (
              <div className="actions">
                <Link className="btn btn-primary" to="/signup">{t('auth.signup')}</Link>
                <Link className="btn" to="/login">{t('auth.login')}</Link>
              </div>
            ) : <p className="notice warn">{t('auth.notConfigured')}</p>}
          </>
        )}
      </section>

      <section className="card glass settings">
        <label>{t('account.language')}
          <select value={lang} onChange={(e) => setLang(e.target.value as Lang)}>
            {(Object.keys(LANGUAGES) as Lang[]).map((l) => <option key={l} value={l}>{LANGUAGES[l].label}</option>)}
          </select>
        </label>
        <div>
          <span className="label">{t('account.theme')}</span>
          <div className="segmented">
            {(['system', 'light', 'dark'] as ThemeChoice[]).map((c) => (
              <button key={c} className={choice === c ? 'on' : ''} aria-pressed={choice === c} onClick={() => setChoice(c)}>{t(`account.themes.${c}`)}</button>
            ))}
          </div>
        </div>
        <div>
          <span className="label">{t('account.notifications')}</span>
          <NotificationsControl />
        </div>
        <div>
          <span className="label">{t('account.install')}</span>
          {isStandalone() ? <p className="small">{t('account.installed')}</p>
            : install ? <button className="btn" onClick={install}>{t('install.button')}</button>
            : <p className="small muted">{t('account.installIos')}</p>}
        </div>
        <button className="link-btn" onClick={openConsentSettings}>{t('account.cookieSettings')}</button>
      </section>

      {user && (
        <section className="card glass">
          <button className="btn btn-danger" onClick={() => void deleteAccount()}>{t('account.deleteAccount')}</button>
        </section>
      )}
    </div>
  )
}
