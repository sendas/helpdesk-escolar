<template>
  <div class="chat-page">
    <aside class="chat-side" :class="{ 'is-hidden': mobileShowConversation }">
      <div class="chat-tabs">
        <button v-if="canTeam" class="chat-tab" :class="{ active: tab === 'equipa' }" @click="setTab('equipa')">
          <span class="material-icons">forum</span> Equipa
          <span v-if="teamUnread" class="chat-badge">{{ teamUnread }}</span>
        </button>
        <button v-if="canSupport" class="chat-tab" :class="{ active: tab === 'apoio' }" @click="setTab('apoio')">
          <span class="material-icons">support_agent</span> Apoio ao vivo
          <span v-if="waitingCount" class="chat-badge warn">{{ waitingCount }}</span>
        </button>
      </div>

      <template v-if="tab === 'equipa'">
        <div class="chat-side-actions">
          <button class="hd-btn hd-btn-primary" @click="openPeople('direct')"><span class="material-icons">edit</span> Nova conversa</button>
          <button class="hd-btn hd-btn-outline" @click="openPeople('group')"><span class="material-icons">group_add</span> Grupo</button>
        </div>
        <div class="chat-list">
          <button v-for="c in teamConversations" :key="c.id" class="chat-item" :class="{ active: current?.id === c.id }" @click="select(c.id)">
            <span class="chat-avatar" :class="c.kind">
              <span v-if="c.kind === 'group'" class="material-icons">{{ c.role_key ? 'workspaces' : 'groups' }}</span>
              <template v-else>{{ initials(c.title) }}</template>
              <i v-if="c.kind === 'direct' && isOnline(c)" class="chat-online"></i>
            </span>
            <span class="chat-item-text">
              <strong>{{ c.kind === 'direct' ? shortName(c.title) : c.title }}</strong>
              <small>{{ preview(c) }}</small>
            </span>
            <span class="chat-item-meta">
              <time>{{ shortTime(c.last_message?.created_at || c.updated_at) }}</time>
              <span v-if="c.unread" class="chat-badge">{{ c.unread }}</span>
            </span>
          </button>
          <div v-if="!teamConversations.length" class="chat-empty-list">Ainda sem conversas. Comece uma nova conversa.</div>
        </div>
      </template>

      <template v-else>
        <label class="avail" :class="{ on: available }">
          <span class="hd-toggle-wrap" @click.prevent="toggleAvailability">
            <span class="hd-toggle-track" :class="{ on: available }"><span class="hd-toggle-thumb"></span></span>
          </span>
          <span>
            <strong>{{ available ? 'Disponível para apoio' : 'Indisponível' }}</strong>
            <small>{{ supportInfo?.open_now ? 'Em horário de apoio' : 'Fora do horário de apoio' }} · {{ supportInfo?.hours_text }}</small>
          </span>
        </label>
        <div class="chat-list">
          <div v-if="waiting.length" class="chat-list-title">À espera ({{ waiting.length }})</div>
          <button v-for="c in waiting" :key="c.id" class="chat-item waiting" :class="{ active: current?.id === c.id }" @click="select(c.id)">
            <span class="chat-avatar support">{{ initials(c.title) }}</span>
            <span class="chat-item-text">
              <strong>{{ shortName(c.title) }}</strong>
              <small>{{ c.last_message?.is_system ? firstMessage(c) : preview(c) }}</small>
            </span>
            <span class="chat-item-meta"><time>há {{ minutesAgo(c.created_at) }} min</time></span>
          </button>
          <div v-if="active.length" class="chat-list-title">Em curso</div>
          <button v-for="c in active" :key="c.id" class="chat-item" :class="{ active: current?.id === c.id }" @click="select(c.id)">
            <span class="chat-avatar support">{{ initials(c.title) }}</span>
            <span class="chat-item-text">
              <strong>{{ shortName(c.title) }}</strong>
              <small>{{ agentName(c) }}</small>
            </span>
            <span class="chat-item-meta"><span v-if="c.unread" class="chat-badge">{{ c.unread }}</span></span>
          </button>
          <div v-if="recentSupport.length" class="chat-list-title">Recentes</div>
          <button v-for="c in recentSupport" :key="c.id" class="chat-item done" :class="{ active: current?.id === c.id }" @click="select(c.id)">
            <span class="chat-avatar support">{{ initials(c.title) }}</span>
            <span class="chat-item-text">
              <strong>{{ shortName(c.title) }}</strong>
              <small>{{ c.support_status === 'converted' ? `Ticket T-${c.ticket_id}` : 'Terminada' }}</small>
            </span>
          </button>
          <div v-if="!waiting.length && !active.length && !recentSupport.length" class="chat-empty-list">Sem pedidos de apoio neste momento.</div>
        </div>
      </template>
    </aside>

    <section class="chat-main" :class="{ 'is-hidden': !mobileShowConversation }">
      <template v-if="current">
        <header class="chat-head">
          <button class="hd-icon-btn chat-back" @click="mobileShowConversation = false"><span class="material-icons">arrow_back</span></button>
          <div class="chat-head-text">
            <strong>{{ current.kind === 'direct' || current.kind === 'support' ? shortName(current.title) : current.title }}</strong>
            <small v-if="current.kind === 'group'">{{ current.members.length }} membros · {{ current.members.map(m => shortName(m.display_name)).join(', ') }}</small>
            <small v-else-if="current.kind === 'support'">{{ supportLabel(current) }}</small>
            <small v-else>{{ current.members.find(m => m.id !== auth.user?.id)?.role_label }}</small>
          </div>
          <template v-if="current.kind === 'support' && canSupport">
            <button v-if="current.support_status === 'waiting'" class="hd-btn hd-btn-primary" @click="accept">Aceitar</button>
            <template v-if="['waiting', 'active'].includes(current.support_status ?? '')">
              <button class="hd-btn hd-btn-outline" @click="convert"><span class="material-icons">confirmation_number</span> Converter em ticket</button>
              <button class="hd-btn hd-btn-outline" @click="endSupport">Terminar</button>
            </template>
            <router-link v-if="current.ticket_id" class="hd-btn hd-btn-outline" :to="`/tickets/${current.ticket_id}`">Abrir T-{{ current.ticket_id }}</router-link>
          </template>
        </header>

        <div ref="scroller" class="chat-messages">
          <button v-if="hasMore" class="chat-more" @click="loadOlder">Mensagens anteriores</button>
          <template v-for="(m, i) in messages" :key="m.id">
            <div v-if="dayChanged(i)" class="chat-day">{{ dayLabel(m.created_at) }}</div>
            <div v-if="m.is_system" class="chat-system">{{ m.body }}</div>
            <div v-else class="chat-msg" :class="{ me: m.author?.id === auth.user?.id, cont: sameAuthor(i) }">
              <span v-if="m.author?.id !== auth.user?.id && !sameAuthor(i)" class="chat-msg-author">{{ shortName(m.author?.display_name) }}</span>
              <div class="chat-bubble" v-html="renderBody(m.body)"></div>
              <time>{{ timeOf(m.created_at) }}<template v-if="m.author?.id === auth.user?.id && m.id === lastMineId && seenByOthers"> · visto</template></time>
            </div>
          </template>
          <div v-if="typingNames.length" class="chat-typing">{{ typingNames.join(', ') }} {{ typingNames.length > 1 ? 'estão' : 'está' }} a escrever…</div>
        </div>

        <footer v-if="canWrite" class="chat-compose">
          <textarea v-model="draft" rows="1" placeholder="Escreva uma mensagem… (use T-123 para referir um ticket)" @keydown.enter.exact.prevent="send" @input="onTyping"></textarea>
          <button class="chat-send" :disabled="!draft.trim() || sending" title="Enviar (Enter)" @click="send"><span class="material-icons">send</span></button>
        </footer>
        <footer v-else class="chat-compose closed">Esta conversa terminou.</footer>
      </template>
      <div v-else class="chat-placeholder">
        <span class="material-icons">{{ tab === 'apoio' ? 'support_agent' : 'forum' }}</span>
        <p>{{ tab === 'apoio' ? 'Escolha um pedido de apoio à esquerda.' : 'Escolha uma conversa ou comece uma nova.' }}</p>
      </div>
    </section>

    <!-- New conversation / group -->
    <div v-if="peopleDialog" class="chat-dialog-backdrop" @click.self="peopleDialog = ''">
      <div class="chat-dialog">
        <div class="chat-dialog-head">
          <strong>{{ peopleDialog === 'group' ? 'Novo grupo' : 'Nova conversa' }}</strong>
          <button class="hd-icon-btn" @click="peopleDialog = ''"><span class="material-icons">close</span></button>
        </div>
        <input v-if="peopleDialog === 'group'" v-model="groupTitle" class="hd-input" placeholder="Nome do grupo" />
        <input v-model="peopleSearch" class="hd-input" placeholder="Procurar pessoa…" />
        <div class="chat-people">
          <label v-for="p in filteredPeople" :key="p.id" class="chat-person" @click="peopleDialog === 'direct' && startDirect(p.id)">
            <input v-if="peopleDialog === 'group'" v-model="groupMembers" type="checkbox" :value="p.id" />
            <span class="chat-avatar">{{ initials(p.display_name) }}<i v-if="p.online" class="chat-online"></i></span>
            <span><strong>{{ shortName(p.display_name) }}</strong><small>{{ p.role_label }}</small></span>
          </label>
          <div v-if="!filteredPeople.length" class="chat-empty-list">Ninguém encontrado.</div>
        </div>
        <div v-if="peopleDialog === 'group'" class="chat-dialog-actions">
          <button class="hd-btn hd-btn-primary" :disabled="!groupTitle.trim() || !groupMembers.length" @click="startGroup">Criar grupo</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  acceptSupport, closeSupport, convertSupport, createGroup, getChatPeople, getConversations, getMessages, getSupportQueue,
  getSupportStatus, markRead, openDirect, sendChatMessage, setSupportAvailability,
  type ChatConversation, type ChatMessage, type ChatUser, type SupportStatus,
} from '../api/chat'
import { onRealtime, sendRealtime } from '../services/realtime'
import { shortName } from '../utils/names'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const canTeam = computed(() => auth.can('chat.team'))
const canSupport = computed(() => auth.can('chat.support'))
const tab = ref<'equipa' | 'apoio'>(route.query.tab === 'apoio' || !canTeam.value ? 'apoio' : 'equipa')

