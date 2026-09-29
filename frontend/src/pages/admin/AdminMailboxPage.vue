<template>
  <div class="hd-page mail-page">
    <div v-if="!loading && !configured" class="hd-card mail-off">
      <span class="material-icons">mail_lock</span>
      <div>
        <strong>A caixa de correio do helpdesk ainda não está ligada.</strong>
        <p>É usada a mesma ligação das respostas por email: Microsoft 365 (MAIL_REPLY_PROVIDER=graph, GRAPH_MAIL_USER e a permissão
          <em>Mail.ReadWrite</em> na app registration) ou IMAP (IMAP_SERVER, IMAP_USERNAME, IMAP_PASSWORD) no app.env.</p>
      </div>
    </div>

    <div v-else class="mail-layout" :class="{ reading: !!current }">
      <!-- List -->
      <section class="hd-card mail-list">
        <div class="mail-list-head">
          <div>
            <strong>Caixa de entrada</strong>
            <div class="mail-box">{{ mailbox }}</div>
          </div>
          <button class="hd-icon-btn" type="button" title="Atualizar" :disabled="loading" @click="load()"><span class="material-icons">refresh</span></button>
        </div>
        <div v-if="loading" class="mail-empty">A carregar…</div>
        <div v-else-if="error" class="mail-empty mail-error">{{ error }}</div>
        <template v-else>
          <button v-for="m in items" :key="m.id" type="button" class="mail-row" :class="{ unread: !m.is_read, active: current?.id === m.id }" @click="open(m)">
            <div class="mail-row-top">
              <span class="mail-from">{{ m.from_name || m.from_email }}</span>
              <span class="mail-date">{{ when(m.received_at) }}</span>
            </div>
            <div class="mail-subject">
              <span v-if="m.has_attachments" class="material-icons mail-clip">attach_file</span>{{ m.subject }}
            </div>
            <div class="mail-preview">{{ m.preview }}</div>
            <div class="mail-tags">
              <span v-if="m.ticket_id" class="mail-tag linked">T-{{ m.ticket_id }}</span>
              <span v-else-if="m.ticket_hint" class="mail-tag hint">resposta ao T-{{ m.ticket_hint }}</span>
              <span v-if="!m.sender_known" class="mail-tag ext">externo</span>
            </div>
          </button>
          <div v-if="!items.length" class="mail-empty">Caixa vazia.</div>
          <div class="mail-pages">
            <button class="hd-btn hd-btn-outline" type="button" :disabled="page === 1" @click="load(page - 1)">Anteriores</button>
            <span>Página {{ page }}</span>
            <button class="hd-btn hd-btn-outline" type="button" :disabled="!hasMore" @click="load(page + 1)">Seguintes</button>
          </div>
        </template>
      </section>

      <!-- Reading pane -->
      <section v-if="current" class="hd-card mail-read">
        <button class="mail-back" type="button" @click="current = null"><span class="material-icons">arrow_back</span> Voltar</button>
        <div v-if="loadingMsg" class="mail-empty">A abrir…</div>
        <template v-else-if="detail">
          <h2 class="mail-read-subject">{{ detail.subject }}</h2>
          <div class="mail-read-meta">
            <strong>{{ detail.from_name || detail.from_email }}</strong> &lt;{{ detail.from_email }}&gt;
            <span v-if="detail.sender" class="mail-tag known">utilizador do helpdesk</span>
            <span v-else class="mail-tag ext">sem conta no helpdesk</span>
            <div>{{ when(detail.received_at, true) }}</div>
          </div>
          <div v-if="detail.ticket_id" class="mail-linked">
            <span class="material-icons">link</span> Este email já está no <router-link :to="`/tickets/${detail.ticket_id}`">ticket T-{{ detail.ticket_id }}</router-link>.
          </div>
          <div class="mail-body">{{ detail.body || detail.preview }}</div>
          <div v-if="detail.attachments.length" class="mail-atts">
            <span v-for="a in detail.attachments" :key="a.name" class="mail-att"><span class="material-icons">attach_file</span>{{ a.name }} <small>{{ size(a.size) }}</small></span>
          </div>

          <div class="mail-actions">
            <template v-if="!detail.ticket_id && canManage">
              <button class="hd-btn hd-btn-primary" type="button" @click="mode = mode === 'new' ? '' : 'new'"><span class="material-icons">add_task</span> Criar ticket</button>
              <button class="hd-btn hd-btn-outline" type="button" @click="mode = mode === 'attach' ? '' : 'attach'"><span class="material-icons">playlist_add</span> Juntar a um ticket</button>
            </template>
            <button class="hd-btn hd-btn-outline" type="button" @click="toggleRead"><span class="material-icons">{{ current.is_read ? 'mark_email_unread' : 'mark_email_read' }}</span> {{ current.is_read ? 'Marcar como não lido' : 'Marcar como lido' }}</button>
            <button v-if="canArchive" class="hd-btn hd-btn-outline" type="button" @click="archive"><span class="material-icons">archive</span> Arquivar</button>
          </div>

          <div v-if="mode === 'new'" class="mail-form">
            <div class="mail-form-hint">
              {{ detail.sender ? `O pedido fica em nome de ${detail.sender.display_name}.` : 'O remetente não tem conta: o pedido fica em seu nome, com os dados do remetente na descrição.' }}
              Os anexos permitidos passam para o ticket.
            </div>
            <label>Assunto <input v-model="form.title" class="hd-input" /></label>
            <div class="mail-form-row">
              <label>Categoria <select v-model.number="form.category_id" class="hd-select"><option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option></select></label>
              <label>Escola <select v-model.number="form.school_id" class="hd-select"><option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option></select></label>
              <label>Prioridade <select v-model="form.priority" class="hd-select"><option value="low">Baixa</option><option value="medium">Média</option><option value="high">Alta</option><option value="urgent">Urgente</option></select></label>
            </div>
            <button class="hd-btn hd-btn-primary" type="button" :disabled="busy || !form.category_id || !form.school_id" @click="createTicket">{{ busy ? 'A criar…' : 'Criar ticket' }}</button>
          </div>
          <div v-if="mode === 'attach'" class="mail-form">
            <label>Número do ticket <input v-model="attachId" class="hd-input" placeholder="ex.: 142" inputmode="numeric" /></label>
            <label class="mail-check"><input v-model="attachInternal" type="checkbox" /> Juntar como nota interna (o requerente não vê)</label>
            <button class="hd-btn hd-btn-primary" type="button" :disabled="busy || !Number(String(attachId).replace(/\D/g, ''))" @click="attach">{{ busy ? 'A juntar…' : 'Juntar ao ticket' }}</button>
          </div>
        </template>
      </section>
      <section v-else class="hd-card mail-read mail-placeholder">
        <span class="material-icons">drafts</span>
        Escolha um email para o ler.
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
// Caixa de entrada do helpdesk (backend app/api/v1/mailbox.py)
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../boot/axios'
import { getCategories, getSchools } from '../../api/tickets'
import { useAuthStore } from '../../stores/auth'
import { errorMessage, notifyError, notifySuccess } from '../../utils/feedback'

