<template>
  <div class="hd-page admin-tickets-page">
    <div class="tickets-heading">
      <div>
        <h1>Gestão de tickets</h1>
        <p>{{ total }} ticket{{ total !== 1 ? 's' : '' }} encontrado{{ total !== 1 ? 's' : '' }}</p>
      </div>
      <div class="tickets-actions">
        <button v-if="auth.isAdmin" class="hd-btn hd-btn-outline" @click="syncReplies" :disabled="mailSyncing">
          <span class="material-icons">mark_email_read</span>
          {{ mailSyncing ? 'A atualizar emails...' : 'Atualizar receção de emails' }}
        </button>
        <button class="hd-btn hd-btn-primary" @click="load">
          <span class="material-icons">refresh</span>
          Atualizar
        </button>
      </div>
    </div>

    <section class="hd-card tickets-panel">
      <div class="filters-grid">
        <input class="hd-input" v-model="searchQuery" placeholder="Pesquisar..." @input="debouncedLoad" style="grid-column:1/-1" />
        <select class="hd-select" v-model="filterStatus" @change="resetAndLoad">
          <option value="">Todos os estados</option>
          <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
        </select>
        <select class="hd-select" v-model="filterCat" @change="resetAndLoad">
          <option value="">Todas as categorias</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <select class="hd-select" v-model="filterPriority" @change="resetAndLoad">
          <option value="">Todas as prioridades</option>
          <option value="urgent">Urgente</option>
          <option value="high">Alta</option>
          <option value="medium">Média</option>
          <option value="low">Baixa</option>
        </select>
        <select class="hd-select" v-model="filterSchool" @change="resetAndLoad">
          <option value="">Todas as escolas</option>
          <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </div>

      <div v-if="mailSyncMessage" class="mail-sync-message">{{ mailSyncMessage }}</div>

      <div v-if="selectedIds.length" class="bulk-bar">
        <strong>{{ selectedIds.length }} selecionado{{ selectedIds.length !== 1 ? 's' : '' }}</strong>
        <select class="hd-select" v-model="bulkStatus">
          <option value="">Estado...</option>
          <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
        </select>
        <button class="hd-btn hd-btn-outline" :disabled="!bulkStatus" @click="applyBulkStatus">Aplicar estado</button>
        <select class="hd-select" v-model="bulkAssignee">
          <option value="">Responsável...</option>
          <option value="none">— Não atribuído</option>
          <option v-for="u in staffUsers" :key="u.id" :value="String(u.id)">{{ u.display_name }}</option>
        </select>
        <button class="hd-btn hd-btn-outline" :disabled="!bulkAssignee" @click="applyBulkAssignee">Aplicar responsável</button>
        <select class="hd-select" v-model="bulkGroup">
          <option value="">Grupo...</option>
          <option value="none">— Sem grupo</option>
          <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
        </select>
        <button class="hd-btn hd-btn-outline" :disabled="!bulkGroup" @click="applyBulkGroup">Aplicar grupo</button>
        <select class="hd-select" v-model="bulkPriority">
          <option value="">Prioridade...</option>
          <option value="urgent">Urgente</option>
          <option value="high">Alta</option>
          <option value="medium">Média</option>
          <option value="low">Baixa</option>
        </select>
        <button class="hd-btn hd-btn-outline" :disabled="!bulkPriority" @click="applyBulkPriority">Aplicar prioridade</button>
        <button v-if="auth.isAdmin" class="hd-btn hd-btn-outline" @click="archiveSelected">
          <span class="material-icons">archive</span>
          Arquivar
        </button>
        <button v-if="auth.isAdmin" class="hd-btn danger-action" @click="deleteSelected">
          <span class="material-icons">delete</span>
          Apagar
        </button>
        <button class="hd-btn hd-btn-outline" @click="selectedIds = []">Limpar</button>
      </div>

      <div v-if="loading" class="state-block">A carregar...</div>

      <template v-else>
        <div class="desktop-table-wrap">
          <table class="hd-table tickets-table">
            <thead>
              <tr>
                <th><input type="checkbox" :checked="allVisibleSelected" @change="toggleAllVisible" /></th>
                <th>Ticket</th>
                <th>Assunto</th>
                <th>Categoria</th>
                <th>Solicitante</th>
                <th>Prioridade</th>
                <th>Tempo de resposta</th>
                <th>Estado</th>
                <th>Responsável</th>
                <th>Grupo</th>
                <th v-if="auth.isAdmin">Emails</th>
                <th>Atualizado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in tickets" :key="t.id">
                <td><input type="checkbox" :checked="selectedIds.includes(t.id)" @change="toggleSelected(t.id)" /></td>
                <td class="ticket-id">T-{{ t.id }}</td>
                <td class="subject-cell">
                  <router-link :to="`/tickets/${t.id}`">{{ t.title }}</router-link>
                  <small>{{ t.school?.short_name || t.school?.name || 'Sem escola' }}</small>
                </td>
                <td><CategoryPill :category="t.category" /></td>
                <td v-if="auth.isAdmin">
                  <div class="user-cell">
                    <AvatarCircle :name="t.creator.display_name" size="24" />
                    <span>{{ t.creator.display_name }}</span>
                  </div>
                </td>
                <td><PriorityBadge :priority="t.priority" /></td>
                <td><SlaBadge :created-at="t.created_at" :sla-hours="t.category?.sla_hours" :status="t.status" /></td>
                <td><StatusSelect :value="t.status" :options="statusOpts" @change="changeStatus(t, $event)" /></td>
                <td>
                  <AssigneeSelect :value="primaryAssigneeId(t)" :users="staffUsers" @change="changeAssignee(t, $event)" />
                  <small v-if="assigneeSummary(t)" class="assignee-summary">{{ assigneeSummary(t) }}</small>
                </td>
                <td><GroupSelect :value="t.group?.id ?? ''" :groups="groups" @change="changeGroup(t, $event)" /></td>
                <td>
                  <button
                    class="email-pill"
                    :class="{ active: t.creator_email_notifications }"
                    @click="toggleEmailNotifications(t)"
                  >
                    <span class="material-icons">{{ t.creator_email_notifications ? 'notifications_active' : 'notifications_off' }}</span>
                    {{ t.creator_email_notifications ? 'Ativos' : 'Desativados' }}
                  </button>
                </td>
                <td class="muted-cell">{{ timeAgo(t.updated_at) }}</td>
                <td>
                  <router-link :to="`/tickets/${t.id}`">
                    <button class="hd-icon-btn" title="Ver detalhes">
                      <span class="material-icons">open_in_new</span>
                    </button>
                  </router-link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mobile-ticket-list">
          <article v-for="t in tickets" :key="t.id" class="ticket-card">
            <div class="ticket-card-top">
              <input type="checkbox" :checked="selectedIds.includes(t.id)" @change="toggleSelected(t.id)" />
              <div class="ticket-card-title">
                <router-link :to="`/tickets/${t.id}`">T-{{ t.id }} · {{ t.title }}</router-link>
                <small>{{ t.school?.name || 'Sem escola' }} · {{ timeAgo(t.updated_at) }}</small>
              </div>
            </div>
            <div class="ticket-card-meta">
              <CategoryPill :category="t.category" />
              <PriorityBadge :priority="t.priority" />
            </div>
            <div class="ticket-card-user">
              <AvatarCircle :name="t.creator.display_name" size="26" />
              <span>{{ t.creator.display_name }}</span>
            </div>
            <div class="ticket-card-controls">
              <label>Estado<StatusSelect :value="t.status" :options="statusOpts" @change="changeStatus(t, $event)" /></label>
              <label>
                Responsável
                <AssigneeSelect :value="primaryAssigneeId(t)" :users="staffUsers" @change="changeAssignee(t, $event)" />
                <small v-if="assigneeSummary(t)" class="assignee-summary">{{ assigneeSummary(t) }}</small>
              </label>
              <label>Grupo<GroupSelect :value="t.group?.id ?? ''" :groups="groups" @change="changeGroup(t, $event)" /></label>
              <label v-if="auth.isAdmin">
                Emails
                <button
                  class="email-pill"
                  :class="{ active: t.creator_email_notifications }"
                  @click="toggleEmailNotifications(t)"
                >
                  <span class="material-icons">{{ t.creator_email_notifications ? 'notifications_active' : 'notifications_off' }}</span>
                  {{ t.creator_email_notifications ? 'Ativos' : 'Desativados' }}
                </button>
              </label>
            </div>
          </article>
        </div>

        <div v-if="!tickets.length" class="state-block">Sem tickets.</div>
      </template>

      <div v-if="total > pageSize" class="pagination-row">
        <button class="hd-btn hd-btn-outline" :disabled="page <= 1" @click="page--;load()">Anterior</button>
        <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button class="hd-btn hd-btn-outline" :disabled="page >= Math.ceil(total / pageSize)" @click="page++;load()">Próxima</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import { adminBulkActionTickets, adminBulkUpdateTickets, adminUpdateTicket, getCategories, getSchools, getTickets, syncMailReplies } from '../../api/tickets'
