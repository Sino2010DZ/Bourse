/// <reference lib="webworker" />
// Service worker : fonctionnement hors-ligne de l'app + notifications d'alertes.
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'

declare let self: ServiceWorkerGlobalScope & { __WB_MANIFEST: (string | { url: string; revision: string | null })[] }

self.skipWaiting()
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()
registerRoute(new NavigationRoute(createHandlerBoundToURL('/index.html'), { denylist: [/^\/api\//, /^\/\.netlify\//] }))

interface AlertPayload { title: string; body: string; url?: string; tag?: string }

self.addEventListener('push', (event) => {
  let data: AlertPayload = { title: 'Alerte', body: '' }
  try { data = event.data?.json() as AlertPayload } catch { data.body = event.data?.text() ?? '' }
  event.waitUntil(self.registration.showNotification(data.title, {
    body: data.body,
    icon: '/icons/icon-192.png',
    badge: '/icons/badge-72.png',
    tag: data.tag,
    data: { url: data.url ?? '/alerts' },
  }))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data as { url?: string })?.url ?? '/'
  event.waitUntil((async () => {
    const all = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    const existing = all.find((c) => 'focus' in c) as WindowClient | undefined
    if (existing) { await existing.navigate(url); return existing.focus() }
    return self.clients.openWindow(url)
  })())
})
