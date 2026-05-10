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

async function getActiveSwRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!navigator.serviceWorker) return null
  try {
    // navigator.serviceWorker.ready only resolves when a SW is in 'activated' state.
    // Race with a 10 s timeout so we don't block forever if SW never activates.
    return await Promise.race([
      navigator.serviceWorker.ready,
      new Promise<never>((_, reject) => setTimeout(() => reject(new Error('sw-timeout')), 10000)),
    ]) as ServiceWorkerRegistration
  } catch {
    return null
  }
}

const _isIos = typeof navigator !== 'undefined' &&
  /iPhone|iPad|iPod/.test(navigator.userAgent) &&
  !(window as any).MSStream

export function usePushNotifications() {
  const isSupported = 'Notification' in window && 'PushManager' in window && 'serviceWorker' in navigator

  // On iOS, push only works in standalone (PWA) mode, not in Safari browser.
  const isStandalone = (navigator as any).standalone === true
  const needsInstall = _isIos && !isStandalone

  const permission = ref<NotificationPermission>(isSupported ? Notification.permission : 'denied')
  const isSubscribed = ref(false)
  const loading = ref(false)
  const error = ref('')

  const canEnable = computed(() => isSupported && !needsInstall && permission.value !== 'denied')

  // Check browser subscription state and, if found, silently re-sync with the
  // server. This handles the case where the DB was reset (container rebuild) but
  // the browser still holds a valid subscription.
  async function _checkAndSync() {
    const reg = await getActiveSwRegistration()
    if (!reg) return
    const sub = await reg.pushManager.getSubscription()
    if (!sub) {
      isSubscribed.value = false
      return
    }
    isSubscribed.value = true
    // Re-register with server (upsert — safe to call on every load).
    try {
      await subscribePush(sub.toJSON() as PushSubscriptionJSON)
    } catch {
      // Non-fatal: network may be down; subscription shown as active locally.
    }
  }

  async function requestAndSubscribe() {
    if (!isSupported || needsInstall) return
    loading.value = true
    error.value = ''
    try {
      const result = await Notification.requestPermission()
      permission.value = result
      if (result !== 'granted') {
        error.value = 'Permissão negada. Ative nas definições do browser.'
        return
      }

      const reg = await getActiveSwRegistration()
      if (!reg) {
        error.value = 'Service worker não está pronto. Recarregue a página e tente novamente.'
        return
      }

      // If there's an existing subscription (possibly with an old VAPID key),
      // drop it first so we always get a fresh one with the current server key.
      const existing = await reg.pushManager.getSubscription()
      if (existing) await existing.unsubscribe()

      const publicKey = await getVapidPublicKey()
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      })
      await subscribePush(sub.toJSON() as PushSubscriptionJSON)
      isSubscribed.value = true
    } catch (err: any) {
      console.error('[Push] Erro ao subscrever:', err)
      if (err?.name === 'NotAllowedError') {
        error.value = 'Permissão negada. Ative nas definições do browser.'
      } else if (err?.message === 'sw-timeout') {
        error.value = 'O service worker demorou demasiado. Recarregue a página.'
      } else if (err?.name === 'AbortError' || err?.message?.includes('push service')) {
        error.value = 'Erro a contactar o serviço push do browser. Verifique a ligação à internet.'
      } else {
        error.value = err?.message || 'Erro desconhecido ao ativar notificações.'
      }
    } finally {
      loading.value = false
    }
  }

  // Force unsubscribe in browser + remove from server.
  async function unsubscribe() {
    loading.value = true
    error.value = ''
    try {
      const reg = await getActiveSwRegistration()
      if (!reg) return
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        await unsubscribePush(sub.endpoint)
        await sub.unsubscribe()
      }
      isSubscribed.value = false
    } catch (err: any) {
      console.error('[Push] Erro ao cancelar:', err)
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

  return { isSupported, needsInstall, permission, isSubscribed, canEnable, loading, error, requestAndSubscribe, unsubscribe }
}