import { getGroups, getUsers } from '../../api/users'
import { useAuthStore } from '../../stores/auth'
import AvatarCircle from '../../components/AvatarCircle.vue'
import PriorityBadge from '../../components/PriorityBadge.vue'
import SlaBadge from '../../components/SlaBadge.vue'
import { timeAgo as formatTimeAgo } from '../../utils/dates'

const CategoryPill = defineComponent({
  props: { category: { type: Object, required: true } },
  setup(props) {
    return () => h('span', {
      class: 'category-pill',
      style: { background: `${(props.category as any).color}22`, color: (props.category as any).color },
    }, [
      h('span', { class: 'material-icons' }, (props.category as any).icon),
      (props.category as any).name,
    ])
  },
})

const StatusSelect = defineComponent({
  props: { value: { type: String, required: true }, options: { type: Array, required: true } },
  emits: ['change'],
  setup(props, { emit }) {
    return () => h('select', {
      class: 'hd-select compact-select',
      value: props.value,
      onChange: (e: Event) => emit('change', (e.target as HTMLSelectElement).value),
    }, (props.options as any[]).map(o => h('option', { value: o.v }, o.l)))
  },
})

const AssigneeSelect = defineComponent({
  props: { value: { type: [String, Number], default: '' }, users: { type: Array, required: true } },
  emits: ['change'],
  setup(props, { emit }) {
    return () => h('select', {
      class: 'hd-select compact-select',
      value: props.value,
      onChange: (e: Event) => emit('change', (e.target as HTMLSelectElement).value),
    }, [
      h('option', { value: '' }, '— Nenhum'),
      ...(props.users as any[]).map(u => h('option', { value: u.id }, u.display_name)),
    ])
  },
})

