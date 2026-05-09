/// <reference lib="webworker" />
import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'

declare const self: ServiceWorkerGlobalScope

cleanupOutdatedCaches()

// Quasar / vite-plugin-pwa injects the precache manifest here
precacheAndRoute(self.__WB_MANIFEST)

self.skipWaiting()
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

// ----- Push notifications -----

self.addEventListener('push', (event) => {
  if (!event.data) return
  let data: { title?: string; body?: string; url?: string } = {}
  try {
    data = event.data.json()
  } catch {
    data = { title: 'Helpdesk', body: event.data.text() }
  }

  event.waitUntil(
    self.registration.showNotification(data.title || 'Helpdesk Escolar', {
      body: data.body || '',
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-96x96.png',
      data: { url: data.url || '/' },
      tag: 'helpdesk',
      renotify: true,
    }),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = (event.notification.data as { url?: string })?.url || '/'

  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        const existing = clients.find((c) => c.url.startsWith(self.location.origin))
        if (existing) {
          existing.focus()
          return (existing as WindowClient).navigate(target)
        }
        return self.clients.openWindow(target)
      }),
  )
})
