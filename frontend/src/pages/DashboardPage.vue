<template>
  <div class="hd-page dash-page">
    <h1 class="dash-greeting">Olá, {{ auth.user?.display_name?.split(' ')[0] }}</h1>

    <!-- Stat cards -->
    <div class="stat-grid">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <div class="stat-card-top">
          <div class="stat-label">{{ s.label }}</div>
          <div class="stat-icon-wrap">
            <span class="material-icons">{{ s.icon }}</span>
          </div>
        </div>
        <div class="stat-value">{{ s.count }}</div>
        <div class="stat-sub">{{ s.sub }}</div>
      </div>
    </div>

    <div class="dash-body">
      <!-- Recent tickets -->
      <div class="hd-card">
        <div class="dash-section-head">
          <div>
            <div style="font-weight:600;font-size:14px">Os meus tickets recentes</div>
            <div style="font-size:12px;color:var(--c-muted)">Últimos pedidos submetidos</div>
          </div>
          <router-link to="/tickets" class="dash-ver-todos">Ver todos</router-link>
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
import { timeAgo } from '../utils/dates'

const auth = useAuthStore()
const tickets = ref<any[]>([])
const categories = ref<any[]>([])

onMounted(async () => {
  const [td, cd] = await Promise.all([getTickets({ page: 1, size: 20 }), getCategories()])
  tickets.value = td.items
  categories.value = cd.slice(0, 5)
})

const recent = computed(() => tickets.value.slice(0, 5))

const stats = computed(() => [
  { label: 'Tickets Abertos', count: tickets.value.filter(t => t.status === 'open').length, icon: 'inbox', sub: 'em aberto' },
  { label: 'Em Análise', count: tickets.value.filter(t => ['assigned','in_progress','waiting_user'].includes(t.status)).length, icon: 'schedule', sub: 'em curso' },
  { label: 'Resolvidos', count: tickets.value.filter(t => t.status === 'resolved').length, icon: 'check_circle', sub: 'resolvidos' },
  { label: 'Tempo Médio', count: '—', icon: 'bar_chart', sub: 'até resposta' },
])

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

/* ── Stat grid: 2×2 on mobile, 4×1 on desktop ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 14px;
  padding: 16px;
}

.stat-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.stat-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .05em;
  text-transform: uppercase;
  color: var(--c-muted);
  line-height: 1.3;
}

.stat-icon-wrap {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--c-primary-soft, rgba(61,82,213,.12));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-wrap .material-icons {
  font-size: 18px;
  color: var(--c-primary);
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  color: var(--c-text);
  margin-bottom: 4px;
}

.stat-sub {
  font-size: 12px;
  color: var(--c-muted);
}

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

/* ── Desktop layout ── */
@media (min-width: 768px) {
  .dash-greeting {
    font-size: 26px;
    margin-bottom: 24px;
  }

  .stat-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }

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

  /* Switch to table on desktop */
  .ticket-list-mobile {
    display: none;
  }

  .ticket-table-desktop {
    display: table;
  }
}
</style>
