import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'
import { APP_NAME } from '../config'
import { Icon } from './Icon'

interface InstallEvent extends Event { prompt: () => Promise<void> }

let deferred: InstallEvent | null = null
const listeners = new Set<() => void>()
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault()
  deferred = e as InstallEvent
  listeners.forEach((l) => l())
})

export function useInstallPrompt() {
  const [, force] = useState(0)
  useEffect(() => {
    const l = () => force((n) => n + 1)
    listeners.add(l)
    return () => { listeners.delete(l) }
  }, [])
  return deferred
    ? async () => { await deferred?.prompt(); deferred = null; listeners.forEach((l) => l()) }
    : null
}

// Proposé sur PC / Android (Chrome, Edge). Sur iPhone, voir la page Compte.
export function InstallBanner() {
  const { t } = useI18n()
  const install = useInstallPrompt()
  const [hidden, setHidden] = useState(() => sessionStorage.getItem('tg.installHidden') === '1')
  if (!install || hidden) return null
  return (
    <div className="install glass">
      <span>{t('install.banner', { app: APP_NAME })}</span>
      <button className="btn btn-primary btn-sm" onClick={install}>{t('install.button')}</button>
      <button className="icon-btn" aria-label={t('common.close')} onClick={() => { sessionStorage.setItem('tg.installHidden', '1'); setHidden(true) }}>
        <Icon name="close" size={16} />
      </button>
    </div>
  )
}