const GroupSelect = defineComponent({
  props: { value: { type: [String, Number], default: '' }, groups: { type: Array, required: true } },
  emits: ['change'],
  setup(props, { emit }) {
    return () => h('select', {
      class: 'hd-select compact-select',
      value: props.value,
      onChange: (e: Event) => emit('change', (e.target as HTMLSelectElement).value),
    }, [
      h('option', { value: '' }, '— Sem grupo'),
      ...(props.groups as any[]).map(g => h('option', { value: g.id }, g.name)),
    ])
  },
})

const tickets = ref<any[]>([])
const auth = useAuthStore()
const categories = ref<any[]>([])
const schools = ref<any[]>([])
const staffUsers = ref<any[]>([])
const groups = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 25
const selectedIds = ref<number[]>([])
const bulkStatus = ref('')
const bulkAssignee = ref('')
const bulkGroup = ref('')
const bulkPriority = ref('')
const mailSyncMessage = ref('')
const mailSyncing = ref(false)
const filterStatus = ref('')
const filterCat = ref<number | ''>('')
const filterPriority = ref('')
const filterSchool = ref<number | ''>('')
const searchQuery = ref('')
let _searchTimer: ReturnType<typeof setTimeout> | null = null

const statusOpts = [
  { v: 'open', l: 'Aberto' },
  { v: 'assigned', l: 'Atribuído' },
  { v: 'in_progress', l: 'Em Curso' },
  { v: 'waiting_user', l: 'A aguardar utilizador' },
  { v: 'resolved', l: 'Resolvido' },
  { v: 'closed', l: 'Fechado' },
]

const allVisibleSelected = computed(() => tickets.value.length > 0 && tickets.value.every(t => selectedIds.value.includes(t.id)))

onMounted(async () => {
  const [cats, schs, users, grps] = await Promise.all([getCategories(), getSchools(), getUsers(), getGroups()])
  categories.value = cats
  schools.value = schs
  groups.value = grps
  staffUsers.value = users.filter(isAssignableTechnician)
  await load()
})

function resetAndLoad() {
  page.value = 1
  load()
}

function debouncedLoad() {
  if (_searchTimer) clearTimeout(_searchTimer)
  _searchTimer = setTimeout(() => { page.value = 1; load() }, 350)
}

