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

async function getSwRegistration(): Promise<ServiceWorkerRegistration | null> {
  if ((window as any).__swRegistration) return (window as any).__swRegistration
  if (!navigator.serviceWorker) return null
  try {
    return await navigator.serviceWorker.ready
  } catch {
    return null
  }
}

export function usePushNotifications() {
  const isSupported = 'Notification' in window && 'PushManager' in window && 'serviceWorker' in navigator
  const permission = ref<NotificationPermission>(isSupported ? Notification.permission : 'denied')
  const isSubscribed = ref(false)
  const loading = ref(false)

  const canEnable = computed(() => isSupported && permission.value !== 'denied')

  async function _checkSubscribed() {
    const reg = await getSwRegistration()
    if (!reg) return
    const sub = await reg.pushManager.getSubscription()
    isSubscribed.value = !!sub
  }

  async function requestAndSubscribe() {
    if (!isSupported) return
    loading.value = true
    try {
      const result = await Notification.requestPermission()
      permission.value = result
      if (result !== 'granted') return

      const reg = await getSwRegistration()
      if (!reg) return

      const publicKey = await getVapidPublicKey()
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      })
      await subscribePush(sub.toJSON() as PushSubscriptionJSON)
      isSubscribed.value = true
    } catch (err) {
      console.error('[Push] Erro ao subscrever:', err)
    } finally {
      loading.value = false
    }
  }

  async function unsubscribe() {
    loading.value = true
    try {
      const reg = await getSwRegistration()
      if (!reg) return
      const sub = await reg.pushManager.getSubscription()
      if (sub) {
        await unsubscribePush(sub.endpoint)
        await sub.unsubscribe()
      }
      isSubscribed.value = false
    } catch (err) {
      console.error('[Push] Erro ao cancelar:', err)
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    if (isSupported) {
      permission.value = Notification.permission
      _checkSubscribed()
      window.addEventListener('sw-registered', () => _checkSubscribed(), { once: true })
    }
  })

  return { isSupported, permission, isSubscribed, canEnable, loading, requestAndSubscribe, unsubscribe }
}
