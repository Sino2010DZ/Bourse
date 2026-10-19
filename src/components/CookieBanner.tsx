import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n'
import { getConsent, OPEN_CONSENT_EVENT, setConsent } from '../lib/consent'

// Bandeau cookies : rien de publicitaire n'est chargé sans accord explicite.
export function CookieBanner() {
  const { t } = useI18n()
  const [open, setOpen] = useState(() => getConsent() === null)
  const [details, setDetails] = useState(false)
  const [ads, setAds] = useState(() => getConsent()?.ads ?? false)

  useEffect(() => {
    const onOpen = () => { setAds(getConsent()?.ads ?? false); setDetails(true); setOpen(true) }
    window.addEventListener(OPEN_CONSENT_EVENT, onOpen)
    return () => window.removeEventListener(OPEN_CONSENT_EVENT, onOpen)
  }, [])

  if (!open) return null
  const done = (value: boolean) => { setConsent(value); setOpen(false); setDetails(false) }

  return (
    <div className="cookie glass" role="dialog" aria-modal="false" aria-labelledby="cookie-title">
      <h2 id="cookie-title">{t('cookies.title')}</h2>
      <p>{t('cookies.text')} <Link to="/legal/privacy">{t('cookies.more')}</Link></p>
      {details && (
        <div className="cookie-details">
          <label className="switch-row">
            <span><strong>{t('cookies.necessary')}</strong><small>{t('cookies.necessaryDesc')}</small></span>
            <input type="checkbox" checked disabled />
          </label>
          <label className="switch-row">
            <span><strong>{t('cookies.ads')}</strong><small>{t('cookies.adsDesc')}</small></span>
            <input type="checkbox" checked={ads} onChange={(e) => setAds(e.target.checked)} />
          </label>
        </div>
      )}
      <div className="cookie-actions">
        <button className="btn" onClick={() => done(false)}>{t('cookies.rejectAll')}</button>
        {details
          ? <button className="btn" onClick={() => done(ads)}>{t('cookies.save')}</button>
          : <button className="btn" onClick={() => setDetails(true)}>{t('cookies.customize')}</button>}
        <button className="btn btn-primary" onClick={() => done(true)}>{t('cookies.acceptAll')}</button>
      </div>
    </div>
  )
}
