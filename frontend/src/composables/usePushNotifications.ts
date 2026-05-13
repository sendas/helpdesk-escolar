import { ref, computed, onMounted } from 'vue'
import { getVapidPublicKey, subscribePush, unsubscribePush } from '../api/tickets'

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const arr = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return arr
}

// Returns any existing SW registration immediately (does not wait for activation).
async function getAnyRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!navigator.serviceWorker) return null
  try {
    const regs = await navigator.serviceWorker.getRegistrations()
    return regs[0] ?? null
  } catch { return null }
}

// Returns an *active* SW registration, registering /sw.js if none exists yet.
async function getActiveRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!navigator.serviceWorker) return null
  try {
    // Try existing registrations first — avoids waiting for ready.
    const regs = await navigator.serviceWorker.getRegistrations()
    const withActive = regs.find(r => r.active)
    if (withActive) return withActive

    // No active SW yet — register now and wait up to 12 s.
    const reg = regs[0] ?? await navigator.serviceWorker.register('/sw.js')
    return await Promise.race([
      new Promise<ServiceWorkerRegistration>((resolve) => {
        const check = () => { if (reg.active) { resolve(reg); return true } return false }
        if (check()) return
        reg.addEventListener('updatefound', () => {
          const sw = reg.installing ?? reg.waiting ?? reg.active
          if (!sw) return
          sw.addEventListener('statechange', () => { if (sw.state === 'activated') resolve(reg) })
        })
        // Poll as fallback (some browsers don't fire updatefound for existing installs).
        const t = setInterval(() => { if (check()) clearInterval(t) }, 300)
      }),
      new Promise<never>((_, reject) => setTimeout(() => reject(new Error('sw-timeout')), 12000)),
    ])
  } catch { return null }
}

const _isIos = typeof navigator !== 'undefined' &&
  /iPhone|iPad|iPod/.test(navigator.userAgent) && !(window as any).MSStream

// Push requires HTTPS (except localhost). Detect HTTP so we can show a clear message.
const _isHttp = typeof location !== 'undefined' &&
  location.protocol === 'http:' && location.hostname !== 'localhost'

export function usePushNotifications() {
  const isSupported = !_isHttp && 'Notification' in window && 'PushManager' in window && 'serviceWorker' in navigator
  const needsHttps = _isHttp
  const isStandalone = (navigator as any).standalone === true
  // Show install hint on any iOS browser (standalone = false), regardless of isSupported.
  const needsInstall = _isIos && !isStandalone && !_isHttp

  const permission = ref<NotificationPermission>(isSupported ? Notification.permission : 'denied')
  const isSubscribed = ref(false)
  const loading = ref(false)
  const error = ref('')
  const swState = ref<'unknown' | 'ok' | 'missing'>('unknown')

  const canEnable = computed(() => isSupported && !needsInstall && permission.value !== 'denied')

  async function _checkAndSync() {
    const reg = await getAnyRegistration()
    if (!reg) { swState.value = 'missing'; isSubscribed.value = false; return }
    swState.value = 'ok'
    try {
      const sub = await reg.pushManager.getSubscription()
      if (!sub) { isSubscribed.value = false; return }
      isSubscribed.value = true
      // Silently re-sync with server on every load (handles DB resets).
      await subscribePush(sub.toJSON() as PushSubscriptionJSON)
    } catch { /* non-fatal */ }
  }

  async function withTimeout<T>(promise: Promise<T>, ms: number, errorMsg: string): Promise<T> {
    return Promise.race([
      promise,
      new Promise<never>((_, reject) => setTimeout(() => reject(new Error(errorMsg)), ms))
    ])
  }

  async function requestAndSubscribe() {
    if (!isSupported || needsInstall) return
    loading.value = true
    error.value = ''
    try {
      const result = await withTimeout(Notification.requestPermission(), 10000, 'timeout-perm')
      permission.value = result
      if (result !== 'granted') { error.value = 'Permissão negada. Ative nas definições do browser.'; return }

      const reg = await getActiveRegistration()
      if (!reg) { error.value = 'O service worker não está pronto. Tente o botão "Reiniciar subscrição" abaixo.'; return }
      swState.value = 'ok'

      const old = await withTimeout(reg.pushManager.getSubscription(), 5000, 'timeout-sub')
      if (old) await withTimeout(old.unsubscribe(), 5000, 'timeout-unsub')

      const publicKey = await withTimeout(getVapidPublicKey(), 10000, 'timeout-vapid')
      const sub = await withTimeout(
        reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(publicKey) }),
        15000, 'timeout-subscribe'
      )
      await withTimeout(subscribePush(sub.toJSON() as PushSubscriptionJSON), 10000, 'timeout-api')
      isSubscribed.value = true
    } catch (err: any) {
      console.error('[Push] subscribe error:', err)
      if (err?.name === 'NotAllowedError') error.value = 'Permissão negada. Ative nas definições do browser.'
      else if (err?.message === 'sw-timeout') error.value = 'Service worker não activou. Tente "Reiniciar subscrição".'
      else if (err?.message?.startsWith('timeout-')) error.value = 'A operação demorou demasiado tempo. Tente reiniciar.'
      else error.value = err?.message || 'Erro desconhecido. Tente "Reiniciar subscrição".'
    } finally { loading.value = false }
  }

  async function unsubscribe() {
    loading.value = true
    error.value = ''
    try {
      const reg = await getAnyRegistration()
      if (reg) {
        const sub = await withTimeout(reg.pushManager.getSubscription(), 5000, 'timeout')
        if (sub) {
          await withTimeout(unsubscribePush(sub.endpoint), 5000, 'timeout').catch(() => {})
          await withTimeout(sub.unsubscribe(), 5000, 'timeout')
        }
      }
      isSubscribed.value = false
    } catch (err: any) {
      console.error('[Push] unsubscribe error:', err)
      error.value = 'Erro ao desativar. Tente "Reiniciar subscrição".'
    } finally { loading.value = false }
  }

  async function hardReset() {
    if (!isSupported || needsInstall) return
    loading.value = true
    error.value = ''
    try {
      const perm = await withTimeout(Notification.requestPermission(), 10000, 'timeout-perm')
      permission.value = perm
      if (perm !== 'granted') {
        error.value = 'Permissão negada. Ative nas definições do browser.'
        loading.value = false
        return
      }

      const regs = await withTimeout(navigator.serviceWorker.getRegistrations(), 5000, 'timeout-regs')
      for (const reg of regs) {
        try { 
          const sub = await withTimeout(reg.pushManager.getSubscription(), 3000, 'timeout');
          if (sub) { 
            await withTimeout(unsubscribePush(sub.endpoint), 3000, 'timeout').catch(() => {});
            await withTimeout(sub.unsubscribe(), 3000, 'timeout')
          } 
        } catch {}
        await withTimeout(reg.unregister(), 3000, 'timeout')
      }
      isSubscribed.value = false
      swState.value = 'missing'
      await requestAndSubscribe()
    } catch (err: any) {
      error.value = 'Erro no reset: ' + (err?.message || 'desconhecido')
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    if (isSupported && !needsInstall) {
      permission.value = Notification.permission
      _checkAndSync()
    }
  })

  return { isSupported, needsHttps, needsInstall, permission, isSubscribed, canEnable, loading, error, swState, requestAndSubscribe, unsubscribe, hardReset }
}
