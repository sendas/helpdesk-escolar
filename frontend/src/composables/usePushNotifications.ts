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

  async function requestAndSubscribe() {
    if (!isSupported || needsInstall) return
    loading.value = true
    error.value = ''
    try {
      const result = await Notification.requestPermission()
      permission.value = result
      if (result !== 'granted') { error.value = 'Permissão negada. Ative nas definições do browser.'; return }

      const reg = await getActiveRegistration()
      if (!reg) { error.value = 'O service worker não está pronto. Tente o botão "Reiniciar subscrição" abaixo.'; return }
      swState.value = 'ok'

      // Drop any existing browser subscription first (may have stale VAPID key).
      const old = await reg.pushManager.getSubscription()
      if (old) await old.unsubscribe()

      const publicKey = await getVapidPublicKey()
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(publicKey) })
      await subscribePush(sub.toJSON() as PushSubscriptionJSON)
      isSubscribed.value = true
    } catch (err: any) {
      console.error('[Push] subscribe error:', err)
      if (err?.name === 'NotAllowedError') error.value = 'Permissão negada. Ative nas definições do browser.'
      else if (err?.message === 'sw-timeout') error.value = 'Service worker não activou. Tente "Reiniciar subscrição".'
      else error.value = err?.message || 'Erro desconhecido. Tente "Reiniciar subscrição".'
    } finally { loading.value = false }
  }

  async function unsubscribe() {
    loading.value = true
    error.value = ''
    try {
      const reg = await getAnyRegistration()  // does NOT wait for activation
      if (reg) {
        const sub = await reg.pushManager.getSubscription()
        if (sub) { await unsubscribePush(sub.endpoint).catch(() => {}); await sub.unsubscribe() }
      }
      isSubscribed.value = false
    } catch (err: any) {
      console.error('[Push] unsubscribe error:', err)
      error.value = 'Erro ao desativar. Tente "Reiniciar subscrição".'
    } finally { loading.value = false }
  }

  // Nuclear reset: unregister all SWs, clear all push subscriptions, re-register.
  async function hardReset() {
    loading.value = true
    error.value = ''
    try {
      const regs = await navigator.serviceWorker.getRegistrations()
      for (const reg of regs) {
        try { const sub = await reg.pushManager.getSubscription(); if (sub) { await unsubscribePush(sub.endpoint).catch(() => {}); await sub.unsubscribe() } } catch {}
        await reg.unregister()
      }
      isSubscribed.value = false
      swState.value = 'missing'
      // Re-register SW and subscribe.
      await requestAndSubscribe()
    } catch (err: any) {
      error.value = 'Erro no reset: ' + (err?.message || 'desconhecido')
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
