<template>
  <div class="hd-page ar-page" :class="{ 'has-open': !!current }">
    <!-- List -->
    <section class="ar-list hd-card">
      <div class="ar-tabs" role="tablist">
        <button v-for="t in tabs" :key="t.key" type="button" role="tab" :aria-selected="state === t.key" class="ar-tab" :class="{ active: state === t.key }" @click="setState(t.key)">
          {{ t.label }}<span v-if="t.count !== null" class="ar-count">{{ t.count }}</span>
        </button>
      </div>
      <input v-model="search" class="hd-input ar-search" placeholder="Pesquisar nome, email, n.º de aluno…" @input="onSearch" />
      <button class="ar-import" type="button" :disabled="importing" title="Cria aqui os pedidos que chegaram antes desta secção existir, a partir dos emails de aviso" @click="importPrevious">
        <span class="material-icons">{{ importing ? 'hourglass_empty' : 'move_to_inbox' }}</span>
        {{ importing ? 'A importar…' : 'Importar pedidos anteriores (emails de aviso)' }}
      </button>
      <div v-if="loading" class="ar-empty">A carregar…</div>
      <div v-else-if="!items.length" class="ar-empty">
        <span class="material-icons">mark_email_read</span>
        {{ state === 'open' || state === 'new' ? 'Não há pedidos à espera.' : 'Sem pedidos.' }}
      </div>
      <button v-for="r in items" :key="r.id" type="button" class="ar-item" :class="{ active: current?.id === r.id, unread: r.status === 'new' }" @click="open(r.id)">
        <div class="ar-item-top">
          <strong>{{ r.name }}</strong>
          <span class="ar-when">{{ when(r.updated_at) }}</span>
        </div>
        <div class="ar-item-meta">
          <span class="ar-pill" :class="r.status">{{ STATUS[r.status] }}</span>
          <span>{{ r.profile_label }}<template v-if="r.student_number"> · {{ r.student_number }}</template><template v-if="r.year"> · {{ r.year }} {{ r.class_name }}</template></span>
        </div>
        <div class="ar-item-msg">{{ r.message }}</div>
      </button>
    </section>

    <!-- Request -->
    <section v-if="current" class="ar-detail hd-card">
      <div class="ar-detail-head">
        <button class="hd-icon-btn ar-back" type="button" title="Voltar à lista" @click="close"><span class="material-icons">arrow_back</span></button>
        <div class="ar-detail-title">
          <div class="ar-name">{{ current.name }}</div>
          <div class="ar-sub">Pedido #{{ current.id }} · {{ fullWhen(current.created_at) }} · <span class="ar-pill" :class="current.status">{{ STATUS[current.status] }}</span></div>
        </div>
        <button v-if="current.status !== 'closed'" class="hd-btn hd-btn-outline" type="button" @click="changeStatus('closed')"><span class="material-icons">task_alt</span> Fechar</button>
        <button v-else class="hd-btn hd-btn-outline" type="button" @click="changeStatus('new')"><span class="material-icons">undo</span> Reabrir</button>
      </div>

      <dl class="ar-facts">
        <div><dt>Perfil</dt><dd>{{ current.profile_label }}</dd></div>
        <div v-if="current.student_number"><dt>N.º do cartão</dt><dd>{{ current.student_number }}</dd></div>
        <div v-if="current.year || current.class_name"><dt>Ano / turma</dt><dd>{{ current.year }} {{ current.class_name }}</dd></div>
        <div v-if="current.recruitment_group"><dt>Grupo</dt><dd>{{ current.recruitment_group }}</dd></div>
        <div><dt>Escola</dt><dd>{{ current.school || '—' }}</dd></div>
        <div><dt>Email</dt><dd><a v-if="current.email" :href="`mailto:${current.email}`">{{ current.email }}</a><template v-else>— (não indicou)</template></dd></div>
        <div><dt>Telefone</dt><dd><a v-if="current.phone" :href="`tel:${current.phone}`">{{ current.phone }}</a><template v-else>—</template></dd></div>
      </dl>

      <div class="ar-thread">
        <div class="ar-msg inbound">
          <div class="ar-msg-head"><strong>{{ current.name }}</strong> · {{ fullWhen(current.created_at) }}</div>
          <div class="ar-msg-body">{{ current.message }}</div>
        </div>
        <div v-for="m in current.messages" :key="m.id" class="ar-msg" :class="m.kind">
          <div class="ar-msg-head">
            <span class="material-icons">{{ KIND_ICON[m.kind] }}</span>
            <strong>{{ m.kind === 'inbound' ? current.name : shortName(m.author?.display_name) }}</strong>
            · {{ KIND_LABEL[m.kind] }} · {{ fullWhen(m.created_at) }}
          </div>
          <div class="ar-msg-body">{{ m.body }}</div>
        </div>
      </div>

      <div class="ar-reply">
        <div class="ar-kinds" role="radiogroup" aria-label="Tipo de resposta">
          <button v-for="k in kinds" :key="k.key" type="button" role="radio" :aria-checked="kind === k.key" class="ar-kind" :class="{ active: kind === k.key }"
                  :disabled="k.key === 'email' && !current.email" :title="k.key === 'email' && !current.email ? 'Esta pessoa não indicou email' : ''" @click="kind = k.key">
            <span class="material-icons">{{ KIND_ICON[k.key] }}</span> {{ k.label }}
          </button>
        </div>
        <textarea v-model="body" class="hd-textarea" rows="5" :placeholder="placeholder"></textarea>
        <div class="ar-reply-actions">
          <label class="ar-close"><input v-model="closeAfter" type="checkbox" /> Fechar o pedido</label>
          <button class="hd-btn hd-btn-primary" type="button" :disabled="!body.trim() || sending" @click="send">
            <span class="material-icons">{{ kind === 'email' ? 'send' : 'save' }}</span>
            {{ sending ? 'A enviar…' : kind === 'email' ? `Enviar para ${current.email}` : 'Registar' }}
          </button>
        </div>
      </div>
    </section>
    <section v-else class="ar-detail ar-placeholder hd-card">
      <span class="material-icons">contact_mail</span>
      Escolha um pedido para ver e responder.
    </section>
  </div>
