import { Link } from 'react-router-dom'
import { useI18n, LANGUAGES, type Lang } from '../i18n'
import { useAuth } from '../context/AuthContext'
import { useTheme, type ThemeChoice } from '../context/ThemeContext'
import { useInstallPrompt } from '../components/InstallBanner'
import { NotificationsControl } from './Alerts'
import { isStandalone } from '../lib/push'
import { openConsentSettings } from '../lib/consent'
import { supabase } from '../lib/supabase'

export function Account() {
  const { t, lang, setLang } = useI18n()
  const { user, plan, configured, signOut, session } = useAuth()
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
            <p>{t('account.plan')} : <span className={`badge ${plan === 'premium' ? 'on' : ''}`}>{plan === 'premium' ? t('common.premium') : t('common.free')}</span>
              {plan === 'free' && <> · <Link to="/pricing">{t('common.upgrade')}</Link></>}</p>
            <button className="btn" onClick={() => void signOut()}>{t('auth.logout')}</button>
          </>
        ) : (
          <>
            <p>{t('account.plan')} : <span className="badge">{plan === 'premium' ? t('common.premium') : t('account.guest')}</span></p>
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
