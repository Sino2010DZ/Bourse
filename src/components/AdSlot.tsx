import { useEffect, useRef, useState } from 'react'
import { env, PLAN_LIMITS } from '../config'
import { useAuth } from '../context/AuthContext'
import { CONSENT_EVENT, getConsent } from '../lib/consent'

// Emplacement publicitaire discret (plan gratuit uniquement).
// Ne s'affiche que si : AdSense est configuré (VITE_ADSENSE_CLIENT),
// l'utilisateur a accepté les cookies publicitaires, et il est en plan gratuit.
export function AdSlot({ slot }: { slot?: string }) {
  const { plan } = useAuth()
  const [consent, setConsentState] = useState(() => getConsent()?.ads ?? false)
  const ref = useRef<HTMLModElement>(null)

  useEffect(() => {
    const onChange = () => setConsentState(getConsent()?.ads ?? false)
    window.addEventListener(CONSENT_EVENT, onChange)
    return () => window.removeEventListener(CONSENT_EVENT, onChange)
  }, [])

  const active = !!env.adsenseClient && !!slot && consent && PLAN_LIMITS[plan].ads

  useEffect(() => {
    if (!active) return
    if (!document.querySelector('script[data-adsense]')) {
      const s = document.createElement('script')
      s.async = true
      s.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${env.adsenseClient}`
      s.crossOrigin = 'anonymous'
      s.dataset.adsense = '1'
      document.head.appendChild(s)
    }
    try {
      const w = window as unknown as { adsbygoogle: unknown[] }
      ;(w.adsbygoogle = w.adsbygoogle || []).push({})
    } catch { /* ignore */ }
  }, [active])

  if (!active) return null
  return (
    <div className="ad glass">
      <ins ref={ref} className="adsbygoogle" style={{ display: 'block' }} data-ad-client={env.adsenseClient}
        data-ad-slot={slot} data-ad-format="auto" data-full-width-responsive="true" />
    </div>
  )
}