const conversations = ref<ChatConversation[]>([])
const queue = ref<ChatConversation[]>([])
const current = ref<ChatConversation | null>(null)
const messages = ref<ChatMessage[]>([])
const hasMore = ref(false)
const draft = ref('')
const sending = ref(false)
const scroller = ref<HTMLElement | null>(null)
const mobileShowConversation = ref(false)
const supportInfo = ref<SupportStatus | null>(null)
const available = ref(false)
const typing = ref<Record<number, { name: string; timer: ReturnType<typeof setTimeout> }>>({})
const readBy = ref<Record<number, string>>({})
const people = ref<ChatUser[]>([])
const peopleDialog = ref<'' | 'direct' | 'group'>('')
const peopleSearch = ref('')
const groupTitle = ref('')
const groupMembers = ref<number[]>([])
let lastTypingSent = 0

const teamConversations = computed(() => conversations.value.filter((c) => c.kind !== 'support'))
const teamUnread = computed(() => teamConversations.value.reduce((n, c) => n + c.unread, 0))
const waiting = computed(() => queue.value.filter((c) => c.support_status === 'waiting'))
const active = computed(() => queue.value.filter((c) => c.support_status === 'active'))
const waitingCount = computed(() => waiting.value.length)
const recentSupport = computed(() => conversations.value.filter((c) => c.kind === 'support' && !['waiting', 'active'].includes(c.support_status ?? '')).slice(0, 10))
const canWrite = computed(() => current.value && (current.value.kind !== 'support' || ['waiting', 'active'].includes(current.value.support_status ?? '')))
const typingNames = computed(() => Object.values(typing.value).map((t) => t.name))
const lastMineId = computed(() => [...messages.value].reverse().find((m) => m.author?.id === auth.user?.id)?.id)
const seenByOthers = computed(() => {
  const mine = messages.value.find((m) => m.id === lastMineId.value)
  if (!mine) return false
  return Object.entries(readBy.value).some(([uid, at]) => Number(uid) !== auth.user?.id && at >= mine.created_at)
})
const filteredPeople = computed(() => {
  const q = peopleSearch.value.trim().toLowerCase()
  return people.value.filter((p) => !q || p.display_name.toLowerCase().includes(q))
})