const auth = useAuthStore()
const router = useRouter()
const canManage = computed(() => auth.isStaff)
const loading = ref(true)
const configured = ref(true)
const error = ref('')
const items = ref<any[]>([])
const mailbox = ref('')
const page = ref(1)
const hasMore = ref(false)
const canArchive = ref(true)
const current = ref<any | null>(null)
const detail = ref<any | null>(null)
const loadingMsg = ref(false)
const mode = ref<'' | 'new' | 'attach'>('')
const busy = ref(false)
const categories = ref<any[]>([])
const schools = ref<any[]>([])
const form = ref<any>({ title: '', category_id: null, school_id: null, priority: 'medium' })
const attachId = ref('')
const attachInternal = ref(false)

async function load(p = page.value) {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/api/v1/mailbox', { params: { page: p } })
    configured.value = data.configured
    items.value = data.items
    mailbox.value = data.mailbox
    hasMore.value = data.has_more
    canArchive.value = data.can_archive !== false
    page.value = p
  } catch (e) {
    error.value = errorMessage(e, 'Não foi possível ler a caixa de correio.')
  } finally {
    loading.value = false
  }
}

async function open(m: any) {
  current.value = m
  mode.value = ''
  detail.value = null
  loadingMsg.value = true
  try {
    detail.value = (await api.get('/api/v1/mailbox/message', { params: { id: m.id } })).data
    form.value = { title: detail.value.subject, category_id: categories.value[0]?.id ?? null, school_id: schools.value[0]?.id ?? null, priority: 'medium' }
    attachId.value = detail.value.ticket_hint ? String(detail.value.ticket_hint) : ''
    if (!m.is_read) {
      api.post('/api/v1/mailbox/read', { id: m.id, read: true }).then(() => { m.is_read = true }).catch(() => {})
    }
  } catch (e) {
    notifyError(e, 'Não foi possível abrir o email.')
  } finally {
    loadingMsg.value = false
  }
}