</template>

<script setup lang="ts">
// Pedidos sem acesso: requests from the "Não tenho acesso ao mail institucional" form, answered here.
// Email answers go to the person; their replies come back into the same request (marker "[Acesso #N]").
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAccessRequest, importPreviousAccessRequests, listAccessRequests, replyAccessRequest, setAccessRequestStatus, type AccessRequest } from '../../api/accessRequests'
import { confirmDialog, notifyError, notifySuccess } from '../../utils/feedback'
import { shortName } from '../../utils/names'

const route = useRoute()
const router = useRouter()
const STATUS: Record<string, string> = { new: 'Por responder', answered: 'Respondido', closed: 'Fechado' }
const KIND_LABEL: Record<string, string> = { email: 'resposta por email', phone: 'contacto por telefone', note: 'nota interna', inbound: 'respondeu por email' }
const KIND_ICON: Record<string, string> = { email: 'mail', phone: 'call', note: 'sticky_note_2', inbound: 'reply' }
const kinds = [
  { key: 'email' as const, label: 'Responder por email' },
  { key: 'phone' as const, label: 'Registar telefonema' },
  { key: 'note' as const, label: 'Nota interna' },
]

const state = ref('open')
const search = ref('')
const items = ref<AccessRequest[]>([])
const counts = ref<Record<string, number>>({})
const loading = ref(true)
const current = ref<AccessRequest | null>(null)
const kind = ref<'email' | 'phone' | 'note'>('email')
const body = ref('')
const closeAfter = ref(false)
const sending = ref(false)
const importing = ref(false)

async function importPrevious() {
  const ok = await confirmDialog('Procurar os emails de aviso "Sem acesso ao mail institucional" dos últimos 4 meses e criar aqui os pedidos que ainda não existem? Ficam como "Por responder": feche os que já tratou por email.', { ok: 'Importar' })
  if (!ok) return
  importing.value = true
  try {
    const r = await importPreviousAccessRequests(120)
    notifySuccess(r.added ? `${r.added} pedido${r.added === 1 ? '' : 's'} importado${r.added === 1 ? '' : 's'}.` : 'Não havia pedidos novos para importar.')
    state.value = 'all'
    await load()
  } catch (e) {
    notifyError(e, 'Não foi possível importar.')
  } finally {
    importing.value = false
  }
}

