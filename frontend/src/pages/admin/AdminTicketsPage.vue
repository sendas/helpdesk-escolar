<template>
  <div class="hd-page">
    <div class="hd-row" style="margin-bottom:20px">
      <h1 style="font-size:22px">Gestão de tickets</h1>
      <div class="hd-spacer"></div>
      <span style="font-size:13px;color:var(--c-muted)">{{ total }} ticket{{ total !== 1 ? 's' : '' }}</span>
    </div>

    <div class="hd-card">
      <!-- Filters -->
      <div style="display:flex;gap:10px;padding:14px 16px;border-bottom:1px solid var(--c-border);flex-wrap:wrap;align-items:center">
        <select class="hd-select" style="width:auto" v-model="filterStatus" @change="load">
          <option value="">Todos os estados</option>
          <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
        </select>
        <select class="hd-select" style="width:auto" v-model="filterCat" @change="load">
          <option value="">Todas as categorias</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <select class="hd-select" style="width:auto" v-model="filterPriority" @change="load">
          <option value="">Todas as prioridades</option>
          <option value="urgent">Urgente</option>
          <option value="high">Alta</option>
          <option value="medium">Média</option>
          <option value="low">Baixa</option>
        </select>
        <select class="hd-select" style="width:auto" v-model="filterSchool" @change="load">
          <option value="">Todas as escolas</option>
          <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
        <div class="hd-spacer"></div>
        <button class="hd-btn hd-btn-outline" style="font-size:12px;padding:6px 12px" @click="syncReplies">
          <span class="material-icons" style="font-size:14px">mark_email_read</span> Ler respostas
        </button>
        <button class="hd-btn hd-btn-outline" style="font-size:12px;padding:6px 12px" @click="load">
          <span class="material-icons" style="font-size:14px">refresh</span> Atualizar
        </button>
      </div>
      <div v-if="mailSyncMessage" style="padding:10px 16px;border-bottom:1px solid var(--c-border);font-size:13px;color:var(--c-muted)">
        {{ mailSyncMessage }}
      </div>

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
        <select class="hd-select" v-model="bulkPriority">
          <option value="">Prioridade...</option>
          <option value="urgent">Urgente</option>
          <option value="high">Alta</option>
          <option value="medium">Média</option>
          <option value="low">Baixa</option>
        </select>
        <button class="hd-btn hd-btn-outline" :disabled="!bulkPriority" @click="applyBulkPriority">Aplicar prioridade</button>
        <button class="hd-btn hd-btn-outline" @click="selectedIds = []">Limpar</button>
      </div>

      <div v-if="loading" style="padding:48px;text-align:center;color:var(--c-muted)">A carregar...</div>
      <table v-else class="hd-table">
        <thead>
          <tr>
            <th><input type="checkbox" :checked="allVisibleSelected" @change="toggleAllVisible" /></th>
            <th>ID</th>
            <th>ASSUNTO</th>
            <th>CATEGORIA</th>
            <th>SOLICITANTE</th>
            <th>PRIORIDADE</th>
            <th>ESTADO</th>
            <th>RESPONSÁVEL</th>
            <th>ATUALIZADO</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tickets" :key="t.id">
            <td><input type="checkbox" :checked="selectedIds.includes(t.id)" @change="toggleSelected(t.id)" /></td>
            <td style="color:var(--c-muted);font-size:12px;white-space:nowrap">T-{{ t.id }}</td>
            <td style="font-weight:500;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ t.title }}</td>
            <td>
              <span style="display:inline-flex;align-items:center;gap:4px;font-size:12px;padding:2px 8px;border-radius:4px"
                :style="{ background: t.category.color + '22', color: t.category.color }">
                <span class="material-icons" style="font-size:12px">{{ t.category.icon }}</span>
                {{ t.category.name }}
              </span>
            </td>
            <td>
              <div class="hd-row" style="gap:6px">
                <AvatarCircle :name="t.creator.display_name" size="24" />
                <span style="font-size:13px">{{ t.creator.display_name }}</span>
              </div>
            </td>
            <td><PriorityBadge :priority="t.priority" /></td>
            <td>
              <select
                class="hd-select"
                style="font-size:12px;padding:3px 6px;width:auto"
                :value="t.status"
                @change="changeStatus(t, ($event.target as HTMLSelectElement).value)"
              >
                <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
              </select>
            </td>
            <td>
              <select
                class="hd-select"
                style="font-size:12px;padding:3px 6px;width:auto"
                :value="t.assignee?.id ?? ''"
                @change="changeAssignee(t, ($event.target as HTMLSelectElement).value)"
              >
                <option value="">— Nenhum</option>
                <option v-for="u in staffUsers" :key="u.id" :value="u.id">{{ u.display_name }}</option>
              </select>
            </td>
            <td style="color:var(--c-muted);white-space:nowrap">{{ timeAgo(t.updated_at) }}</td>
            <td>
              <router-link :to="`/tickets/${t.id}`">
                <button class="hd-icon-btn" title="Ver detalhes">
                  <span class="material-icons" style="font-size:16px">open_in_new</span>
                </button>
              </router-link>
            </td>
          </tr>
          <tr v-if="!tickets.length">
            <td colspan="10" style="text-align:center;color:var(--c-muted);padding:40px">Sem tickets.</td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div v-if="total > pageSize" class="hd-row" style="padding:12px 16px;border-top:1px solid var(--c-border);justify-content:flex-end;gap:8px">
        <button class="hd-btn hd-btn-outline" style="padding:4px 10px;font-size:12px" :disabled="page <= 1" @click="page--;load()">‹ Anterior</button>
        <span style="font-size:13px;color:var(--c-muted)">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button class="hd-btn hd-btn-outline" style="padding:4px 10px;font-size:12px" :disabled="page >= Math.ceil(total / pageSize)" @click="page++;load()">Próxima ›</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getTickets, getCategories, adminUpdateTicket, adminBulkUpdateTickets, syncMailReplies } from '../../api/tickets'
