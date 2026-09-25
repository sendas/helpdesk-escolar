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
      // Catch up on anything missed while reconnecting/polling
      if (lastSeq > 0) catchUp()
      else lastSeq = event.seq
      realtimeStatus.value = 'live'
      flush()
      emit({ type: 'realtime.connected' })
      return
    }
    if (event.type !== 'ping') emit(event)
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

async function catchUp() {
  try {
    const { data } = await api.get('/api/v1/realtime/poll', { params: { after: lastSeq } })
    data.events.forEach(emit)
  } catch { /* ignore */ }
}

function startPolling() {
  if (realtimeStatus.value === 'polling') return
  realtimeStatus.value = 'polling'
  flush()
  const tick = async () => {
    if (realtimeStatus.value !== 'polling' || stopped) return
    try {
      const { data } = await api.get('/api/v1/realtime/poll', { params: { after: lastSeq } })
      if (lastSeq === 0) lastSeq = data.seq
      else data.events.forEach(emit)
    } catch { /* ignore */ }
    pollTimer = setTimeout(tick, POLL_MS)
  }
  tick()
  emit({ type: 'realtime.connected' })
}

function stopPolling() {
  if (pollTimer) clearTimeout(pollTimer)
  pollTimer = null
}

export function startRealtime(authToken: string) {
  if (!stopped && token === authToken) return
  stopRealtime()
  token = authToken
  stopped = false
  wsFailures = 0
  openSocket()
}

export function stopRealtime() {
  stopped = true
  stopPolling()
  if (retryTimer) clearTimeout(retryTimer)
  ws?.close()
  ws = null
  lastSeq = 0
  sticky.clear()
  outbox.length = 0
  realtimeStatus.value = 'offline'
}
