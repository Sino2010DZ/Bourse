import { env } from '../config'
import { supabase } from './supabase'

export type PushStatus = 'unsupported' | 'ios-install' | 'denied' | 'off' | 'on' | 'unconfigured'

export const isIos = () => /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
export const isStandalone = () =>
  window.matchMedia?.('(display-mode: standalone)').matches || (navigator as Navigator & { standalone?: boolean }).standalone === true

function urlBase64ToUint8Array(base64: string) {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const raw = atob((base64 + padding).replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(raw, (c) => c.charCodeAt(0))
}

export async function getPushStatus(): Promise<PushStatus> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
    return isIos() && !isStandalone() ? 'ios-install' : 'unsupported'
  }
  if (!env.vapidPublicKey || !supabase) return 'unconfigured'
  if (Notification.permission === 'denied') return 'denied'
  const reg = await navigator.serviceWorker.getRegistration()
  const sub = await reg?.pushManager.getSubscription()
  return sub ? 'on' : 'off'
}

// Demande l'autorisation puis enregistre l'appareil pour recevoir les alertes.
export async function enablePush(): Promise<PushStatus> {
  if (!env.vapidPublicKey || !supabase) return 'unconfigured'
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') return 'denied'
  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(env.vapidPublicKey),
  })
  const json = sub.toJSON()
  await supabase.from('push_subscriptions').delete().eq('endpoint', sub.endpoint)
  const { error } = await supabase.from('push_subscriptions').insert({
    endpoint: sub.endpoint,
    p256dh: json.keys?.p256dh,
    auth: json.keys?.auth,
    user_agent: navigator.userAgent.slice(0, 200),
  })
  return error ? 'off' : 'on'
}