import { getSchools } from '../../api/tickets'
import { getUsers } from '../../api/users'
import AvatarCircle from '../../components/AvatarCircle.vue'
import PriorityBadge from '../../components/PriorityBadge.vue'

const tickets = ref<any[]>([])
const categories = ref<any[]>([])
const schools = ref<any[]>([])
const staffUsers = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 25
const selectedIds = ref<number[]>([])
const bulkStatus = ref('')
const bulkAssignee = ref('')
const bulkPriority = ref('')
const mailSyncMessage = ref('')

const filterStatus = ref('')
const filterCat = ref<number | ''>('')
const filterPriority = ref('')
const filterSchool = ref<number | ''>('')

const statusOpts = [
  { v: 'open', l: 'Aberto' }, { v: 'assigned', l: 'Atribuído' },
  { v: 'in_progress', l: 'Em Curso' }, { v: 'resolved', l: 'Resolvido' }, { v: 'closed', l: 'Fechado' },
]

const allVisibleSelected = computed(() => tickets.value.length > 0 && tickets.value.every(t => selectedIds.value.includes(t.id)))

onMounted(async () => {
  const [cats, schs, users] = await Promise.all([getCategories(), getSchools(), getUsers()])
  categories.value = cats
  schools.value = schs
  staffUsers.value = users.filter((u: any) => u.is_active && (u.role === 'technician' || u.role === 'admin'))
  await load()
})

async function load() {
  loading.value = true
  try {
    const p: any = { page: page.value, size: pageSize, admin: true }
    if (filterStatus.value) p.status = filterStatus.value
    if (filterCat.value) p.category_id = filterCat.value
    if (filterPriority.value) p.priority = filterPriority.value
    if (filterSchool.value) p.school_id = filterSchool.value
    const d = await getTickets(p)
    tickets.value = d.items
    total.value = d.total
    selectedIds.value = selectedIds.value.filter(id => tickets.value.some(t => t.id === id))
  } finally { loading.value = false }
}

async function changeStatus(ticket: any, status: string) {
  try {
    const updated = await adminUpdateTicket(ticket.id, { status })
    const idx = tickets.value.findIndex(t => t.id === ticket.id)
    if (idx !== -1) tickets.value[idx] = { ...tickets.value[idx], ...updated }
  } catch { await load() }
}

async function changeAssignee(ticket: any, val: string) {
  const assignee_id = val ? Number(val) : null
  try {
    const updated = await adminUpdateTicket(ticket.id, { assignee_id })
    const idx = tickets.value.findIndex(t => t.id === ticket.id)
    if (idx !== -1) tickets.value[idx] = { ...tickets.value[idx], ...updated }
  } catch { await load() }
}

function toggleSelected(id: number) {
  selectedIds.value = selectedIds.value.includes(id) ? selectedIds.value.filter(i => i !== id) : [...selectedIds.value, id]
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
  await applyBulk({ assignee_id: bulkAssignee.value === 'none' ? null : Number(bulkAssignee.value) })
  bulkAssignee.value = ''
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

async function syncReplies() {
  mailSyncMessage.value = 'A ler respostas de email...'
  try {
    const result = await syncMailReplies()
    mailSyncMessage.value = `Respostas lidas: ${result.processed} adicionada(s), ${result.skipped} ignorada(s).`
    await load()
  } catch {
    mailSyncMessage.value = 'Não foi possível ler respostas de email. Verifica a configuração IMAP.'
  }
}

function timeAgo(d: string) {
  const h = Math.floor((Date.now() - new Date(d).getTime()) / 3600000)
  if (h < 1) return 'agora'
  if (h < 24) return `há ${h}h`
  return `há ${Math.floor(h / 24)} d`
}
</script>

<style scoped>
.bulk-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-bg);
}
.bulk-bar .hd-select {
  width: auto;
}
@media (max-width: 820px) {
  .bulk-bar {
    display: grid;
    grid-template-columns: 1fr;
  }
  .bulk-bar .hd-select {
    width: 100%;
  }
}
</style>
