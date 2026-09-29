<template>
  <div class="hd-page board-page">
    <div class="board-toolbar">
      <input v-model="search" class="hd-input board-search" placeholder="Filtrar por assunto, nº ou pessoa…" />
      <select v-model="schoolId" class="hd-select board-filter" @change="load">
        <option value="">Todas as escolas</option>
        <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
      <label class="board-mine">
        <input v-model="onlyMine" type="checkbox" @change="load" /> Só os meus
      </label>
      <span v-if="!canMove" class="board-note">Só leitura — o seu papel não permite mudar o estado.</span>
      <span v-else class="board-note">Tickets em aberto por estado. Arraste um cartão para outra coluna para mudar o estado.</span>
    </div>

    <div v-if="loading" class="board-empty">A carregar…</div>
    <div v-else class="board">
      <section
        v-for="col in columns"
        :key="col.status"
        class="board-col"
        :class="{ over: overCol === col.status }"
        :style="{ '--col-color': statusColor(col.status) }"
        @dragover.prevent="canMove && (overCol = col.status)"
        @dragleave="overCol = ''"
        @drop.prevent="onDrop(col.status)"
      >
        <header class="board-col-head">
          <span class="board-col-dot"></span>
          <span>{{ col.label }}</span>
          <span class="board-count">{{ visible(col.status).length }}</span>
        </header>
        <div class="board-cards">
          <article
            v-for="t in visible(col.status)"
            :key="t.id"
            class="board-card"
            :class="{ unread: t.is_unread, dragging: draggingId === t.id }"
            :draggable="canMove"
            @dragstart="onDragStart(t)"
            @dragend="draggingId = 0; overCol = ''"
            @click="$router.push(`/tickets/${t.id}`)"
          >
            <div class="board-card-top">
              <span class="board-id">T-{{ t.id }}</span>
              <span v-if="t.school" class="board-school" :title="t.school.name">{{ schoolInitials(t.school.name) }}</span>
              <PriorityBadge :priority="t.priority" />
              <select
                v-if="canMove"
                class="board-move"
                :value="t.status"
                title="Mudar estado"
                aria-label="Mudar estado"
                @click.stop
                @change="move(t, ($event.target as HTMLSelectElement).value)"
              >
                <option v-for="c in columns" :key="c.status" :value="c.status">{{ c.label }}</option>
                <option value="closed">Fechado</option>
              </select>
            </div>
            <div class="board-title">{{ t.title }}</div>
            <div class="board-meta">
              <span class="board-cat">{{ t.category?.name }}</span>
              <span>· {{ timeAgo(t.updated_at) }}</span>
            </div>
            <div class="board-people">
              <PersonName class="board-requester" :name="t.creator?.display_name" />
              <span class="board-assignees">
                <AvatarCircle v-for="a in (t.assignees?.length ? t.assignees : t.assignee ? [t.assignee] : []).slice(0, 3)"
                              :key="a.id" :name="shortName(a.display_name)" size="22" :title="a.display_name" />
              </span>
            </div>
          </article>
          <div v-if="!visible(col.status).length" class="board-col-empty">Sem tickets</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
// Quadro (Kanban): open tickets by state; drag a card to change its state
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { adminUpdateTicket, getSchools, getTickets } from '../../api/tickets'
import AvatarCircle from '../../components/AvatarCircle.vue'
import PersonName from '../../components/PersonName.vue'
import PriorityBadge from '../../components/PriorityBadge.vue'
import { onRealtime } from '../../services/realtime'
import { useAuthStore } from '../../stores/auth'
import { timeAgo } from '../../utils/dates'
import { notifyError } from '../../utils/feedback'
import { schoolInitials, shortName } from '../../utils/names'
import { statusColor, statusLabel } from '../../utils/ticketStatus'

const auth = useAuthStore()
const canMove = computed(() => auth.isStaff)
const columns = ['open', 'assigned', 'in_progress', 'waiting_user', 'resolved'].map((status) => ({ status, label: statusLabel(status, true) }))
const tickets = ref<any[]>([])
const schools = ref<any[]>([])
const loading = ref(true)
const search = ref('')
const schoolId = ref<number | ''>('')
const onlyMine = ref(false)
const draggingId = ref(0)
const overCol = ref('')

function visible(status: string) {
  const q = search.value.trim().toLowerCase().replace(/^t-/, '')
  return tickets.value.filter((t) => t.status === status && (!q
    || String(t.id) === q
    || String(t.title).toLowerCase().includes(q)
    || String(t.creator?.display_name ?? '').toLowerCase().includes(q)))
}

async function load() {
  try {
    const params: any = { admin: true, size: 100 }
    if (schoolId.value) params.school_id = schoolId.value
    if (onlyMine.value && auth.user) params.assignee_id = auth.user.id
    const pages = await Promise.all(columns.map((c) => getTickets({ ...params, status: c.status })))
    tickets.value = pages.flatMap((p) => p.items)
  } catch (e) {
    notifyError(e, 'Não foi possível carregar o quadro.')
  } finally {
    loading.value = false
  }
}

