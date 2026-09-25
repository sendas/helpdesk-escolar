<template>
  <div class="sw" :class="{ open }">
    <transition name="sw-pop">
      <section v-if="open" class="sw-panel" role="dialog" aria-label="Apoio ao vivo">
        <header class="sw-head">
          <div class="sw-head-icon"><span class="material-icons">support_agent</span></div>
          <div class="sw-head-text">
            <strong>Apoio ao vivo</strong>
            <small>
              <span class="sw-dot" :class="{ on: status?.open_now }"></span>
              {{ status?.open_now ? (status.agents_online ? 'Equipa TIC disponível' : 'Em horário de apoio') : 'Fechado neste momento' }}
            </small>
          </div>
          <button class="sw-icon-btn" title="Fechar" @click="open = false"><span class="material-icons">close</span></button>
        </header>

        <div ref="scroller" class="sw-body">
          <template v-if="!conversation || finished && startingNew">
            <div class="sw-intro">
              <p v-if="status?.open_now">Escreva o seu problema e um técnico responde-lhe aqui, em tempo real.</p>
              <p v-else>O apoio ao vivo está fechado. Pode deixar a mensagem na mesma: <strong>criamos um ticket</strong> e respondemos por lá.</p>
              <div class="sw-hours">
                <span class="material-icons">schedule</span>
                <div>
                  <div v-for="d in hoursList" :key="d.day" :class="{ today: d.today }">{{ d.label }}: {{ d.text }}</div>
                </div>
              </div>
            </div>
          </template>
          <template v-else>
            <div v-for="m in messages" :key="m.id" class="sw-msg" :class="{ me: m.author?.id === auth.user?.id, system: m.is_system }">
              <template v-if="m.is_system">
                <span>{{ m.body }}</span>
                <router-link v-if="conversation?.ticket_id && m.body.includes('T-' + conversation.ticket_id)" :to="`/tickets/${conversation.ticket_id}`" @click="open = false">Abrir ticket</router-link>
              </template>
              <template v-else>
                <small v-if="m.author?.id !== auth.user?.id">{{ shortName(m.author?.display_name) }}</small>
                <div class="sw-bubble">{{ m.body }}</div>
                <time>{{ timeOf(m.created_at) }}</time>
              </template>
            </div>
            <div v-if="typingName" class="sw-typing">{{ typingName }} está a escrever…</div>
            <div v-if="conversation.support_status === 'waiting'" class="sw-waiting">
              <span class="sw-spinner"></span>
              À espera de um técnico. Se ninguém responder em {{ status?.wait_minutes ?? 5 }} minutos, criamos um ticket automaticamente.
            </div>
          </template>
        </div>

        <footer class="sw-foot">
          <template v-if="!conversation || (finished && startingNew)">
            <select v-model="schoolId" class="hd-input sw-school">
              <option :value="null">Escola…</option>
              <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </template>
          <template v-if="!finished || startingNew">
            <div class="sw-compose">
              <textarea v-model="draft" rows="2" :placeholder="status?.open_now || conversation ? 'Escreva a sua mensagem…' : 'Descreva o problema…'" @keydown.enter.exact.prevent="send" @input="typing"></textarea>
              <button class="sw-send" :disabled="!draft.trim() || sending" :title="sendLabel" @click="send">
                <span class="material-icons">send</span>
              </button>
            </div>
            <div class="sw-foot-row">
              <span class="sw-hint">{{ sendLabel }} · Enter para enviar</span>
              <button v-if="conversation && !finished" class="sw-link" @click="endConversation">Terminar conversa</button>
            </div>
          </template>
          <div v-else class="sw-foot-row">
            <span class="sw-hint">{{ conversation?.support_status === 'converted' ? 'Esta conversa passou a ticket.' : 'Conversa terminada.' }}</span>
            <button class="hd-btn hd-btn-primary sw-new" @click="startingNew = true">Nova conversa</button>
          </div>
          <div v-if="error" class="sw-error">{{ error }}</div>
        </footer>
      </section>
    </transition>

    <transition name="sw-pop">
      <div v-if="showIntro && !open" class="sw-intro-tip">
        <button class="sw-tip-close" title="Fechar" @click="dismissIntro"><span class="material-icons">close</span></button>
        <strong>Novo: apoio ao vivo 👋</strong>
        <span>Tem um problema rápido? Fale aqui com a equipa TIC em tempo real{{ status?.open_now ? '' : ' (ou deixe a mensagem e criamos um ticket)' }}.</span>
        <button class="sw-tip-btn" @click="dismissIntro(); toggle()">Experimentar</button>
      </div>
    </transition>
    <button class="sw-launcher" :title="open ? 'Fechar apoio ao vivo' : 'Apoio ao vivo'" @click="toggle">
      <span class="material-icons">{{ open ? 'expand_more' : 'forum' }}</span>
      <span v-if="!open" class="sw-launcher-label">Apoio ao vivo</span>
      <span v-if="status?.open_now && !open" class="sw-launcher-dot"></span>
      <span v-if="unread && !open" class="sw-launcher-badge">{{ unread }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { closeSupport, getMySupport, getSupportStatus, markRead, startSupport, sendChatMessage, type ChatConversation, type ChatMessage, type SupportStatus } from '../api/chat'
import { getSchools } from '../api/tickets'
import { onRealtime, sendRealtime } from '../services/realtime'
import { shortName } from '../utils/names'
import { onOpenSupportChat } from '../utils/supportChat'

const auth = useAuthStore()
const open = ref(false)
const status = ref<SupportStatus | null>(null)
const conversation = ref<ChatConversation | null>(null)
const messages = ref<ChatMessage[]>([])
const schools = ref<any[]>([])
const schoolId = ref<number | null>(null)
const draft = ref('')
const sending = ref(false)
const error = ref('')
const unread = ref(0)
const startingNew = ref(false)
const typingName = ref('')
const scroller = ref<HTMLElement | null>(null)
let typingTimer: ReturnType<typeof setTimeout> | null = null
let lastTypingSent = 0

const finished = computed(() => !!conversation.value && ['closed', 'converted'].includes(conversation.value.support_status ?? ''))
const sendLabel = computed(() => {
  if (conversation.value && !finished.value) return 'Enviar'
  return status.value?.open_now ? 'Pedir apoio' : 'Criar ticket'
})

const DAY_LABELS: Record<string, string> = { '1': 'Segunda', '2': 'Terça', '3': 'Quarta', '4': 'Quinta', '5': 'Sexta', '6': 'Sábado', '7': 'Domingo' }
const hoursList = computed(() => {
  const today = String(((new Date().getDay() + 6) % 7) + 1)
  return Object.entries(status.value?.hours ?? {})
    .filter(([, d]) => d.enabled)
    .map(([day, d]) => ({ day, label: DAY_LABELS[day], text: `${d.start}–${d.end}`, today: day === today }))
})

function timeOf(iso: string) {
  return new Date(iso).toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
}

async function scrollDown() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

async function load() {
  status.value = await getSupportStatus()
  const mine = await getMySupport()
  conversation.value = mine?.conversation ?? null
  messages.value = mine?.messages ?? []
  unread.value = open.value ? 0 : (mine?.conversation.unread ?? 0)
  scrollDown()
}

async function toggle() {
  open.value = !open.value
  if (open.value) dismissIntro()
  if (open.value) {
    if (!schools.value.length) getSchools().then((s) => { schools.value = s }).catch(() => {})
    await load()
    if (conversation.value) markRead(conversation.value.id).catch(() => {})
    unread.value = 0
  }
}

async function send() {
  const body = draft.value.trim()
  if (!body || sending.value) return
  sending.value = true
  error.value = ''
  try {
    if (conversation.value && !finished.value) {
      await sendChatMessage(conversation.value.id, body)
    } else {
      const res = await startSupport(body, schoolId.value)
      conversation.value = res.conversation
      messages.value = res.messages
      startingNew.value = false
    }
    draft.value = ''
    scrollDown()
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Não foi possível enviar a mensagem.'
  } finally {
    sending.value = false
  }
}

async function endConversation() {
  if (!conversation.value || !confirm('Terminar esta conversa de apoio?')) return
  conversation.value = await closeSupport(conversation.value.id)
  await load()
}

function typing() {
  if (!conversation.value || finished.value) return
  const now = Date.now()
  if (now - lastTypingSent < 3000) return
  lastTypingSent = now
  sendRealtime({ type: 'chat.typing', conversation_id: conversation.value.id })
}

const INTRO_KEY = 'support_intro_seen'
const showIntro = ref(false)
function dismissIntro() {
  showIntro.value = false
  try { localStorage.setItem(INTRO_KEY, '1') } catch { /* ignore */ }
}

const offs: Array<() => void> = []
onMounted(() => {
  try { showIntro.value = !localStorage.getItem(INTRO_KEY) } catch { showIntro.value = false }
  offs.push(onOpenSupportChat(() => { dismissIntro(); if (!open.value) toggle() }))
  getSupportStatus().then((s) => { status.value = s }).catch(() => {})
  getMySupport().then((m) => {
    if (m && ['waiting', 'active'].includes(m.conversation.support_status ?? '')) {
      conversation.value = m.conversation
      messages.value = m.messages
      unread.value = m.conversation.unread
    }
  }).catch(() => {})
  offs.push(onRealtime('chat.message', (e) => {
    if (!conversation.value || e.conversation_id !== conversation.value.id) return
    if (!messages.value.some((m) => m.id === e.message.id)) messages.value.push(e.message)
    if (e.message.is_system) load()
    if (open.value) { markRead(e.conversation_id).catch(() => {}); scrollDown() }
    else if (e.message.author?.id !== auth.user?.id) unread.value += 1
    if (e.message.author) typingName.value = ''
  }))
  offs.push(onRealtime('chat.typing', (e) => {
    if (e.conversation_id !== conversation.value?.id) return
    typingName.value = shortName(e.user.name)
    if (typingTimer) clearTimeout(typingTimer)
    typingTimer = setTimeout(() => { typingName.value = '' }, 5000)
  }))
})
onBeforeUnmount(() => offs.forEach((off) => off()))
</script>

<style scoped>
.sw { position: fixed; right: 20px; bottom: 20px; z-index: 3000; display: flex; flex-direction: column; align-items: flex-end; gap: 12px; }
.sw-launcher {
  position: relative; display: inline-flex; align-items: center; gap: 8px; height: 48px; padding: 0 18px 0 14px;
  border: 0; border-radius: 999px; cursor: pointer; color: #fff; font-weight: 700; font-size: 14px;
  background: linear-gradient(135deg, #2563EB, #0891B2); box-shadow: 0 10px 30px rgba(37, 99, 235, .35);
}
.sw.open .sw-launcher { width: 48px; padding: 0; justify-content: center; }
.sw-launcher .material-icons { font-size: 22px; }
.sw-launcher-dot { position: absolute; top: 6px; left: 32px; width: 10px; height: 10px; border-radius: 50%; background: #22C55E; border: 2px solid #fff; }
.sw-launcher-badge { position: absolute; top: -4px; right: -4px; min-width: 20px; height: 20px; border-radius: 10px; background: #DC2626; color: #fff; font-size: 11px; display: grid; place-items: center; padding: 0 5px; }
.sw-panel {
  width: min(380px, calc(100vw - 32px)); height: min(560px, calc(100vh - 120px)); display: flex; flex-direction: column;
  background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 18px; overflow: hidden;
  box-shadow: 0 24px 60px rgba(15, 23, 42, .25);
}
.sw-head { display: flex; align-items: center; gap: 10px; padding: 14px 14px 14px 16px; color: #fff; background: linear-gradient(135deg, #1E3A8A, #2563EB 55%, #0891B2); }
.sw-head-icon { width: 36px; height: 36px; border-radius: 12px; background: rgba(255, 255, 255, .18); display: grid; place-items: center; }
.sw-head-text { flex: 1; min-width: 0; }
.sw-head-text strong { display: block; font-size: 15px; }
.sw-head-text small { display: flex; align-items: center; gap: 6px; font-size: 12px; opacity: .9; }
.sw-dot { width: 8px; height: 8px; border-radius: 50%; background: #94A3B8; }
.sw-dot.on { background: #4ADE80; }
.sw-icon-btn { border: 0; background: transparent; color: #fff; cursor: pointer; opacity: .85; }
.sw-body { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 10px; background: var(--c-bg); }
.sw-intro p { margin: 0 0 12px; font-size: 13.5px; line-height: 1.5; }
.sw-hours { display: flex; gap: 8px; font-size: 12.5px; color: var(--c-muted); background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 12px; padding: 10px 12px; }
.sw-hours .material-icons { font-size: 17px; color: var(--c-primary); }
.sw-hours .today { color: var(--c-text); font-weight: 700; }
.sw-msg { display: flex; flex-direction: column; align-items: flex-start; max-width: 85%; }
.sw-msg.me { align-self: flex-end; align-items: flex-end; }
.sw-msg small { font-size: 11px; color: var(--c-muted); margin: 0 0 2px 4px; }
.sw-bubble { padding: 8px 12px; border-radius: 14px 14px 14px 4px; background: var(--c-surface); border: 1px solid var(--c-border); font-size: 13.5px; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
.sw-msg.me .sw-bubble { background: #2563EB; color: #fff; border-color: #2563EB; border-radius: 14px 14px 4px 14px; }
.sw-msg time { font-size: 10.5px; color: var(--c-muted); margin: 2px 4px 0; }
.sw-msg.system { align-self: center; align-items: center; max-width: 95%; text-align: center; font-size: 12px; color: var(--c-muted); gap: 4px; }
.sw-msg.system a { font-weight: 700; color: var(--c-primary); }
.sw-typing { font-size: 12px; color: var(--c-muted); font-style: italic; }
.sw-waiting { display: flex; gap: 8px; align-items: flex-start; font-size: 12px; color: var(--c-muted); background: var(--c-surface); border: 1px dashed var(--c-border); border-radius: 12px; padding: 10px; }
.sw-spinner { width: 14px; height: 14px; flex-shrink: 0; border-radius: 50%; border: 2px solid var(--c-border); border-top-color: var(--c-primary); animation: sw-spin 1s linear infinite; margin-top: 1px; }
@keyframes sw-spin { to { transform: rotate(360deg); } }
.sw-foot { padding: 10px 12px 12px; border-top: 1px solid var(--c-border); background: var(--c-surface); display: flex; flex-direction: column; gap: 8px; }
.sw-school { padding: 7px 10px; font-size: 13px; }
.sw-compose { display: flex; gap: 8px; align-items: flex-end; }
.sw-compose textarea { flex: 1; resize: none; border: 1px solid var(--c-border); border-radius: 12px; padding: 9px 12px; font: inherit; font-size: 13.5px; background: var(--c-bg); color: var(--c-text); outline: none; }
.sw-compose textarea:focus { border-color: var(--c-primary); }
.sw-send { width: 40px; height: 40px; border-radius: 12px; border: 0; background: var(--c-primary); color: #fff; cursor: pointer; display: grid; place-items: center; }
.sw-send:disabled { opacity: .45; cursor: default; }
.sw-foot-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.sw-hint { font-size: 11.5px; color: var(--c-muted); }
.sw-link { border: 0; background: transparent; color: #DC2626; font-size: 12px; font-weight: 700; cursor: pointer; }
.sw-new { font-size: 12.5px; padding: 6px 12px; }
.sw-error { color: #DC2626; font-size: 12px; }
.sw-intro-tip { position: relative; width: 260px; padding: 14px 14px 12px; border-radius: 16px; background: var(--c-surface); border: 1px solid var(--c-border); box-shadow: 0 16px 40px rgba(15, 23, 42, .18); font-size: 13px; line-height: 1.45; }
.sw-intro-tip::after { content: ''; position: absolute; right: 28px; bottom: -7px; width: 12px; height: 12px; background: var(--c-surface); border-right: 1px solid var(--c-border); border-bottom: 1px solid var(--c-border); transform: rotate(45deg); }
.sw-intro-tip strong { display: block; font-size: 14px; margin-bottom: 4px; padding-right: 18px; }
.sw-intro-tip span { display: block; color: var(--c-muted); }
.sw-tip-close { position: absolute; top: 8px; right: 8px; border: 0; background: transparent; color: var(--c-muted); cursor: pointer; }
.sw-tip-close .material-icons { font-size: 16px; }
.sw-tip-btn { margin-top: 10px; border: 0; border-radius: 10px; padding: 7px 12px; background: var(--c-primary); color: #fff; font-weight: 700; font-size: 12.5px; cursor: pointer; }
.sw-pop-enter-active, .sw-pop-leave-active { transition: all .18s ease; }
.sw-pop-enter-from, .sw-pop-leave-to { opacity: 0; transform: translateY(12px) scale(.98); }
@media (max-width: 600px) { .sw { right: 12px; bottom: 12px; } .sw-launcher-label { display: none; } .sw-launcher { width: 52px; height: 52px; padding: 0; justify-content: center; } }
</style>
