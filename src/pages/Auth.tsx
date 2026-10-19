import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useI18n } from '../i18n'
import { supabase } from '../lib/supabase'
import { Logo } from '../components/Logo'

function NotConfigured() {
  const { t } = useI18n()
  return <p className="notice warn">{t('auth.notConfigured')}</p>
}

function AuthCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="page auth-page">
      <div className="card glass auth-card">
        <Logo size={36} />
        <h1>{title}</h1>
        {supabase ? children : <NotConfigured />}
      </div>
    </div>
  )
}

export function Login() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    const { error } = await supabase!.auth.signInWithPassword({ email, password })
    setBusy(false)
    if (error) return setError(t('auth.errorLogin'))
    navigate('/')
  }

  return (
    <AuthCard title={t('auth.login')}>
      <form className="form" onSubmit={submit}>
        <label>{t('auth.email')}<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <label>{t('auth.password')}<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {error && <p className="notice warn" role="alert">{error}</p>}
        <button className="btn btn-primary" disabled={busy}>{t('auth.login')}</button>
      </form>
      <p className="small"><Link to="/forgot-password">{t('auth.forgot')}</Link></p>
      <p className="small">{t('auth.noAccount')} <Link to="/signup">{t('auth.signup')}</Link></p>
    </AuthCard>
  )
}

export function Signup() {
  const { t, lang } = useI18n()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [accept, setAccept] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (password.length < 8) return setError(t('auth.errorShort'))
    if (password !== confirm) return setError(t('auth.errorMismatch'))
    if (!accept) return setError(t('auth.errorTerms'))
    setBusy(true)
    // L'adresse de retour suit le domaine actuel : rien à changer le jour où
    // un vrai nom de domaine est branché.
    const { error } = await supabase!.auth.signUp({
      email, password, options: { emailRedirectTo: window.location.origin, data: { locale: lang } },
    })
    setBusy(false)
    if (error) return setError(error.message)
    setDone(true)
  }

  return (
    <AuthCard title={t('auth.signup')}>
      {done ? <p className="notice ok">{t('auth.checkEmail')}</p> : (
        <form className="form" onSubmit={submit}>
          <label>{t('auth.email')}<input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          <label>{t('auth.password')}<input type="password" autoComplete="new-password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
          <label>{t('auth.passwordConfirm')}<input type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required /></label>
          <label className="check">
            <input type="checkbox" checked={accept} onChange={(e) => setAccept(e.target.checked)} />
            <span>{t('auth.accept')} (<Link to="/legal/terms">{t('legal.terms')}</Link>, <Link to="/legal/privacy">{t('legal.privacy')}</Link>)</span>
          </label>
          {error && <p className="notice warn" role="alert">{error}</p>}
          <button className="btn btn-primary" disabled={busy}>{t('auth.signup')}</button>
        </form>
      )}
      <p className="small">{t('auth.haveAccount')} <Link to="/login">{t('auth.login')}</Link></p>
    </AuthCard>
  )
}

export function ForgotPassword() {
  const { t } = useI18n()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    await supabase!.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/reset-password` })
    setSent(true)
  }
  return (
    <AuthCard title={t('auth.forgot')}>
      {sent ? <p className="notice ok">{t('auth.resetSent')}</p> : (
        <form className="form" onSubmit={submit}>
          <label>{t('auth.email')}<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
          <button className="btn btn-primary">{t('auth.sendReset')}</button>
        </form>
      )}
    </AuthCard>
  )
}

export function ResetPassword() {
  const { t } = useI18n()
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [ok, setOk] = useState(false)
  useEffect(() => { void supabase?.auth.getSession() }, [])
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (password.length < 8) return setMsg(t('auth.errorShort'))
    const { error } = await supabase!.auth.updateUser({ password })
    setOk(!error)
    setMsg(error ? error.message : t('auth.passwordUpdated'))
  }
  return (
    <AuthCard title={t('auth.updatePassword')}>
      <form className="form" onSubmit={submit}>
        <label>{t('auth.newPassword')}<input type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        {msg && <p className={`notice ${ok ? 'ok' : 'warn'}`}>{msg}</p>}
        <button className="btn btn-primary">{t('auth.updatePassword')}</button>
      </form>
    </AuthCard>
  )
}