const tabs = computed(() => [
  { key: 'open', label: 'Em aberto', count: (counts.value.new ?? 0) + (counts.value.answered ?? 0) },
  { key: 'new', label: 'Por responder', count: counts.value.new ?? 0 },
  { key: 'closed', label: 'Fechados', count: null },
  { key: 'all', label: 'Todos', count: null },
])
const placeholder = computed(() => ({
  email: 'Escreva a resposta — segue por email, assinada com o seu nome. A pessoa pode responder ao email.',
  phone: 'Resumo do telefonema (só a equipa vê).',
  note: 'Nota para a equipa (a pessoa não vê).',
}[kind.value]))

async function load() {
  loading.value = true
  try {
    const d = await listAccessRequests(state.value, search.value.trim())
    items.value = d.items
    counts.value = d.counts
  } catch (e) {
    notifyError(e, 'Não foi possível carregar os pedidos.')
  } finally {
    loading.value = false
  }
}

let searchTimer: number | undefined
function onSearch() {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(load, 250)
}
function setState(s: string) { state.value = s; load() }

async function open(id: number) {
  try {
    current.value = await getAccessRequest(id)
    kind.value = current.value.email ? 'email' : 'phone'
    body.value = ''
    closeAfter.value = false
    if (Number(route.query.pedido) !== id) router.replace({ query: { ...route.query, pedido: String(id) } })
  } catch (e) {
    notifyError(e, 'Não foi possível abrir o pedido.')
  }
}
function close() {
  current.value = null
  router.replace({ query: { ...route.query, pedido: undefined } })
}

async function send() {
  if (!current.value || !body.value.trim()) return
  sending.value = true
  try {
    current.value = await replyAccessRequest(current.value.id, body.value.trim(), kind.value, closeAfter.value)
    notifySuccess(kind.value === 'email' ? 'Resposta enviada.' : 'Registado.')
    body.value = ''
    closeAfter.value = false
    load()
  } catch (e) {
    notifyError(e, 'Não foi possível enviar.')
  } finally {
    sending.value = false
  }
}

async function changeStatus(s: 'new' | 'closed') {
  if (!current.value) return
  try {
    current.value = await setAccessRequestStatus(current.value.id, s)
    load()
  } catch (e) {
    notifyError(e, 'Não foi possível alterar o estado.')
  }
}

