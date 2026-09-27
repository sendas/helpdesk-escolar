<template>
  <div class="hd-page">
    <div class="hd-row" style="margin-bottom:20px;justify-content:flex-end">
      <router-link to="/tickets/new">
        <button class="hd-btn hd-btn-primary"><span class="material-icons" style="font-size:16px">add</span> Novo ticket</button>
      </router-link>
    </div>

    <div class="hd-card">
      <div class="list-toolbar">
        <input class="hd-input list-search" v-model="searchQuery" placeholder="Pesquisar tickets..." @input="debouncedLoad" />
        <select class="hd-select list-filter" v-model="filterStatus" @change="load">
          <option value="">Todos os estados</option>
          <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
          <template v-if="auth.isStaff">
            <option value="a_expirar">A expirar (prazo quase a terminar)</option>
            <option value="fora_prazo">Fora do prazo</option>
          </template>
        </select>
        <select class="hd-select list-filter" v-model="filterCat" @change="load">
          <option value="">Todas as categorias</option>
          <option v-for="c in visibleCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <button class="unread-filter" :class="{ on: onlyUnread }" type="button" @click="onlyUnread = !onlyUnread" title="Mostrar só os tickets com novidades">
          <span class="unread-dot on"></span>
          {{ unreadCount ? `${unreadCount} não lido${unreadCount === 1 ? '' : 's'}` : 'Tudo lido' }}
        </button>
        <button v-if="unreadCount" class="hd-btn hd-btn-outline mark-all" type="button" @click="markAllRead">
          <span class="material-icons">done_all</span> Marcar todos como lidos
        </button>
        <div class="list-toolbar-end">
          <CategoryFilterButton :categories="categories" @changed="onHiddenChanged" />
        </div>
      </div>

      <div v-if="loading" style="padding:48px;text-align:center;color:var(--c-muted)">A carregar...</div>
      <template v-else>
        <div class="tcards">
          <TicketCard v-for="t in activeTickets" :key="'c' + t.id" :ticket="t" />
          <div v-if="!activeTickets.length" class="tcards-empty">{{ onlyUnread ? 'Não há tickets por ler.' : searchQuery.trim() ? `Nenhum ticket encontrado para "${searchQuery.trim()}".` : 'Sem tickets em aberto.' }}</div>
        </div>
        <table class="hd-table list-table">
          <thead>
            <tr><th>ID</th><th>ASSUNTO</th><th>ESTADO</th><th>PRIORIDADE</th><th>SOLICITANTE</th><th>ESCOLA</th><th>CATEGORIA</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in activeTickets" :key="t.id" :class="{ 'row-auto-closed': isAutoClosed(t), 'row-unread': t.is_unread }" :title="isAutoClosed(t) ? 'Fechado automaticamente via email' : undefined" @click="$router.push(`/tickets/${t.id}`)">
              <td class="cell-id">
                <span class="unread-dot" :class="{ on: t.is_unread }" :title="t.is_unread ? 'Tem novidades que ainda não leu' : ''"></span>
                T-{{ t.id }}
                <ReminderChip :at="t.reminder_at" />
              </td>
              <td class="cell-title">{{ t.title }}</td>
              <td style="white-space:nowrap">
                <div style="display:flex;align-items:center;gap:6px">
                  <span class="hd-status" :class="t.status">{{ statusLabel(t.status) }}</span>
                  <span v-if="t.is_escalated" class="badge-fornecedor" title="Reportado à empresa de apoio">E</span>
                </div>
              </td>
              <td><PriorityBadge :priority="t.priority" /></td>
              <td class="cell-person" :title="t.creator?.display_name">
                <div class="person-box"><PersonName :name="t.creator?.display_name" /></div>
              </td>
              <td class="cell-school" :title="t.school?.name"><span v-if="t.school" class="school-initials">{{ schoolInitials(t.school.name) }}</span><template v-else>—</template></td>
              <td><span class="cat-chip" :title="t.category?.name">{{ t.category?.name }}</span></td>
            </tr>
            <tr v-if="!activeTickets.length">
              <td colspan="7" style="text-align:center;color:var(--c-muted);padding:40px">{{ onlyUnread ? 'Não há tickets por ler.' : searchQuery.trim() ? `Nenhum ticket encontrado para "${searchQuery.trim()}".` : 'Sem tickets em aberto.' }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Completed tickets toggle -->
        <div v-if="completedTickets.length" class="completed-toggle">
          <button class="hd-btn hd-btn-outline completed-toggle-btn" @click="showCompleted = !showCompleted">
            <span class="material-icons">{{ showCompleted ? 'expand_less' : 'expand_more' }}</span>
            {{ showCompleted ? 'Ocultar tickets concluídos' : `Mostrar ${completedTickets.length} ticket${completedTickets.length !== 1 ? 's' : ''} concluído${completedTickets.length !== 1 ? 's' : ''}` }}
          </button>
        </div>

        <div v-if="showCompleted && completedTickets.length" class="tcards">
          <TicketCard v-for="t in completedTickets" :key="'d' + t.id" :ticket="t" done />
        </div>
        <table v-if="showCompleted && completedTickets.length" class="hd-table completed-table list-table">
          <thead>
            <tr><th>ID</th><th>ASSUNTO</th><th>ESTADO</th><th>PRIORIDADE</th><th>SOLICITANTE</th><th>ESCOLA</th><th>CATEGORIA</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in completedTickets" :key="t.id" class="completed-row" :class="{ 'row-auto-closed': isAutoClosed(t), 'row-unread': t.is_unread }" :title="isAutoClosed(t) ? 'Fechado automaticamente via email' : undefined" @click="$router.push(`/tickets/${t.id}`)">
              <td class="cell-id">
                <span class="unread-dot" :class="{ on: t.is_unread }" :title="t.is_unread ? 'Tem novidades que ainda não leu' : ''"></span>
                T-{{ t.id }}
                <ReminderChip :at="t.reminder_at" />
              </td>
              <td class="cell-title">{{ t.title }}</td>
              <td><span class="hd-status" :class="t.status">{{ statusLabel(t.status) }}</span></td>
              <td><PriorityBadge :priority="t.priority" /></td>
              <td class="cell-person" :title="t.creator?.display_name">
                <div class="person-box"><PersonName :name="t.creator?.display_name" /></div>
              </td>
              <td class="cell-school" :title="t.school?.name"><span v-if="t.school" class="school-initials">{{ schoolInitials(t.school.name) }}</span><template v-else>—</template></td>
              <td><span class="cat-chip" :title="t.category?.name">{{ t.category?.name }}</span></td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { getTickets, getCategories, markTicketsRead } from '../api/tickets'
import { onRealtime } from '../services/realtime'
import PriorityBadge from '../components/PriorityBadge.vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import CategoryFilterButton from '../components/CategoryFilterButton.vue'
import PersonName from '../components/PersonName.vue'
import ReminderChip from '../components/ReminderChip.vue'
import TicketCard from '../components/TicketCard.vue'
import { schoolInitials } from '../utils/names'

const route = useRoute()
const auth = useAuthStore()

const tickets = ref<any[]>([])
const categories = ref<any[]>([])
const loading = ref(false)
const filterStatus = ref('')
const filterCat = ref<number | ''>('')
const searchQuery = ref('')
const showCompleted = ref(false)
let _searchTimer: ReturnType<typeof setTimeout> | null = null

const DONE = ['resolved', 'closed']
const onlyUnread = ref(false)
const shown = computed(() => onlyUnread.value ? tickets.value.filter(t => t.is_unread) : tickets.value)
const unreadCount = computed(() => tickets.value.filter(t => t.is_unread).length)
const activeTickets = computed(() =>
  filterStatus.value ? shown.value : shown.value.filter(t => !DONE.includes(t.status))
)
const completedTickets = computed(() =>
  filterStatus.value ? [] : shown.value.filter(t => DONE.includes(t.status))
)

async function markAllRead() {
  const ids = tickets.value.filter(t => t.is_unread).map(t => t.id)
  tickets.value = tickets.value.map(t => ({ ...t, is_unread: false }))
  onlyUnread.value = false
  await markTicketsRead(ids).catch(() => load(true))
}


const STATUS_GROUPS: Record<string, string[]> = {
  em_curso: ['assigned', 'in_progress', 'waiting_user'],
  concluidos: ['resolved', 'closed'],
}

const statusOpts = [
  { v: 'open', l: 'Aberto' },
  { v: 'em_curso', l: 'Em curso (todos)' },
  { v: 'assigned', l: 'Atribuído' },
  { v: 'in_progress', l: 'Em Curso' }, { v: 'waiting_user', l: 'A aguardar utilizador' },
  { v: 'concluidos', l: 'Resolvidos ou fechados' },
  { v: 'resolved', l: 'Resolvido' }, { v: 'closed', l: 'Fechado' },
]

const hiddenIds = computed(() => auth.user?.hidden_category_ids ?? [])
const visibleCategories = computed(() => categories.value.filter(c => !hiddenIds.value.includes(c.id)))

// New replies arrive in real time: refresh the list quietly (at most once per second)
let refreshTimer: ReturnType<typeof setTimeout> | null = null
function refreshSoon() {
  if (refreshTimer) clearTimeout(refreshTimer)
  refreshTimer = setTimeout(() => load(true), 1000)
}
const realtimeOffs = [onRealtime('ticket.changed', refreshSoon), onRealtime('tickets.changed', refreshSoon)]
onBeforeUnmount(() => { realtimeOffs.forEach((off) => off()); if (refreshTimer) clearTimeout(refreshTimer) })

// The search box at the top of every page opens this list with ?q=...
watch(() => route.query.q, (q) => {
  if (q === undefined) return
  searchQuery.value = String(q)
  load()
})

onMounted(async () => {
  if (route.query.q) searchQuery.value = String(route.query.q)
  const q = String(route.query.estado ?? '')
  if (q === 'abertos') filterStatus.value = 'open'
  else if (q === 'em_curso') filterStatus.value = 'em_curso'
  else if (q === 'resolvidos') filterStatus.value = 'concluidos'
  else if (q === 'a_expirar' && auth.isStaff) filterStatus.value = 'a_expirar'
  else if (q === 'fora_prazo' && auth.isStaff) filterStatus.value = 'fora_prazo'
  categories.value = await getCategories()
  await load()
})

function onHiddenChanged() {
  if (filterCat.value && hiddenIds.value.includes(Number(filterCat.value))) filterCat.value = ''
  load()
}

function debouncedLoad() {
  if (_searchTimer) clearTimeout(_searchTimer)
  _searchTimer = setTimeout(load, 350)
}

async function load(quiet = false) {
  if (!quiet) loading.value = true
  try {
    const p: any = { page: 1, size: 50 }
    if (filterStatus.value === 'fora_prazo') p.overdue = true
    else if (filterStatus.value === 'a_expirar') p.expiring = true
    else if (STATUS_GROUPS[filterStatus.value]) p.status_in = STATUS_GROUPS[filterStatus.value]
    else if (filterStatus.value) p.status = filterStatus.value
    if (hiddenIds.value.length) p.exclude_category_ids = hiddenIds.value
    if (filterCat.value) p.category_id = filterCat.value
    if (searchQuery.value.trim()) p.search = searchQuery.value.trim()
    const d = await getTickets(p)
    tickets.value = d.items
  } finally { loading.value = false }
}

function isAutoClosed(t: any) {
  return !!t.closed_via_email && DONE.includes(t.status)
}

function statusLabel(s: string) {
  return { open:'Aberto', assigned:'Atribuído', in_progress:'Em Curso', waiting_user:'A aguardar utilizador', resolved:'Resolvido', closed:'Fechado' }[s] ?? s
}

</script>

<style scoped>
.list-toolbar { display: flex; gap: 10px; padding: 14px 16px; border-bottom: 1px solid var(--c-border); flex-wrap: wrap; align-items: center; }
.list-search { width: 220px; }
.list-filter { width: auto; }
.list-toolbar-end { margin-left: auto; }
/* Wide screens: table. Tablets and phones: cards like an inbox */
.tcards { display: none; }
.tcards-empty { text-align: center; color: var(--c-muted); padding: 32px 12px; }
@media (max-width: 1280px) {
  .list-table { display: none; }
  .tcards { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); gap: 10px; padding: 12px; }
}
@media (max-width: 700px) {
  .list-toolbar { display: grid; grid-template-columns: 1fr 1fr; padding: 12px; }
  .list-search { width: 100%; grid-column: 1 / -1; }
  .list-filter { width: 100%; min-width: 0; }
  .list-toolbar-end { margin-left: 0; grid-column: 1 / -1; display: flex; justify-content: flex-end; }
  .unread-filter, .mark-all { justify-content: center; }
}
.cell-id { color: var(--c-muted); font-size: 12px; white-space: nowrap; }
.unread-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; background: transparent; }
.unread-dot.on { background: #2563EB; box-shadow: 0 0 0 3px rgba(37, 99, 235, .18); }
.row-unread td { background: rgba(37, 99, 235, .045); }
.row-unread .cell-title { font-weight: 800; color: var(--c-text); }
.row-unread .cell-id { color: var(--c-text); font-weight: 700; }
.dark .row-unread td { background: rgba(96, 165, 250, .08); }
.unread-filter { display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-text); font-size: 12.5px; font-weight: 700; cursor: pointer; }
.unread-filter.on { border-color: #2563EB; background: rgba(37, 99, 235, .1); color: #1D4ED8; }
.dark .unread-filter.on { color: #93C5FD; }
.mark-all { font-size: 12.5px; padding: 6px 12px; }
.mark-all .material-icons { font-size: 16px; }
.cell-title { font-weight: 500; min-width: 220px; color: var(--c-muted-strong, var(--c-text)); }
.cell-person { white-space: nowrap; }
.person-box { max-width: clamp(170px, 26vw, 520px); min-width: 0; }
.cell-school { white-space: nowrap; }
.school-initials { display: inline-block; min-width: 34px; text-align: center; font-size: 12px; font-weight: 800; letter-spacing: .04em; color: #0E7490; background: #CFFAFE; border: 1px solid #A5F3FC; border-radius: 8px; padding: 2px 7px; }
.dark .school-initials { color: #A5F3FC; background: rgba(8, 145, 178, .2); border-color: rgba(34, 211, 238, .35); }
.group-tag {
  display: inline-block; margin-left: 6px; font-size: 10.5px; font-weight: 700; color: var(--c-muted);
  border: 1px solid var(--c-border); border-radius: 6px; padding: 0 6px; line-height: 17px; vertical-align: 1px;
}
.cat-chip {
  display: inline-block; font-size: 12px; font-weight: 600; color: var(--c-primary);
  background: rgba(64, 87, 216, .08); border-radius: 999px; padding: 3px 10px; white-space: nowrap;
  max-width: 150px; overflow: hidden; text-overflow: ellipsis; vertical-align: middle;
}
.dark .cat-chip { background: rgba(99, 125, 255, .16); color: #A5B4FC; }
.badge-fornecedor {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #EA580C;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  flex-shrink: 0;
  cursor: default;
}


.completed-toggle {
  padding: 12px 16px;
  border-top: 1px solid var(--c-border);
}
.completed-toggle-btn {
  font-size: 13px;
  gap: 4px;
  color: var(--c-muted);
}
.completed-table { opacity: 0.72; }
.completed-row { cursor: pointer; }
.completed-row:hover { opacity: 1; }
</style>
