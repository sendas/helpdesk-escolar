<template>
  <div class="hd-page">
    <div class="hd-row" style="margin-bottom:20px;justify-content:flex-end">
      <router-link to="/tickets/new">
        <button class="hd-btn hd-btn-primary"><span class="material-icons" style="font-size:16px">add</span> Novo ticket</button>
      </router-link>
    </div>

    <div class="hd-card">
      <div style="display:flex;gap:10px;padding:14px 16px;border-bottom:1px solid var(--c-border);flex-wrap:wrap">
        <input class="hd-input" style="width:220px" v-model="searchQuery" placeholder="Pesquisar tickets..." @input="debouncedLoad" />
        <select class="hd-select" style="width:auto" v-model="filterStatus" @change="load">
          <option value="">Todos os estados</option>
          <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
          <template v-if="auth.isStaff">
            <option value="a_expirar">A expirar (prazo quase a terminar)</option>
            <option value="fora_prazo">Fora do prazo</option>
          </template>
        </select>
        <select class="hd-select" style="width:auto" v-model="filterCat" @change="load">
          <option value="">Todas as categorias</option>
          <option v-for="c in visibleCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <div style="margin-left:auto">
          <CategoryFilterButton :categories="categories" @changed="onHiddenChanged" />
        </div>
      </div>

      <div v-if="loading" style="padding:48px;text-align:center;color:var(--c-muted)">A carregar...</div>
      <template v-else>
        <table class="hd-table">
          <thead>
            <tr><th>ID</th><th>ASSUNTO</th><th>ESTADO</th><th>PRIORIDADE</th><th>SOLICITANTE</th><th>CATEGORIA</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in activeTickets" :key="t.id" :class="{ 'row-auto-closed': isAutoClosed(t) }" :title="isAutoClosed(t) ? 'Fechado automaticamente via email' : undefined" @click="$router.push(`/tickets/${t.id}`)">
              <td style="color:var(--c-muted);font-size:12px;white-space:nowrap">
                T-{{ t.id }}
                <span v-if="t.has_reminder" class="material-icons reminder-flag" title="Tem um lembrete seu por enviar">alarm</span>
              </td>
              <td class="cell-title">{{ t.title }}</td>
              <td style="white-space:nowrap">
                <div style="display:flex;align-items:center;gap:6px">
                  <span class="hd-status" :class="t.status">{{ statusLabel(t.status) }}</span>
                  <span v-if="t.is_escalated" class="badge-fornecedor" title="Reportado à empresa de apoio">E</span>
                </div>
              </td>
              <td><PriorityBadge :priority="t.priority" /></td>
              <td class="cell-person" :title="t.creator?.display_name">{{ shortName(t.creator?.display_name) }}</td>
              <td><span class="cat-chip" :title="t.category?.name">{{ t.category?.name }}</span></td>
            </tr>
            <tr v-if="!activeTickets.length">
              <td colspan="6" style="text-align:center;color:var(--c-muted);padding:40px">Sem tickets em aberto.</td>
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

        <table v-if="showCompleted && completedTickets.length" class="hd-table completed-table">
          <thead>
            <tr><th>ID</th><th>ASSUNTO</th><th>ESTADO</th><th>PRIORIDADE</th><th>SOLICITANTE</th><th>CATEGORIA</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in completedTickets" :key="t.id" class="completed-row" :class="{ 'row-auto-closed': isAutoClosed(t) }" :title="isAutoClosed(t) ? 'Fechado automaticamente via email' : undefined" @click="$router.push(`/tickets/${t.id}`)">
              <td style="color:var(--c-muted);font-size:12px;white-space:nowrap">
                T-{{ t.id }}
                <span v-if="t.has_reminder" class="material-icons reminder-flag" title="Tem um lembrete seu por enviar">alarm</span>
              </td>
              <td class="cell-title">{{ t.title }}</td>
              <td><span class="hd-status" :class="t.status">{{ statusLabel(t.status) }}</span></td>
              <td><PriorityBadge :priority="t.priority" /></td>
              <td class="cell-person" :title="t.creator?.display_name">{{ shortName(t.creator?.display_name) }}</td>
              <td><span class="cat-chip" :title="t.category?.name">{{ t.category?.name }}</span></td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getTickets, getCategories } from '../api/tickets'
import PriorityBadge from '../components/PriorityBadge.vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import CategoryFilterButton from '../components/CategoryFilterButton.vue'
import { shortName } from '../utils/names'

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
const activeTickets = computed(() =>
  filterStatus.value ? tickets.value : tickets.value.filter(t => !DONE.includes(t.status))
)
const completedTickets = computed(() =>
  filterStatus.value ? [] : tickets.value.filter(t => DONE.includes(t.status))
)

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

onMounted(async () => {
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

async function load() {
  loading.value = true
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
.reminder-flag { font-size: 15px; color: #D97706; vertical-align: -3px; margin-left: 4px; }
.dark .reminder-flag { color: #FCD34D; }
.cell-title { font-weight: 500; min-width: 220px; }
.cell-person { white-space: nowrap; max-width: 170px; overflow: hidden; text-overflow: ellipsis; }
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
