if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const swUrl = (process.env.SERVICE_WORKER_FILE as string) || '/sw.js'
      const registration = await navigator.serviceWorker.register(swUrl, { scope: '/' })

      // Expose for usePushNotifications composable
      ;(window as any).__swRegistration = registration
      window.dispatchEvent(new CustomEvent('sw-registered', { detail: registration }))

      // Auto-reload when a new version activates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing
        if (!newWorker) return
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('[SW] Nova versão instalada, a recarregar.')
            window.location.reload()
          }
        })
      })

      console.log('[SW] Registado com sucesso.')
    } catch (err) {
      console.error('[SW] Erro ao registar:', err)
    }
  })
}