function initials(name?: string | null) {
  return shortName(name).split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase() || '?'
}
function preview(c: ChatConversation) {
  const m = c.last_message
  if (!m) return 'Sem mensagens'
  if (m.is_system) return m.body
  const who = m.author?.id === auth.user?.id ? 'Você' : shortName(m.author?.display_name).split(' ')[0]
  return `${who}: ${m.body}`
}
function firstMessage(c: ChatConversation) { return preview(c) }
function shortTime(iso?: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  const today = new Date()
  return d.toDateString() === today.toDateString()
    ? d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' })
}
function timeOf(iso: string) { return new Date(iso).toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' }) }
function minutesAgo(iso: string) { return Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000)) }
function dayLabel(iso: string) {
  const d = new Date(iso)
  const today = new Date()
  const yesterday = new Date(); yesterday.setDate(today.getDate() - 1)
  if (d.toDateString() === today.toDateString()) return 'Hoje'
  if (d.toDateString() === yesterday.toDateString()) return 'Ontem'
  return d.toLocaleDateString('pt-PT', { weekday: 'long', day: 'numeric', month: 'long' })
}
function dayChanged(i: number) {
  return i === 0 || new Date(messages.value[i - 1].created_at).toDateString() !== new Date(messages.value[i].created_at).toDateString()
}
function sameAuthor(i: number) {
  const prev = messages.value[i - 1]
  const m = messages.value[i]
  return !!prev && !prev.is_system && prev.author?.id === m.author?.id && new Date(m.created_at).getTime() - new Date(prev.created_at).getTime() < 5 * 60000
}
function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]!))
}
// Plain text, with ticket references (T-123 / #123) turned into links
function renderBody(body: string) {
  return escapeHtml(body)
    .replace(/(^|[\s(])#?T-(\d+)\b/gi, (_m, pre, id) => `${pre}<a href="/tickets/${id}" class="chat-ticket-link">T-${id}</a>`)
    .replace(/\n/g, '<br>')
}
function isOnline(c: ChatConversation) {
  const other = c.members.find((m) => m.id !== auth.user?.id)
  return !!other && people.value.some((p) => p.id === other.id && p.online)
}
function agentName(c: ChatConversation) {
  const agent = c.members.find((m) => m.id === c.agent_id)
  return agent ? `Com ${shortName(agent.display_name)}` : 'Em curso'
}
function supportLabel(c: ChatConversation) {
  return {
    waiting: `À espera há ${minutesAgo(c.created_at)} min`,
    active: agentName(c),
    closed: 'Conversa terminada',
    converted: `Convertida no ticket T-${c.ticket_id}`,
  }[c.support_status ?? 'active']
}

async function scrollDown() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

async function loadLists() {
  const [convs, q] = await Promise.all([
    getConversations(),
    canSupport.value ? getSupportQueue() : Promise.resolve([]),
  ])
  conversations.value = convs
  queue.value = q
  if (current.value) {
    const fresh = [...convs, ...q].find((c) => c.id === current.value!.id)
    if (fresh) current.value = { ...fresh, unread: 0 }
  }
}

async function select(id: number) {
  const data = await getMessages(id)
  current.value = data.conversation
  messages.value = data.messages
  hasMore.value = data.messages.length >= 50
  readBy.value = {}
  typing.value = {}
  mobileShowConversation.value = true
  router.replace({ query: { ...route.query, c: String(id) } })
  markRead(id).catch(() => {})
  const inList = conversations.value.find((c) => c.id === id)
  if (inList) inList.unread = 0
  scrollDown()
}

async function loadOlder() {
  if (!current.value || !messages.value.length) return
  const data = await getMessages(current.value.id, messages.value[0].id)
  messages.value = [...data.messages, ...messages.value]
  hasMore.value = data.messages.length >= 50
}

async function send() {
  const body = draft.value.trim()
  if (!body || !current.value || sending.value) return
  sending.value = true
  try {
    const msg = await sendChatMessage(current.value.id, body)
    if (!messages.value.some((m) => m.id === msg.id)) messages.value.push(msg)
    draft.value = ''
    scrollDown()
    loadLists()
  } finally {
    sending.value = false
  }
}

function onTyping() {
  if (!current.value) return
  const now = Date.now()
  if (now - lastTypingSent < 3000) return
  lastTypingSent = now
  sendRealtime({ type: 'chat.typing', conversation_id: current.value.id })
}

function setTab(t: 'equipa' | 'apoio') {
  tab.value = t
  current.value = null
  router.replace({ query: { tab: t === 'apoio' ? 'apoio' : undefined } })
}

async function openPeople(kind: 'direct' | 'group') {
  peopleDialog.value = kind
  peopleSearch.value = ''
  groupTitle.value = ''
  groupMembers.value = []
  people.value = await getChatPeople()
}
async function startDirect(userId: number) {
  const conv = await openDirect(userId)
  peopleDialog.value = ''
  await loadLists()
  select(conv.id)
}
async function startGroup() {
  const conv = await createGroup(groupTitle.value.trim(), groupMembers.value)
  peopleDialog.value = ''
  await loadLists()
  select(conv.id)
}

async function toggleAvailability() {
  available.value = await setSupportAvailability(!available.value)
}
async function accept() {
  if (!current.value) return
  try {
    await acceptSupport(current.value.id)
  } catch (e: any) {
    alert(e?.response?.data?.detail || 'Não foi possível aceitar.')
  }
  await loadLists()
  select(current.value.id)
}
async function convert() {
  if (!current.value || !confirm('Converter esta conversa num ticket? A conversa é copiada para o ticket.')) return
  const ticketId = await convertSupport(current.value.id)
  await loadLists()
  await select(current.value.id)
  if (ticketId && confirm(`Criado o ticket T-${ticketId}. Abrir agora?`)) router.push(`/tickets/${ticketId}`)
}
async function endSupport() {
  if (!current.value || !confirm('Terminar esta conversa de apoio?')) return
  await closeSupport(current.value.id)
  await loadLists()
  select(current.value.id)
}

const offs: Array<() => void> = []
onMounted(async () => {
  await loadLists()
  if (canSupport.value) {
    getSupportStatus().then((s) => { supportInfo.value = s; available.value = !!s.available }).catch(() => {})
  }
  if (canTeam.value) getChatPeople().then((p) => { people.value = p }).catch(() => {})
  const c = Number(route.query.c)
  if (c) {
    const conv = [...conversations.value, ...queue.value].find((x) => x.id === c)
    if (conv?.kind === 'support') tab.value = 'apoio'
    select(c).catch(() => {})
  }
  offs.push(onRealtime('chat.message', (e) => {
    if (current.value && e.conversation_id === current.value.id) {
      if (!messages.value.some((m) => m.id === e.message.id)) messages.value.push(e.message)
      if (e.message.author) delete typing.value[e.message.author.id]
      markRead(e.conversation_id).catch(() => {})
      scrollDown()
      if (e.message.is_system) loadLists()
    }
    loadLists()
  }))
  offs.push(onRealtime('chat.typing', (e) => {
    if (!current.value || e.conversation_id !== current.value.id) return
    const prev = typing.value[e.user.id]
    if (prev) clearTimeout(prev.timer)
    typing.value[e.user.id] = { name: shortName(e.user.name), timer: setTimeout(() => { delete typing.value[e.user.id] }, 5000) }
  }))
  offs.push(onRealtime('chat.read', (e) => {
    if (current.value && e.conversation_id === current.value.id) readBy.value[e.user_id] = e.at
  }))
  offs.push(onRealtime('chat.conversation', () => loadLists()))
  offs.push(onRealtime('support.queue', () => loadLists()))
  offs.push(onRealtime('realtime.connected', () => loadLists()))
})
onBeforeUnmount(() => offs.forEach((off) => off()))
watch(() => route.query.c, (c) => { if (c && Number(c) !== current.value?.id) select(Number(c)).catch(() => {}) })
</script>

<style scoped>
.chat-page { display: grid; grid-template-columns: 320px 1fr; height: calc(100vh - 110px); min-height: 480px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 16px; overflow: hidden; }
.chat-side { border-right: 1px solid var(--c-border); display: flex; flex-direction: column; min-height: 0; }
.chat-tabs { display: flex; gap: 4px; padding: 10px; border-bottom: 1px solid var(--c-border); }
.chat-tab { flex: 1; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 8px; border: 0; border-radius: 10px; background: transparent; color: var(--c-muted); font-weight: 700; font-size: 13px; cursor: pointer; }
.chat-tab .material-icons { font-size: 17px; }
.chat-tab.active { background: var(--c-primary-soft); color: var(--c-primary); }
.chat-badge { min-width: 18px; height: 18px; border-radius: 9px; background: var(--c-primary); color: #fff; font-size: 11px; font-weight: 700; display: inline-grid; place-items: center; padding: 0 5px; }
.chat-badge.warn { background: #F59E0B; }
.chat-side-actions { display: flex; gap: 6px; padding: 10px; }
.chat-side-actions .hd-btn { flex: 1; font-size: 12.5px; padding: 7px 8px; justify-content: center; }
.chat-side-actions .material-icons { font-size: 16px; }
.chat-list { flex: 1; overflow-y: auto; padding: 4px 8px 10px; }
.chat-list-title { font-size: 11px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: var(--c-muted); padding: 10px 8px 4px; }
.chat-item { width: 100%; display: flex; align-items: center; gap: 10px; padding: 9px 8px; border: 0; border-radius: 12px; background: transparent; cursor: pointer; text-align: left; color: var(--c-text); }
.chat-item:hover { background: var(--c-bg); }
.chat-item.active { background: var(--c-primary-soft); }
.chat-item.waiting { background: rgba(245, 158, 11, .1); }
.chat-item.done { opacity: .7; }
.chat-avatar { position: relative; width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0; display: grid; place-items: center; font-size: 13px; font-weight: 800; color: #fff; background: linear-gradient(135deg, #2563EB, #0891B2); }
.chat-avatar.group { border-radius: 12px; background: linear-gradient(135deg, #4057D8, #7C3AED); }
.chat-avatar.support { background: linear-gradient(135deg, #F59E0B, #EA580C); }
.chat-avatar .material-icons { font-size: 19px; }
.chat-online { position: absolute; right: -1px; bottom: -1px; width: 11px; height: 11px; border-radius: 50%; background: #22C55E; border: 2px solid var(--c-surface); }
.chat-item-text { flex: 1; min-width: 0; }
.chat-item-text strong { display: block; font-size: 13.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chat-item-text small { display: block; font-size: 12px; color: var(--c-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chat-item-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; font-size: 11px; color: var(--c-muted); }
.chat-empty-list { padding: 24px 12px; text-align: center; font-size: 13px; color: var(--c-muted); }
.avail { display: flex; gap: 10px; align-items: center; margin: 10px; padding: 10px 12px; border: 1px solid var(--c-border); border-radius: 12px; cursor: pointer; }
.avail.on { border-color: #22C55E; background: rgba(34, 197, 94, .08); }
.avail strong { display: block; font-size: 13px; }
.avail small { display: block; font-size: 11.5px; color: var(--c-muted); }
.chat-main { display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.chat-head { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-bottom: 1px solid var(--c-border); flex-wrap: wrap; }
.chat-head .hd-btn { font-size: 12.5px; padding: 6px 12px; }
.chat-head .hd-btn .material-icons { font-size: 16px; }
.chat-head-text { flex: 1; min-width: 160px; }
.chat-head-text strong { display: block; font-size: 15px; }
.chat-head-text small { display: block; font-size: 12px; color: var(--c-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chat-back { display: none; }
.chat-messages { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 4px; background: var(--c-bg); }
.chat-more { align-self: center; border: 1px solid var(--c-border); background: var(--c-surface); border-radius: 999px; padding: 4px 12px; font-size: 12px; cursor: pointer; color: var(--c-muted); margin-bottom: 8px; }
.chat-day { align-self: center; font-size: 11.5px; font-weight: 700; color: var(--c-muted); background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 999px; padding: 2px 10px; margin: 10px 0 6px; text-transform: capitalize; }
.chat-system { align-self: center; font-size: 12px; color: var(--c-muted); text-align: center; margin: 6px 0; max-width: 80%; }
.chat-msg { display: flex; flex-direction: column; align-items: flex-start; max-width: 72%; margin-top: 8px; }
.chat-msg.cont { margin-top: 1px; }
.chat-msg.me { align-self: flex-end; align-items: flex-end; }
.chat-msg-author { font-size: 11.5px; font-weight: 700; color: var(--c-muted); margin: 0 0 2px 6px; }
.chat-bubble { padding: 8px 12px; border-radius: 16px 16px 16px 4px; background: var(--c-surface); border: 1px solid var(--c-border); font-size: 14px; line-height: 1.45; word-break: break-word; }
.chat-msg.me .chat-bubble { background: var(--c-primary); color: #fff; border-color: transparent; border-radius: 16px 16px 4px 16px; }
.chat-msg time { font-size: 10.5px; color: var(--c-muted); margin: 2px 6px 0; }
:deep(.chat-ticket-link) { font-weight: 700; color: inherit; text-decoration: underline; }
.chat-typing { font-size: 12px; font-style: italic; color: var(--c-muted); margin-top: 6px; }
.chat-compose { display: flex; gap: 8px; align-items: flex-end; padding: 12px 16px; border-top: 1px solid var(--c-border); }
.chat-compose.closed { justify-content: center; font-size: 13px; color: var(--c-muted); }
.chat-compose textarea { flex: 1; resize: none; max-height: 140px; border: 1px solid var(--c-border); border-radius: 14px; padding: 10px 14px; font: inherit; font-size: 14px; background: var(--c-bg); color: var(--c-text); outline: none; field-sizing: content; }
.chat-compose textarea:focus { border-color: var(--c-primary); }
.chat-send { width: 42px; height: 42px; border: 0; border-radius: 14px; background: var(--c-primary); color: #fff; display: grid; place-items: center; cursor: pointer; }
.chat-send:disabled { opacity: .45; cursor: default; }
.chat-placeholder { flex: 1; display: grid; place-content: center; text-align: center; color: var(--c-muted); gap: 6px; }
.chat-placeholder .material-icons { font-size: 48px; opacity: .5; }
.chat-dialog-backdrop { position: fixed; inset: 0; background: rgba(15, 23, 42, .45); display: grid; place-items: center; z-index: 4000; padding: 16px; }
.chat-dialog { width: min(420px, 100%); max-height: 80vh; display: flex; flex-direction: column; gap: 10px; background: var(--c-surface); border-radius: 16px; padding: 16px; }
.chat-dialog-head { display: flex; justify-content: space-between; align-items: center; }
.chat-people { overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.chat-person { display: flex; align-items: center; gap: 10px; padding: 8px; border-radius: 10px; cursor: pointer; }
.chat-person:hover { background: var(--c-bg); }
.chat-person strong { display: block; font-size: 13.5px; }
.chat-person small { display: block; font-size: 12px; color: var(--c-muted); }
.chat-dialog-actions { display: flex; justify-content: flex-end; }
@media (max-width: 800px) {
  .chat-page { grid-template-columns: 1fr; height: calc(100vh - 90px); }
  .chat-side.is-hidden, .chat-main.is-hidden { display: none; }
  .chat-back { display: inline-flex; }
  .chat-msg { max-width: 88%; }
}
</style>
