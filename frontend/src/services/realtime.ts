// Real-time channel: one WebSocket per browser tab, falling back to HTTP polling when a proxy blocks WebSockets.
// Components subscribe with `onRealtime(type, handler)`; see backend app/services/realtime.py for the events.
import { ref } from 'vue'
import { api } from '../boot/axios'

type Handler = (event: any) => void
export type RealtimeStatus = 'offline' | 'connecting' | 'live' | 'polling'

export const realtimeStatus = ref<RealtimeStatus>('offline')

const handlers = new Map<string, Set<Handler>>()
let ws: WebSocket | null = null
let token: string | null = null
let lastSeq = 0
// Identifies the server process: after a restart its sequence numbers start again from 1
let serverBoot = ''
let everConnected = false
// Live events that arrive while missed events are still being fetched
let catchingUp = false
const heldBack: any[] = []
let wsFailures = 0
let pollTimer: ReturnType<typeof setTimeout> | null = null
let retryTimer: ReturnType<typeof setTimeout> | null = null
let stopped = true
const outbox: any[] = []
// Messages re-sent after reconnecting (e.g. "I am looking at ticket 12")
const sticky = new Map<string, any>()

const POLL_MS = 4000

function emit(event: any) {
  if (typeof event.seq === 'number') {
    if (event.seq <= lastSeq) return
    lastSeq = event.seq
  }
  handlers.get(event.type)?.forEach((h) => { try { h(event) } catch { /* ignore */ } })
  handlers.get('*')?.forEach((h) => { try { h(event) } catch { /* ignore */ } })
}

export function onRealtime(type: string, handler: Handler): () => void {
  if (!handlers.has(type)) handlers.set(type, new Set())
  handlers.get(type)!.add(handler)
  return () => handlers.get(type)?.delete(handler)
}

export function sendRealtime(message: any, stickyKey?: string) {
  if (stickyKey) sticky.set(stickyKey, message)
  if (realtimeStatus.value === 'live' && ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message))
  } else if (realtimeStatus.value === 'polling') {
    api.post('/api/v1/realtime/send', message).catch(() => {})
  } else {
    outbox.push(message)
  }
}

export function forgetSticky(key: string) {
  sticky.delete(key)
}

function flush() {
  const pending = [...sticky.values(), ...outbox.splice(0)]
  pending.forEach((m) => sendRealtime(m))
}

function wsUrl() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${location.host}/api/v1/realtime/ws?token=${encodeURIComponent(token ?? '')}`
}

function openSocket() {
  if (stopped || !token) return
  realtimeStatus.value = realtimeStatus.value === 'polling' ? 'polling' : 'connecting'
  let opened = false
  let socket: WebSocket
  try {
    socket = new WebSocket(wsUrl())
  } catch {
    onSocketFailure()
    return
  }
  ws = socket
  const openTimeout = setTimeout(() => { if (!opened) socket.close() }, 6000)
  socket.onmessage = (msg) => {
    let event: any
    try { event = JSON.parse(msg.data) } catch { return }
    if (event.type === 'hello') {
      opened = true
      clearTimeout(openTimeout)
      wsFailures = 0
      stopPolling()
      const restarted = !!serverBoot && event.boot !== serverBoot
      serverBoot = event.boot ?? ''
      // Catch up on anything missed while reconnecting/polling; after a server restart the old numbers mean
      // nothing, so start again from now (pages reload their data on "realtime.connected")
      if (lastSeq > 0 && !restarted) catchUp()
      else lastSeq = event.seq
      realtimeStatus.value = 'live'
      flush()
      announceConnected()
      return
    }
    if (event.type === 'ping') return
    if (catchingUp) heldBack.push(event)
    else emit(event)
  }
  socket.onclose = () => {
    clearTimeout(openTimeout)
    if (ws === socket) ws = null
    if (stopped) return
    if (!opened) onSocketFailure()
    else scheduleReconnect(2000)
  }
  socket.onerror = () => { /* onclose follows */ }
}

function onSocketFailure() {
  wsFailures += 1
  // After two failed attempts assume a proxy blocks WebSockets: poll, and retry the socket now and then
  if (wsFailures >= 2) startPolling()
  scheduleReconnect(wsFailures >= 2 ? 60000 : 3000)
}

function scheduleReconnect(ms: number) {
  if (retryTimer) clearTimeout(retryTimer)
  retryTimer = setTimeout(openSocket, ms)
}

function announceConnected() {
  // resumed: this tab was connected before, so it may have missed events and should reload what it shows
  emit({ type: 'realtime.connected', resumed: everConnected })
  everConnected = true
}

async function catchUp() {
  catchingUp = true
  try {
    const { data } = await api.get('/api/v1/realtime/poll', { params: { after: lastSeq, boot: serverBoot } })
    if (data.reset) lastSeq = data.seq
    else data.events.forEach(emit)
  } catch { /* ignore */ } finally {
    catchingUp = false
    heldBack.splice(0).sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0)).forEach(emit)
  }
}

function startPolling() {
  if (realtimeStatus.value === 'polling') return
  realtimeStatus.value = 'polling'
  flush()
  let reachable = false
  const tick = async () => {
    if (realtimeStatus.value !== 'polling' || stopped) return
    try {
      const { data } = await api.get('/api/v1/realtime/poll', { params: { after: lastSeq, boot: serverBoot } })
      if (data.boot) serverBoot = data.boot
      if (lastSeq === 0 || data.reset) {
        // First answer, or the server restarted: start again from now
        lastSeq = data.seq
      } else data.events.forEach(emit)
      // The server answers (again): pages refresh what they show
      if (!reachable || data.reset) announceConnected()
      reachable = true
    } catch {
      reachable = false
    }
    pollTimer = setTimeout(tick, POLL_MS)
  }
  tick()
}

function stopPolling() {
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = null
}

// An iPad waking up or the network coming back: reconnect now instead of waiting for the next retry
function reconnectSoon() {
  if (stopped || document.visibilityState === 'hidden') return
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return
  if (retryTimer) clearTimeout(retryTimer)
  wsFailures = Math.min(wsFailures, 1)
  openSocket()
}
let wakeListeners = false

export function startRealtime(authToken: string) {
  if (!stopped && token === authToken) return
  stopRealtime()
  token = authToken
  stopped = false
  wsFailures = 0
  if (!wakeListeners) {
    wakeListeners = true
    window.addEventListener('online', reconnectSoon)
    document.addEventListener('visibilitychange', reconnectSoon)
  }
  openSocket()
}

export function stopRealtime() {
  stopped = true
  stopPolling()
  if (retryTimer) clearTimeout(retryTimer)
  ws?.close()
  ws = null
  lastSeq = 0
  serverBoot = ''
  everConnected = false
  catchingUp = false
  heldBack.length = 0
  sticky.clear()
  outbox.length = 0
  realtimeStatus.value = 'offline'
}
