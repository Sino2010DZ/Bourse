import { useEffect, useState } from 'react'
import { useI18n } from '../i18n'

export function OfflineBanner() {
  const { t } = useI18n()
  const [online, setOnline] = useState(() => navigator.onLine)
  useEffect(() => {
    const on = () => setOnline(true)
    const off = () => setOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])
  return online ? null : <p className="notice warn offline" role="status">{t('offline')}</p>
}