async function toggleRead() {
  const m = current.value
  try {
    await api.post('/api/v1/mailbox/read', { id: m.id, read: !m.is_read })
    m.is_read = !m.is_read
  } catch (e) {
    notifyError(e, 'Não foi possível alterar.')
  }
}

async function archive() {
  try {
    await api.post('/api/v1/mailbox/archive', { id: current.value.id })
    items.value = items.value.filter((x) => x.id !== current.value.id)
    current.value = null
    notifySuccess('Email arquivado.')
  } catch (e) {
    notifyError(e, 'Não foi possível arquivar.')
  }
}

function report(data: any) {
  const extra = data.skipped?.length ? ` Anexos não permitidos (não copiados): ${data.skipped.join(', ')}.` : ''
  notifySuccess(`Feito: ticket T-${data.ticket_id}.${extra}`)
}

async function createTicket() {
  busy.value = true
  try {
    const { data } = await api.post('/api/v1/mailbox/ticket', { id: current.value.id, ...form.value })
    report(data)
    router.push(`/tickets/${data.ticket_id}`)
  } catch (e) {
    notifyError(e, 'Não foi possível criar o ticket.')
  } finally {
    busy.value = false
  }
}

async function attach() {
  busy.value = true
  try {
    const { data } = await api.post('/api/v1/mailbox/attach', {
      id: current.value.id, ticket_id: Number(String(attachId.value).replace(/\D/g, '')), internal: attachInternal.value,
    })
    report(data)
    router.push(`/tickets/${data.ticket_id}`)
  } catch (e) {
    notifyError(e, 'Não foi possível juntar o email.')
  } finally {
    busy.value = false
  }
}

