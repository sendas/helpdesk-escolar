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

// Always wait for an *active* SW — avoids the race condition where
// window.__swRegistration is set but the SW is still in 'installing' state.
async function getSwRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!navigator.serviceWorker) return null
  try {
    return await navigator.serviceWorker.ready
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

  async function _checkSubscribed() {
    const reg = await getSwRegistration()
    if (!reg) return
    const sub = await reg.pushManager.getSubscription()
    isSubscribed.value = !!sub
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

      const reg = await Promise.race([
        getSwRegistration(),
        new Promise<null>((_, reject) => setTimeout(() => reject(new Error('timeout')), 8000)),
      ]) as ServiceWorkerRegistration | null

      if (!reg) {
        error.value = 'Service worker não está pronto. Recarregue a página e tente novamente.'
        return
      }

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
      } else if (err?.message === 'timeout') {
        error.value = 'O service worker demorou demasiado. Recarregue a página.'
      } else if (err?.name === 'AbortError' || err?.message?.includes('push service')) {
        error.value = 'Erro a contactar o serviço push do browser. Verifique a ligação.'
      } else {
        error.value = err?.message || 'Erro desconhecido ao ativar notificações.'
      }
    } finally {
      loading.value = false
    }
  }

  async function unsubscribe() {
    loading.value = true
    error.value = ''
    try {
      const reg = await getSwRegistration()
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
    if (isSupported) {
      permission.value = Notification.permission
      _checkSubscribed()
    }
  })

  return { isSupported, needsInstall, permission, isSubscribed, canEnable, loading, error, requestAndSubscribe, unsubscribe }
}
