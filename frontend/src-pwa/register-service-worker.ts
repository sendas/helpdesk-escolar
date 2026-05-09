import { register } from 'register-service-worker'

register(process.env.SERVICE_WORKER_FILE as string, {
  ready () {
    console.log('[SW] App a funcionar em modo offline.')
  },
  registered () {
    console.log('[SW] Service worker registado.')
  },
  cached () {
    console.log('[SW] Conteúdo guardado em cache para uso offline.')
  },
  updatefound () {
    console.log('[SW] Nova versão disponível.')
  },
  updated () {
    console.log('[SW] Nova versão instalada.')
    // Reload so the user gets the latest version immediately
    window.location.reload()
  },
  offline () {
    console.log('[SW] Sem ligação à internet.')
  },
  error (err) {
    console.error('[SW] Erro ao registar:', err)
  },
})