function onDragStart(t: any) {
  draggingId.value = t.id
}

function onDrop(status: string) {
  const t = tickets.value.find((x) => x.id === draggingId.value)
  overCol.value = ''
  draggingId.value = 0
  if (t) move(t, status)
}

async function move(t: any, status: string) {
  if (!canMove.value || t.status === status) return
  const previous = t.status
  t.status = status
  try {
    await adminUpdateTicket(t.id, { status })
    if (status === 'closed') tickets.value = tickets.value.filter((x) => x.id !== t.id)
  } catch (e) {
    t.status = previous
    notifyError(e, 'Não foi possível mudar o estado.')
  }
}

let refreshTimer: ReturnType<typeof setTimeout> | null = null
function refreshSoon() {
  if (refreshTimer) clearTimeout(refreshTimer)
  refreshTimer = setTimeout(load, 1200)
}
const offs = [onRealtime('tickets.changed', refreshSoon), onRealtime('ticket.changed', refreshSoon),
  onRealtime('realtime.connected', (e) => { if (e.resumed) refreshSoon() })]
onBeforeUnmount(() => { offs.forEach((off) => off()); if (refreshTimer) clearTimeout(refreshTimer) })

onMounted(async () => {
  getSchools().then((s) => { schools.value = s }).catch(() => {})
  await load()
})
</script>

<style scoped>
.board-page { max-width: none; }
.board-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }
.board-search { width: 260px; }
.board-filter { width: auto; }
.board-mine { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: var(--c-text); }
.board-note { margin-left: auto; font-size: 12.5px; color: var(--c-muted); }
.board-empty { padding: 60px; text-align: center; color: var(--c-muted); }
/* The 5 columns share the width (they only scroll sideways on narrow screens) */
.board { display: grid; grid-template-columns: repeat(5, minmax(150px, 1fr)); gap: 10px; overflow-x: auto; padding-bottom: 12px; align-items: start; }
@media (max-width: 900px) { .board { grid-template-columns: repeat(5, minmax(220px, 1fr)); scroll-snap-type: x mandatory; } .board-col { scroll-snap-align: start; } }
.board-col { background: var(--c-surface-soft); border: 1px solid var(--c-border); border-top: 3px solid var(--col-color); border-radius: 14px; min-height: 200px; display: flex; flex-direction: column; max-height: calc(100vh - 200px); }
.board-col.over { background: color-mix(in srgb, var(--col-color) 10%, var(--c-surface)); border-color: var(--col-color); }
.board-col-head { display: flex; align-items: center; gap: 6px; padding: 10px 10px; font-weight: 800; font-size: 12.5px; color: var(--c-text); white-space: nowrap; min-width: 0; }
.board-col-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--col-color); }
.board-count { margin-left: auto; font-size: 11.5px; font-weight: 700; color: var(--col-color); background: color-mix(in srgb, var(--col-color) 14%, transparent); border-radius: 999px; padding: 1px 8px; }
.board-cards { display: flex; flex-direction: column; gap: 6px; padding: 0 6px 8px; overflow-y: auto; }
.board-card { background: var(--c-surface); border: 1px solid var(--c-border); border-left: 3px solid var(--col-color); border-radius: 10px; padding: 8px 9px; cursor: pointer; box-shadow: var(--shadow-sm); min-width: 0; }
.board-card[draggable="true"] { cursor: grab; }
.board-card:hover { border-color: var(--col-color); }
.board-card.dragging { opacity: .45; }
.board-card.unread .board-title { font-weight: 800; }
.board-card-top { display: flex; align-items: center; gap: 5px; font-size: 11.5px; color: var(--c-muted); flex-wrap: wrap; }
.board-card-top :deep(.priority-badge), .board-card-top > * { white-space: nowrap; }
.board-id { font-weight: 700; white-space: nowrap; }
.board-school { font-size: 10.5px; font-weight: 800; color: #0E7490; background: #CFFAFE; border-radius: 6px; padding: 0 5px; }
.dark .board-school { color: #A5F3FC; background: rgba(8, 145, 178, .2); }
.board-move { margin-left: auto; border: 1px solid transparent; background: transparent; color: var(--c-muted); border-radius: 6px; font-size: 11px; padding: 1px 0; max-width: 22px; cursor: pointer; }
.board-move:hover, .board-move:focus { border-color: var(--c-border); background: var(--c-surface); max-width: 110px; }
.board-title { font-size: 13px; font-weight: 600; color: var(--c-text); margin: 5px 0 3px; line-height: 1.3; overflow-wrap: anywhere; }
.board-meta { font-size: 11px; color: var(--c-muted); display: flex; gap: 4px; flex-wrap: wrap; }
.board-cat { color: var(--c-primary); font-weight: 600; }
.board-people { display: flex; align-items: center; gap: 6px; margin-top: 6px; font-size: 11.5px; color: var(--c-muted); min-width: 0; }
.board-requester { min-width: 0; flex: 1; }
.board-assignees { display: inline-flex; gap: 2px; }
.board-col-empty { text-align: center; color: var(--c-muted); font-size: 12.5px; padding: 18px 0; }
</style>
