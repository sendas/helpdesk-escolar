// Shared helpers for the live-support bubble (SupportWidget.vue): open it from anywhere and describe its hours.
import { ref } from 'vue'
import { getSupportStatus, type SupportStatus } from '../api/chat'

const OPEN_EVENT = 'helpdesk:open-support-chat'

export function openSupportChat() {
  window.dispatchEvent(new CustomEvent(OPEN_EVENT))
}

export function onOpenSupportChat(handler: () => void) {
  window.addEventListener(OPEN_EVENT, handler)
  return () => window.removeEventListener(OPEN_EVENT, handler)
}

// One shared copy of the support status, refreshed every few minutes
export const supportStatus = ref<SupportStatus | null>(null)
let lastLoad = 0
export async function loadSupportStatus(force = false) {
  if (!force && supportStatus.value && Date.now() - lastLoad < 120000) return supportStatus.value
  lastLoad = Date.now()
  try { supportStatus.value = await getSupportStatus() } catch { /* ignore */ }
  return supportStatus.value
}

const DAY_NAMES: Record<string, string> = { '1': 'segunda', '2': 'terça', '3': 'quarta', '4': 'quinta', '5': 'sexta', '6': 'sábado', '7': 'domingo' }

function hh(t: string) {
  return t.endsWith(':00') ? `${Number(t.slice(0, 2))}h` : t.replace(':', 'h')
}

// "até às 17h" when open; "abre terça às 10h" when closed
export function supportWhen(status: SupportStatus | null): string {
  if (!status) return ''
  const now = new Date()
  const today = String(((now.getDay() + 6) % 7) + 1)
  const hhmm = now.toTimeString().slice(0, 5)
  const day = status.hours[today]
  if (status.open_now && day) return `até às ${hh(day.end)}`
  for (let i = 0; i < 7; i++) {
    const key = String(((Number(today) - 1 + i) % 7) + 1)
    const d = status.hours[key]
    if (!d?.enabled) continue
    if (i === 0 && hhmm >= d.start) continue
    const when = i === 0 ? 'hoje' : i === 1 ? 'amanhã' : DAY_NAMES[key]
    return `abre ${when} às ${hh(d.start)}`
  }
  return ''
}
