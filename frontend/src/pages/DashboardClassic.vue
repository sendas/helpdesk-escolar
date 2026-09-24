<template>
  <div class="hd-page dash-page">
    <h1 class="dash-greeting">Olá, {{ auth.user?.display_name?.split(' ')[0] }}</h1>

    <!-- Stat cards -->
    <div class="stat-grid" :class="auth.isStaff ? 'cols-5' : 'cols-3'">
      <component :is="s.to ? 'router-link' : 'div'" :to="s.to" :title="s.sub" class="stat-card" :class="{ clickable: !!s.to, warn: s.warn && Number(s.count) > 0 }" v-for="s in stats" :key="s.label">
        <div class="stat-icon-wrap">
          <span class="material-icons">{{ s.icon }}</span>
        </div>
        <div style="min-width:0">
          <div class="stat-value">{{ s.count }}</div>
          <div class="stat-label">{{ s.label }}</div>
        </div>
      </component>
    </div>

    <div class="dash-body">
      <!-- Recent tickets -->
      <div class="hd-card">
        <div class="dash-section-head">
          <div>
            <div style="font-weight:600;font-size:14px">Os meus tickets recentes</div>
            <div style="font-size:12px;color:var(--c-muted)">Últimos pedidos submetidos</div>
          </div>
          <div style="display:flex;align-items:center;gap:10px">
            <CategoryFilterButton :categories="allCategories" @changed="load" />
            <router-link to="/tickets" class="dash-ver-todos">Ver todos</router-link>
          </div>
        </div>

        <!-- Mobile: card list -->
        <div class="ticket-list-mobile">
          <div
            v-for="t in recent" :key="t.id"
            class="ticket-row-card"
            @click="$router.push(`/tickets/${t.id}`)"
          >
            <div class="ticket-row-main">
              <span class="ticket-row-id">T-{{ t.id }}</span>
              <span class="ticket-row-title">{{ t.title }}</span>
            </div>
            <div class="ticket-row-meta">
              <span class="hd-status" :class="t.status">{{ statusLabel(t.status) }}</span>
              <PriorityBadge :priority="t.priority" />
              <span class="ticket-row-time">{{ timeAgo(t.updated_at) }}</span>
            </div>
          </div>
          <div v-if="!recent.length" class="ticket-empty">Nenhum ticket criado ainda.</div>
        </div>

        <!-- Desktop: table -->
        <table class="hd-table ticket-table-desktop">
          <thead>
            <tr><th>ID</th><th>ASSUNTO</th><th>ESTADO</th><th>PRIORIDADE</th><th>ATUALIZADO</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in recent" :key="t.id" @click="$router.push(`/tickets/${t.id}`)">
              <td style="color:var(--c-muted);font-size:12px">T-{{ t.id }}</td>
              <td style="font-weight:500">{{ t.title }}</td>
              <td><span class="hd-status" :class="t.status">{{ statusLabel(t.status) }}</span></td>
              <td><PriorityBadge :priority="t.priority" /></td>
              <td style="color:var(--c-muted)">{{ timeAgo(t.updated_at) }}</td>
            </tr>
            <tr v-if="!recent.length">
              <td colspan="5" style="text-align:center;color:var(--c-muted);padding:32px">Nenhum ticket criado ainda.</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Categories -->
      <div class="hd-card cat-panel">
        <div style="font-weight:600;font-size:14px;margin-bottom:4px">Novo pedido rápido</div>
        <div style="font-size:12px;color:var(--c-muted);margin-bottom:14px">Escolha a área do seu problema</div>
        <div class="cat-list">
          <div
            v-for="cat in categories" :key="cat.id"
            class="hd-sel-card cat-item"
            @click="$router.push('/tickets/new')"
          >
            <div class="hd-sel-icon" :style="{ background: cat.color + '22' }">
              <span class="material-icons" :style="{ color: cat.color, fontSize: '16px' }">{{ cat.icon }}</span>
            </div>
            <div style="flex:1;min-width:0">
              <div class="hd-sel-title" style="font-size:12.5px">{{ cat.name }}</div>
              <div style="font-size:11px;color:var(--c-muted)">Resposta: {{ cat.sla_hours }}h</div>
            </div>
            <span class="material-icons" style="font-size:14px;color:var(--c-muted)">chevron_right</span>
          </div>
        </div>
        <router-link to="/tickets/new" class="dash-new-ticket-btn">
          <span class="material-icons" style="font-size:16px">add_circle</span>
          Novo pedido
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getTickets, getCategories } from '../api/tickets'
import { useAuthStore } from '../stores/auth'
import PriorityBadge from '../components/PriorityBadge.vue'
import CategoryFilterButton from '../components/CategoryFilterButton.vue'
import { timeAgo } from '../utils/dates'

const auth = useAuthStore()
const tickets = ref<any[]>([])
const allCategories = ref<any[]>([])

const hiddenIds = computed(() => auth.user?.hidden_category_ids ?? [])
const categories = computed(() => allCategories.value.filter(c => !hiddenIds.value.includes(c.id)).slice(0, 5))

async function load() {
  const [td] = await Promise.all([
    getTickets({ page: 1, size: 50, exclude_category_ids: hiddenIds.value }),
    loadSlaCounts(),
  ])
  tickets.value = td.items
}

onMounted(async () => {
  const [, cd] = await Promise.all([load(), getCategories()])
  allCategories.value = cd
})

const recent = computed(() => tickets.value.slice(0, 5))

