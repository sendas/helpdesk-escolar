import { register } from 'register-service-worker'

register(process.env.SERVICE_WORKER_FILE as string, {
  ready () {
    console.log('[SW] App a funcionar.')
  },
  registered (registration) {
    console.log('[SW] Service worker registado.')
    // Store the registration so usePushNotifications can access it
    ;(window as any).__swRegistration = registration
    window.dispatchEvent(new CustomEvent('sw-registered', { detail: registration }))
  },
  cached () {
    console.log('[SW] Conteúdo em cache para uso offline.')
  },
  updatefound () {
    console.log('[SW] Nova versão disponível, a instalar…')
  },
  updated () {
    console.log('[SW] Nova versão instalada, a recarregar.')
    window.location.reload()
  },
  offline () {
    console.log('[SW] Sem ligação à internet.')
  },
  error (err) {
    console.error('[SW] Erro ao registar:', err)
  },
})