async function load() {
  loading.value = true
  try {
    const params: any = { page: page.value, size: pageSize, admin: true }
    if (filterStatus.value) params.status = filterStatus.value
    if (filterCat.value) params.category_id = filterCat.value
    if (filterPriority.value) params.priority = filterPriority.value
    if (filterSchool.value) params.school_id = filterSchool.value
    if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
    const data = await getTickets(params)
    tickets.value = data.items
    total.value = data.total
    selectedIds.value = selectedIds.value.filter(id => tickets.value.some(t => t.id === id))
  } finally {
    loading.value = false
  }
}

async function changeStatus(ticket: any, status: string) {
  await updateTicketInList(ticket.id, { status })
}

async function changeAssignee(ticket: any, value: string) {
  await updateTicketInList(ticket.id, { assignee_ids: value ? [Number(value)] : [] })
}

async function changeGroup(ticket: any, value: string) {
  await updateTicketInList(ticket.id, { group_id: value ? Number(value) : null })
}

async function toggleEmailNotifications(ticket: any) {
  await updateTicketInList(ticket.id, { creator_email_notifications: !ticket.creator_email_notifications })
}

async function updateTicketInList(id: number, payload: any) {
  try {
    const updated = await adminUpdateTicket(id, payload)
    const idx = tickets.value.findIndex(t => t.id === id)
    if (idx !== -1) tickets.value[idx] = { ...tickets.value[idx], ...updated }
  } catch {
    await load()
  }
}

function toggleSelected(id: number) {
  selectedIds.value = selectedIds.value.includes(id) ? selectedIds.value.filter(item => item !== id) : [...selectedIds.value, id]
}

function toggleAllVisible() {
  if (allVisibleSelected.value) {
    selectedIds.value = selectedIds.value.filter(id => !tickets.value.some(t => t.id === id))
  } else {
    selectedIds.value = Array.from(new Set([...selectedIds.value, ...tickets.value.map(t => t.id)]))
  }
}

async function applyBulkStatus() {
  if (!bulkStatus.value) return
  await applyBulk({ status: bulkStatus.value })
  bulkStatus.value = ''
}

async function applyBulkAssignee() {
  if (!bulkAssignee.value) return
  await applyBulk({ assignee_ids: bulkAssignee.value === 'none' ? [] : [Number(bulkAssignee.value)] })
  bulkAssignee.value = ''
}

function primaryAssigneeId(ticket: any) {
  return ticket.assignees?.[0]?.id ?? ticket.assignee?.id ?? ''
}

function assigneeSummary(ticket: any) {
  const assignees = ticket.assignees?.length ? ticket.assignees : (ticket.assignee ? [ticket.assignee] : [])
  if (!assignees.length) return ''
  if (assignees.length === 1) return assignees[0].display_name
  return `${assignees[0].display_name} +${assignees.length - 1}`
}

function isAssignableTechnician(u: any) {
  return u?.is_active && (u.role === 'technician' || u.is_technician)
}

async function applyBulkGroup() {
  if (!bulkGroup.value) return
  await applyBulk({ group_id: bulkGroup.value === 'none' ? null : Number(bulkGroup.value) })
  bulkGroup.value = ''
}

async function applyBulkPriority() {
  if (!bulkPriority.value) return
  await applyBulk({ priority: bulkPriority.value })
  bulkPriority.value = ''
}

async function applyBulk(payload: any) {
  if (!selectedIds.value.length) return
  try {
    const updated = await adminBulkUpdateTickets({ ids: selectedIds.value, ...payload })
    for (const item of updated) {
      const idx = tickets.value.findIndex(t => t.id === item.id)
      if (idx !== -1) tickets.value[idx] = { ...tickets.value[idx], ...item }
    }
  } catch {
    await load()
  }
}

async function archiveSelected() {
  if (!selectedIds.value.length) return
  if (!window.confirm(`Arquivar ${selectedIds.value.length} ticket(s) selecionado(s)?`)) return
  await adminBulkActionTickets({ ids: selectedIds.value, action: 'archive' })
  selectedIds.value = []
  await load()
}

async function deleteSelected() {
  if (!selectedIds.value.length) return
  if (!window.confirm(`Apagar definitivamente ${selectedIds.value.length} ticket(s)? Esta ação não pode ser anulada.`)) return
  await adminBulkActionTickets({ ids: selectedIds.value, action: 'delete' })
  selectedIds.value = []
  await load()
}

async function syncReplies() {
  if (mailSyncing.value) return
  mailSyncing.value = true
  mailSyncMessage.value = 'A ler respostas de email...'
  try {
    const result = await syncMailReplies()
    mailSyncMessage.value = `Respostas lidas: ${result.processed} adicionada(s), ${result.skipped} ignorada(s).`
    await load()
  } catch {
    mailSyncMessage.value = 'Não foi possível ler respostas de email. Verifica a configuração IMAP.'
  } finally {
    mailSyncing.value = false
  }
}