const expiringCount = ref<number | null>(null)
const overdueCount = ref<number | null>(null)

async function loadSlaCounts() {
  if (!auth.isStaff) return
  const base = { page: 1, size: 1, exclude_category_ids: hiddenIds.value }
  const [exp, over] = await Promise.all([getTickets({ ...base, expiring: true }), getTickets({ ...base, overdue: true })])
  expiringCount.value = exp.total
  overdueCount.value = over.total
}

const stats = computed(() => {
  const list = [
    { label: 'Tickets Abertos', count: tickets.value.filter(t => t.status === 'open').length, icon: 'inbox', sub: 'em aberto', to: '/tickets?estado=abertos', warn: false },
    { label: 'Em Análise', count: tickets.value.filter(t => ['assigned','in_progress','waiting_user'].includes(t.status)).length, icon: 'schedule', sub: 'em curso', to: '/tickets?estado=em_curso', warn: false },
    { label: 'Resolvidos', count: tickets.value.filter(t => t.status === 'resolved' || t.status === 'closed').length, icon: 'check_circle', sub: 'resolvidos ou fechados', to: '/tickets?estado=resolvidos', warn: false },
  ]
  if (auth.isStaff) {
    list.push(
      { label: 'A Expirar', count: expiringCount.value ?? '—' as any, icon: 'hourglass_bottom', sub: 'prazo quase a terminar', to: '/tickets?estado=a_expirar', warn: false },
      { label: 'Fora do Prazo', count: overdueCount.value ?? '—' as any, icon: 'alarm', sub: 'tempo de resposta ultrapassado', to: '/tickets?estado=fora_prazo', warn: true },
    )
  }
  return list
})

function statusLabel(s: string) {
  return { open: 'Aberto', assigned: 'Atribuído', in_progress: 'Em Curso', waiting_user: 'A aguardar', resolved: 'Resolvido', closed: 'Fechado' }[s] ?? s
}
</script>

<style scoped>
/* ── Greeting ── */
.dash-greeting {
  font-size: 22px;
  margin-bottom: 20px;
}

/* ── Stat grid: one compact row (scrolls sideways on narrow screens) ── */
.stat-grid {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(138px, 1fr);
  gap: 10px;
  margin-bottom: 20px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 12px;
  text-decoration: none;
  color: inherit;
  transition: border-color .15s, transform .15s;
}
.stat-card.warn { border-color: #FCA5A5; }
.stat-card.warn .stat-value { color: #DC2626; }
.stat-card.clickable:hover { border-color: var(--c-primary); transform: translateY(-2px); }

.stat-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--c-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: var(--c-primary-soft, rgba(61,82,213,.12));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon-wrap .material-icons { font-size: 18px; color: var(--c-primary); }

.stat-value { font-size: 20px; font-weight: 700; line-height: 1.05; color: var(--c-text); }

/* ── Body: stacked on mobile, side-by-side on desktop ── */
.dash-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dash-section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border);
}

.dash-ver-todos {
  font-size: 13px;
  color: var(--c-primary);
  text-decoration: none;
  font-weight: 500;
  white-space: nowrap;
  margin-left: 12px;
}

/* ── Mobile ticket list ── */
.ticket-list-mobile {
  display: flex;
  flex-direction: column;
}

.ticket-table-desktop {
  display: none;
}

.ticket-row-card {
  padding: 12px 16px;
  border-bottom: 1px solid var(--c-border);
  cursor: pointer;
  transition: background .12s;
}

.ticket-row-card:last-child {
  border-bottom: none;
}

.ticket-row-card:hover {
  background: var(--c-hover);
}

.ticket-row-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
  min-width: 0;
}

.ticket-row-id {
  font-size: 11px;
  color: var(--c-muted);
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
}

.ticket-row-title {
  font-size: 13.5px;
  font-weight: 500;
  color: var(--c-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ticket-row-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.ticket-row-time {
  font-size: 11px;
  color: var(--c-muted);
  margin-left: auto;
}

.ticket-empty {
  padding: 32px;
  text-align: center;
  color: var(--c-muted);
  font-size: 13px;
}

/* ── Categories panel ── */
.cat-panel {
  padding: 20px;
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.cat-item {
  padding: 10px 12px;
}

.dash-new-ticket-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 10px;
  background: var(--c-primary);
  color: #fff;
  border-radius: 10px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: opacity .15s;
}

.dash-new-ticket-btn:hover {
  opacity: .88;
}

/* ── Tablet (≥820px): desktop table + larger greeting; stats ficam 2×2 ── */
@media (min-width: 820px) {
  .dash-greeting {
    font-size: 26px;
    margin-bottom: 24px;
  }

  .ticket-list-mobile {
    display: none;
  }

  .ticket-table-desktop {
    display: table;
  }
}

/* ── Desktop largo (≥1400px): layout lado a lado com painel categorias ── */
@media (min-width: 1400px) {
  .dash-body {
    flex-direction: row;
    align-items: flex-start;
    gap: 20px;
  }

  .dash-body > .hd-card:first-child {
    flex: 1;
    min-width: 0;
  }

  .cat-panel {
    width: 280px;
    flex-shrink: 0;
  }
}

@media (max-width: 560px) {
  .stat-grid { grid-auto-columns: minmax(92px, 1fr); gap: 8px; }
  .stat-card { padding: 9px 10px; }
  .stat-label { white-space: normal; font-size: 11px; line-height: 1.2; }
  .stat-card .stat-icon-wrap { display: none; }
}
</style>