function when(iso: string, full = false) {
  if (!iso) return ''
  const d = new Date(iso)
  const today = new Date()
  if (!full && d.toDateString() === today.toDateString()) return d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
  return d.toLocaleString('pt-PT', full ? { dateStyle: 'full', timeStyle: 'short' } : { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
const size = (n: number) => (n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`)

onMounted(async () => {
  getCategories().then((c) => { categories.value = c }).catch(() => {})
  getSchools().then((s) => { schools.value = s }).catch(() => {})
  await load(1)
})
</script>

<style scoped>
.mail-page { max-width: none; }
.mail-off { display: flex; gap: 14px; padding: 20px; align-items: flex-start; }
.mail-off .material-icons { font-size: 32px; color: var(--c-muted); }
.mail-off p { margin: 6px 0 0; color: var(--c-muted); font-size: 13.5px; }
.mail-layout { display: grid; grid-template-columns: minmax(300px, 420px) minmax(0, 1fr); gap: 16px; align-items: start; }
.mail-list { overflow: hidden; }
.mail-list-head { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--c-border); }
.mail-box { font-size: 12px; color: var(--c-muted); }
.mail-row { display: block; width: 100%; text-align: left; border: 0; border-bottom: 1px solid var(--c-border); background: transparent; padding: 11px 16px; cursor: pointer; color: var(--c-text); }
.mail-row:hover { background: var(--c-surface-soft); }
.mail-row.active { background: var(--c-primary-soft); }
.mail-row-top { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; }
.mail-from { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mail-row.unread .mail-from, .mail-row.unread .mail-subject { font-weight: 800; }
.mail-row.unread { box-shadow: inset 3px 0 0 #2563EB; }
.mail-date { font-size: 11.5px; color: var(--c-muted); white-space: nowrap; }
.mail-subject { font-size: 13px; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mail-clip { font-size: 14px; vertical-align: -2px; margin-right: 3px; color: var(--c-muted); }
.mail-preview { font-size: 12px; color: var(--c-muted); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mail-tags { display: flex; gap: 6px; margin-top: 4px; }
.mail-tag { font-size: 10.5px; font-weight: 700; border-radius: 6px; padding: 0 6px; }
.mail-tag.linked { background: #DCFCE7; color: #166534; }
.mail-tag.hint { background: #E0E7FF; color: #3730A3; }
.mail-tag.ext { background: #FEF3C7; color: #92400E; }
.mail-tag.known { background: #DBEAFE; color: #1E40AF; }
.dark .mail-tag.linked { background: rgba(22, 163, 74, .2); color: #86EFAC; }
.dark .mail-tag.hint { background: rgba(99, 102, 241, .22); color: #C7D2FE; }
.dark .mail-tag.ext { background: rgba(217, 119, 6, .2); color: #FCD34D; }
.dark .mail-tag.known { background: rgba(37, 99, 235, .22); color: #BFDBFE; }
.mail-pages { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; font-size: 12.5px; color: var(--c-muted); }
.mail-pages .hd-btn { font-size: 12px; padding: 4px 10px; }
.mail-empty { padding: 40px 16px; text-align: center; color: var(--c-muted); }
.mail-error { color: #DC2626; }
.mail-read { padding: 20px 22px; min-height: 320px; }
.mail-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: var(--c-muted); }
.mail-placeholder .material-icons { font-size: 40px; }
.mail-back { display: none; border: 0; background: transparent; color: var(--c-primary); font-weight: 700; cursor: pointer; align-items: center; gap: 4px; padding: 0 0 10px; }
.mail-read-subject { font-family: var(--font-sans); font-size: 18px; font-weight: 800; margin: 0 0 6px; }
.mail-read-meta { font-size: 13px; color: var(--c-muted); margin-bottom: 14px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.mail-read-meta > div { width: 100%; }
.mail-linked { display: flex; align-items: center; gap: 6px; background: #DCFCE7; color: #166534; border-radius: 8px; padding: 8px 12px; font-size: 13px; margin-bottom: 12px; }
.dark .mail-linked { background: rgba(22, 163, 74, .18); color: #86EFAC; }
.mail-body { white-space: pre-wrap; font-size: 14px; line-height: 1.55; border-top: 1px solid var(--c-border); padding-top: 14px; max-height: 55vh; overflow-y: auto; overflow-wrap: anywhere; }
.mail-atts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.mail-att { display: inline-flex; align-items: center; gap: 4px; font-size: 12.5px; border: 1px solid var(--c-border); border-radius: 8px; padding: 3px 8px; }
.mail-att .material-icons { font-size: 15px; color: var(--c-muted); }
.mail-att small { color: var(--c-muted); }
.mail-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
.mail-actions .hd-btn { font-size: 12.5px; }
.mail-form { margin-top: 14px; border: 1px solid var(--c-border); border-radius: 12px; padding: 14px; display: flex; flex-direction: column; gap: 10px; background: var(--c-surface-soft); }
.mail-form label { display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; font-weight: 700; color: var(--c-muted); }
.mail-form .mail-check { flex-direction: row; align-items: center; gap: 6px; font-weight: 600; }
.mail-form-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.mail-form-hint { font-size: 12.5px; color: var(--c-muted); }
.mail-form .hd-btn { align-self: flex-end; }
@media (max-width: 900px) {
  .mail-layout { grid-template-columns: 1fr; }
  .mail-layout.reading .mail-list { display: none; }
  .mail-layout:not(.reading) .mail-placeholder { display: none; }
  .mail-back { display: inline-flex; }
  .mail-form-row { grid-template-columns: 1fr; }
}
</style>