function toDate(iso: string) { return new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z') }
function when(iso: string) {
  const d = toDate(iso)
  const today = new Date()
  return d.toDateString() === today.toDateString()
    ? d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' })
}
function fullWhen(iso: string) {
  return toDate(iso).toLocaleString('pt-PT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

watch(() => route.query.pedido, (id) => { if (id && Number(id) !== current.value?.id) open(Number(id)) })
onMounted(async () => {
  await load()
  if (route.query.pedido) open(Number(route.query.pedido))
})
</script>

<style scoped>
.ar-page { display: grid; grid-template-columns: minmax(280px, 380px) minmax(0, 1fr); gap: 16px; align-items: start; max-width: 1280px; }
.ar-list { padding: 12px; display: flex; flex-direction: column; gap: 6px; max-height: calc(100vh - 140px); overflow: auto; }
.ar-tabs { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 4px; }
.ar-tab { border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-muted); border-radius: 999px; padding: 4px 10px; font-size: 12.5px; font-weight: 700; cursor: pointer; display: inline-flex; gap: 6px; align-items: center; }
.ar-tab.active { background: var(--c-primary); border-color: var(--c-primary); color: #fff; }
.ar-count { font-size: 11px; opacity: .85; }
.ar-search { margin-bottom: 4px; }
.ar-import { align-self: flex-start; display: inline-flex; align-items: center; gap: 5px; background: none; border: 0; color: var(--c-primary); font-size: 12.5px; font-weight: 700; cursor: pointer; padding: 2px 0 6px; }
.ar-import .material-icons { font-size: 16px; }
.ar-import:disabled { opacity: .6; cursor: wait; }
.ar-empty { color: var(--c-muted); font-size: 13px; padding: 30px 10px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.ar-empty .material-icons { font-size: 32px; }
.ar-item { text-align: left; border: 1px solid var(--c-border); border-radius: 10px; background: var(--c-surface); color: var(--c-text); padding: 10px 12px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; }
.ar-item.active { border-color: var(--c-primary); box-shadow: inset 0 0 0 1px var(--c-primary); }
.ar-item.unread strong { font-weight: 800; }
.ar-item-top { display: flex; justify-content: space-between; gap: 8px; }
.ar-item-top strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13.5px; }
.ar-when { font-size: 11.5px; color: var(--c-muted); flex-shrink: 0; }
.ar-item-meta { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--c-muted); flex-wrap: wrap; }
.ar-item-msg { font-size: 12.5px; color: var(--c-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ar-pill { font-size: 11px; font-weight: 800; border-radius: 999px; padding: 1px 8px; border: 1px solid transparent; }
.ar-pill.new { background: #FEF3C7; color: #92400E; border-color: #FCD34D; }
.ar-pill.answered { background: #DBEAFE; color: #1E40AF; border-color: #93C5FD; }
.ar-pill.closed { background: #E5E7EB; color: #374151; border-color: #D1D5DB; }
.dark .ar-pill.new { background: rgba(245, 158, 11, .15); color: #FCD34D; border-color: rgba(245, 158, 11, .4); }
.dark .ar-pill.answered { background: rgba(59, 130, 246, .15); color: #93C5FD; border-color: rgba(59, 130, 246, .4); }
.dark .ar-pill.closed { background: rgba(148, 163, 184, .15); color: #CBD5E1; border-color: rgba(148, 163, 184, .35); }
.ar-detail { padding: 18px 20px; display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.ar-placeholder { align-items: center; justify-content: center; color: var(--c-muted); min-height: 260px; text-align: center; }
.ar-placeholder .material-icons { font-size: 38px; }
.ar-detail-head { display: flex; align-items: center; gap: 10px; }
.ar-back { display: none; }
.ar-detail-title { flex: 1; min-width: 0; }
.ar-name { font-weight: 800; font-size: 17px; }
.ar-sub { font-size: 12.5px; color: var(--c-muted); margin-top: 2px; }
.ar-facts { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 8px 16px; margin: 0; padding: 12px 14px; border: 1px solid var(--c-border); border-radius: 10px; }
.ar-facts dt { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; color: var(--c-muted); }
.ar-facts dd { margin: 2px 0 0; font-size: 13.5px; word-break: break-word; }
.ar-thread { display: flex; flex-direction: column; gap: 10px; }
.ar-msg { border: 1px solid var(--c-border); border-radius: 10px; padding: 10px 12px; }
.ar-msg.inbound { background: var(--c-primary-soft, rgba(61, 82, 213, .06)); }
.ar-msg.note, .ar-msg.phone { border-style: dashed; }
.ar-msg-head { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--c-muted); flex-wrap: wrap; }
.ar-msg-head strong { color: var(--c-text); }
.ar-msg-head .material-icons { font-size: 15px; }
.ar-msg-body { white-space: pre-wrap; font-size: 13.5px; line-height: 1.5; margin-top: 6px; word-break: break-word; }
.ar-reply { border-top: 1px solid var(--c-border); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }
.ar-kinds { display: flex; gap: 6px; flex-wrap: wrap; }
.ar-kind { border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-text); border-radius: 8px; padding: 5px 10px; font-size: 12.5px; font-weight: 700; display: inline-flex; gap: 5px; align-items: center; cursor: pointer; }
.ar-kind .material-icons { font-size: 16px; }
.ar-kind.active { border-color: var(--c-primary); color: var(--c-primary); box-shadow: inset 0 0 0 1px var(--c-primary); }
.ar-kind:disabled { opacity: .45; cursor: not-allowed; }
.ar-reply-actions { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
.ar-close { display: inline-flex; gap: 6px; align-items: center; font-size: 13px; }
@media (max-width: 900px) {
  .ar-page { grid-template-columns: 1fr; }
  .ar-list { max-height: none; }
  .ar-page.has-open .ar-list, .ar-page:not(.has-open) .ar-detail { display: none; }
  .ar-back { display: inline-flex; }
  .ar-detail { padding: 14px; }
}
</style>