function timeAgo(date: string) {
  return formatTimeAgo(date)
}
</script>

<style scoped>
.admin-tickets-page { max-width: 1400px; }
.tickets-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
}
.tickets-heading h1 { margin: 0 0 4px; font-size: 24px; }
.tickets-heading p { margin: 0; color: var(--c-muted); }
.tickets-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.tickets-panel { overflow: hidden; }
.filters-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(160px, 1fr));
  gap: 10px;
  padding: 16px;
  border-bottom: 1px solid var(--c-border);
}
.mail-sync-message {
  padding: 10px 16px;
  border-bottom: 1px solid var(--c-border);
  color: var(--c-muted);
  font-size: 13px;
}
.bulk-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-bg);
}
.bulk-bar .hd-select { width: auto; min-width: 150px; }
.danger-action {
  border-color: rgba(239, 68, 68, .35);
  color: #EF4444;
  background: rgba(239, 68, 68, .08);
}
.danger-action:hover { background: rgba(239, 68, 68, .14); }
.desktop-table-wrap { overflow-x: auto; }
.tickets-table { min-width: 1420px; }
.tickets-table th, .tickets-table td { vertical-align: middle; }
.ticket-id, .muted-cell { color: var(--c-muted); font-size: 12px; white-space: nowrap; }
.subject-cell { max-width: 260px; }
.subject-cell a {
  display: block;
  color: var(--c-text);
  font-weight: 700;
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.subject-cell small {
  display: block;
  margin-top: 3px;
  color: var(--c-muted);
}
.user-cell {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 180px;
}
:deep(.category-pill) {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
:deep(.category-pill .material-icons) { font-size: 13px; }
:deep(.compact-select) {
  width: auto;
  min-width: 132px;
  padding: 5px 8px;
  font-size: 12px;
}
.assignee-summary {
  color: var(--c-muted);
  display: block;
  font-size: 11px;
  margin-top: 4px;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.email-pill {
  align-items: center;
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 999px;
  color: var(--c-muted);
  cursor: pointer;
  display: inline-flex;
  font-size: 12px;
  font-weight: 800;
  gap: 5px;
  justify-content: center;
  min-width: 116px;
  padding: 5px 9px;
}
.email-pill.active {
  background: rgba(22, 163, 74, 0.1);
  border-color: rgba(22, 163, 74, 0.24);
  color: #15803D;
}
.email-pill .material-icons {
  font-size: 14px;
}
.state-block {
  padding: 44px 18px;
  text-align: center;
  color: var(--c-muted);
}
.pagination-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--c-border);
  color: var(--c-muted);
}
.mobile-ticket-list { display: none; }
@media (max-width: 980px) {
  .filters-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 820px) {
  .tickets-heading { display: grid; grid-template-columns: 1fr; }
  .tickets-actions { display: grid; grid-template-columns: 1fr 1fr; }
  .tickets-actions .hd-btn { justify-content: center; }
  .filters-grid { grid-template-columns: 1fr; padding: 12px; }
  .bulk-bar { display: grid; grid-template-columns: 1fr; }
  .bulk-bar .hd-select, .bulk-bar .hd-btn { width: 100%; }
  .desktop-table-wrap { display: none; }
  .mobile-ticket-list {
    display: grid;
    gap: 12px;
    padding: 12px;
  }
  .ticket-card {
    border: 1px solid var(--c-border);
    border-radius: 8px;
    padding: 12px;
    background: var(--c-surface);
  }
  .ticket-card-top {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 10px;
    align-items: start;
  }
  .ticket-card-title a {
    display: block;
    color: var(--c-text);
    font-weight: 800;
    text-decoration: none;
    line-height: 1.3;
  }
  .ticket-card-title small {
    display: block;
    color: var(--c-muted);
    margin-top: 3px;
  }
  .ticket-card-meta, .ticket-card-user {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    margin-top: 10px;
  }
  .ticket-card-user span { font-size: 13px; color: var(--c-muted); }
  .ticket-card-controls {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    margin-top: 12px;
  }
  .ticket-card-controls label {
    display: grid;
    gap: 5px;
    color: var(--c-muted);
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
  }
  :deep(.compact-select) { width: 100%; }
  .pagination-row { justify-content: center; }
}
</style>
