<template>
  <div class="hd-page">
    <div class="report-bar">
      <label>Relatório mensal
        <input v-model="reportMonth" type="month" class="hd-input" style="width:auto;padding:5px 10px" />
      </label>
      <button type="button" class="hd-btn hd-btn-outline" :disabled="openingReport" @click="openReport">
        <span class="material-icons" style="font-size:16px">print</span> {{ openingReport ? 'A preparar…' : 'Ver / imprimir' }}
      </button>
    </div>
    <!-- KPI cards -->
    <div class="hd-grid-4" style="margin-bottom:24px">
      <div class="hd-stat" v-for="s in kpis" :key="s.label">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div class="hd-stat-label">{{ s.label }}</div>
          <span class="material-icons hd-stat-icon" style="font-size:20px">{{ s.icon }}</span>
        </div>
        <div class="hd-stat-value">{{ s.value }}</div>
        <div class="hd-stat-trend" :style="{ color: s.up ? '#22C55E' : '#EF4444' }">
          <span class="material-icons" style="font-size:12px">{{ s.up ? 'trending_up' : 'trending_down' }}</span>
          {{ s.trend }}
        </div>
      </div>
    </div>

    <div class="stats-grid-2" style="margin-bottom:20px">
      <!-- Bar chart -->
      <div class="hd-card" style="padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:4px">Tickets criados vs resolvidos</div>
        <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">Últimas 4 semanas</div>
        <div v-if="loading" style="height:220px;display:flex;align-items:center;justify-content:center;color:var(--c-muted)">
          A carregar...
        </div>
        <Bar v-else :data="barData" :options="barOptions" style="max-height:220px" />
      </div>

      <!-- Donut chart -->
      <div class="hd-card" style="padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:4px">Distribuição por estado</div>
        <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">Total de tickets</div>
        <div v-if="loading" style="height:220px;display:flex;align-items:center;justify-content:center;color:var(--c-muted)">
          A carregar...
        </div>
        <div v-else style="display:flex;align-items:center;gap:24px">
          <Doughnut :data="donutData" :options="donutOptions" style="max-height:200px;max-width:200px" />
          <div style="display:flex;flex-direction:column;gap:8px">
            <div v-for="item in donutLegend" :key="item.label" class="hd-row" style="gap:8px;font-size:12px">
              <div style="width:10px;height:10px;border-radius:50%;flex-shrink:0" :style="{ background: item.color }"></div>
              <span style="color:var(--c-muted)">{{ item.label }}</span>
              <span style="font-weight:600;margin-left:auto">{{ item.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="stats-grid-2">
      <!-- Category breakdown -->
      <div class="hd-card" style="padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:4px">Tickets por categoria</div>
        <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">Volume relativo</div>
        <div v-if="loading" style="color:var(--c-muted)">A carregar...</div>
        <div v-else style="display:flex;flex-direction:column;gap:12px">
          <div v-for="cat in categoryStats" :key="cat.name">
            <div class="hd-row" style="margin-bottom:4px">
              <span style="font-size:13px;font-weight:500">{{ cat.name }}</span>
              <div class="hd-spacer"></div>
              <span style="font-size:13px;color:var(--c-muted)">{{ cat.count }}</span>
            </div>
            <div style="height:6px;background:var(--c-border);border-radius:3px;overflow:hidden">
              <div style="height:100%;border-radius:3px;transition:width .4s"
                :style="{ width: cat.pct + '%', background: cat.color }"></div>
            </div>
          </div>
          <div v-if="!categoryStats.length" style="color:var(--c-muted);font-size:13px">Sem dados.</div>
        </div>
      </div>

      <div class="hd-card" style="padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:4px">Utilizadores mais ativos</div>
        <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">Últimos 30 dias</div>
        <table class="hd-table compact-table">
          <thead><tr><th>UTILIZADOR</th><th>ACESSOS</th><th>ÚLTIMO ACESSO</th></tr></thead>
          <tbody>
            <tr v-for="u in accessTopUsers" :key="u.id">
              <td>
                <div style="font-weight:600">{{ u.name }}</div>
                <div style="font-size:11px;color:var(--c-muted)">{{ u.email }}</div>
              </td>
              <td style="font-weight:700">{{ u.hits }}</td>
              <td>{{ formatDateTime(u.last_seen) }}</td>
            </tr>
            <tr v-if="!accessTopUsers.length">
              <td colspan="3" style="text-align:center;color:var(--c-muted);padding:24px">Sem dados.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Requesters' satisfaction -->
    <div class="hd-card rating-card" style="padding:20px;margin-top:20px">
      <div style="font-weight:600;font-size:14px;margin-bottom:4px">Satisfação dos utilizadores</div>
      <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">Avaliações dos pedidos concluídos, últimos {{ ratings?.days ?? 90 }} dias</div>
      <div v-if="!ratings || !ratings.count" style="color:var(--c-muted);font-size:13px">Ainda não há avaliações. Os requerentes podem avaliar cada pedido quando é resolvido ou fechado.</div>
      <div v-else class="rating-layout">
        <div class="rating-avg">
          <div class="rating-avg-value">{{ ratings.average?.toFixed(1) }}</div>
          <div class="rating-avg-stars">{{ '★'.repeat(Math.round(ratings.average ?? 0)) }}<span>{{ '★'.repeat(5 - Math.round(ratings.average ?? 0)) }}</span></div>
          <div style="font-size:12px;color:var(--c-muted)">{{ ratings.count }} avaliaç{{ ratings.count === 1 ? 'ão' : 'ões' }}</div>
        </div>
        <div class="rating-bars">
          <div v-for="n in [5, 4, 3, 2, 1]" :key="n" class="rating-bar-row">
            <span>{{ n }} ★</span>
            <div class="rating-bar"><div :style="{ width: ratingPct(n) + '%' }"></div></div>
            <span class="rating-bar-count">{{ ratings.distribution[String(n)] }}</span>
          </div>
        </div>
        <div class="rating-comments">
          <router-link v-for="c in ratings.recent_comments" :key="c.ticket_id" :to="`/tickets/${c.ticket_id}`" class="rating-comment-item">
            <span class="rating-comment-stars">{{ '★'.repeat(c.stars) }}</span> “{{ c.comment }}”
            <small>T-{{ c.ticket_id }} · {{ c.title }}</small>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref as _ref, computed as _computed } from 'vue'
import { api as _api } from '../../boot/axios'
import { notifyError as _notifyError } from '../../utils/feedback'
import { STATUS_LABELS } from '../../utils/ticketStatus'
import { ref, computed, onMounted } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, ArcElement,
  Tooltip, Legend, Title,
} from 'chart.js'
import { getAdminStats } from '../../api/tickets'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend, Title)

const loading = ref(true)
const stats = ref<any>(null)

onMounted(async () => {
  try { stats.value = await getAdminStats() }
  catch { /* use empty state */ }
  finally { loading.value = false }
})

const kpis = computed(() => {
  if (!stats.value) return [
    { label: 'Total de tickets', value: '—', icon: 'confirmation_number', trend: '', up: true },
    { label: 'Abertos', value: '—', icon: 'inbox', trend: '', up: true },
    { label: 'Resolvidos este mês', value: '—', icon: 'check_circle', trend: '', up: true },
    { label: 'Tempo médio resolução', value: '—', icon: 'schedule', trend: '', up: true },
  ]
  const s = stats.value
  return [
    { label: 'Total de tickets', value: s.total ?? '—', icon: 'confirmation_number', trend: 'este mês', up: true },
    { label: 'Abertos', value: s.open ?? '—', icon: 'inbox', trend: 'aguardando', up: false },
    { label: 'Resolvidos/fechados', value: s.by_status ? (s.by_status.resolved ?? 0) + (s.by_status.closed ?? 0) : '—', icon: 'check_circle', trend: 'total', up: true },
    { label: 'Tempo médio', value: s.avg_resolution_hours ? `${s.avg_resolution_hours}h` : '—', icon: 'schedule', trend: 'até resolução', up: true },
  ]
})


const barData = computed(() => {
  const weekly = stats.value?.weekly ?? []
  const labels = weekly.length ? weekly.map((w: any) => w.week) : ['Sem 1', 'Sem 2', 'Sem 3', 'Sem 4']
  const created = weekly.length ? weekly.map((w: any) => w.created) : [0, 0, 0, 0]
  const resolved = weekly.length ? weekly.map((w: any) => w.resolved) : [0, 0, 0, 0]
  return {
    labels,
    datasets: [
      { label: 'Criados', data: created, backgroundColor: '#3D52D5cc', borderRadius: 4 },
      { label: 'Resolvidos/fechados', data: resolved, backgroundColor: '#22C55Ecc', borderRadius: 4 },
    ],
  }
})

const barOptions = {
  responsive: true,
  plugins: { legend: { position: 'top' as const } },
  scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { stepSize: 1 } } },
}


const statusColors: Record<string, string> = {
  open: '#3D52D5', assigned: '#F59E0B', in_progress: '#8B5CF6', waiting_user: '#0891B2', resolved: '#22C55E', closed: '#6B7280',
}
const statusLabels = STATUS_LABELS

const donutData = computed(() => {
  const by_status = stats.value?.by_status ?? {}
  const keys = Object.keys(statusColors)
  return {
    labels: keys.map(k => statusLabels[k]),
    datasets: [{
      data: keys.map(k => by_status[k] ?? 0),
      backgroundColor: keys.map(k => statusColors[k]),
      borderWidth: 0,
    }],
  }
})

const donutOptions = { responsive: true, plugins: { legend: { display: false } }, cutout: '70%' }

const donutLegend = computed(() => {
  const by_status = stats.value?.by_status ?? {}
  return Object.keys(statusColors).map(k => ({
    label: statusLabels[k],
    color: statusColors[k],
    count: by_status[k] ?? 0,
  }))
})

const categoryStats = computed(() => {
  const by_cat = stats.value?.by_category ?? []
  if (!by_cat.length) return []
  const max = Math.max(...by_cat.map((c: any) => c.count))
  return by_cat.map((c: any) => ({ ...c, pct: max ? Math.round(c.count / max * 100) : 0 }))
})

const accessTopUsers = computed(() => stats.value?.access?.top_users ?? [])

function formatDateTime(value?: string | null) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('pt-PT', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value))
}

const ratings = _computed<any>(() => (stats.value as any)?.ratings ?? null)
function ratingPct(n: number) {
  const r = ratings.value
  if (!r || !r.count) return 0
  return Math.round((r.distribution[String(n)] / r.count) * 100)
}

// Monthly report (the one emailed to the Direção), printable: Imprimir → Guardar como PDF
const _prev = new Date(); _prev.setDate(1); _prev.setMonth(_prev.getMonth() - 1)
const reportMonth = _ref(`${_prev.getFullYear()}-${String(_prev.getMonth() + 1).padStart(2, '0')}`)
const openingReport = _ref(false)
async function openReport() {
  const win = window.open('', '_blank')
  openingReport.value = true
  try {
    const { data } = await _api.get('/api/v1/admin/report/html', { params: { month: reportMonth.value }, responseType: 'text' })
    if (win) { win.document.open(); win.document.write(data); win.document.close() }
  } catch (e) {
    win?.close()
    _notifyError(e, 'Não foi possível gerar o relatório.')
  } finally {
    openingReport.value = false
  }
}
</script>

<style scoped>
.report-bar { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.report-bar label { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--c-muted); }
.rating-layout { display: grid; grid-template-columns: 140px minmax(0, 1fr) minmax(0, 1.3fr); gap: 24px; align-items: start; }
@media (max-width: 900px) { .rating-layout { grid-template-columns: 1fr; } }
.rating-avg { text-align: center; }
.rating-avg-value { font-size: 40px; font-weight: 800; line-height: 1; }
.rating-avg-stars { color: #F59E0B; font-size: 18px; letter-spacing: 1px; margin: 4px 0; }
.rating-avg-stars span { color: #D1D5DB; }
.rating-bar-row { display: grid; grid-template-columns: 36px 1fr 30px; align-items: center; gap: 8px; font-size: 12.5px; margin-bottom: 6px; }
.rating-bar { height: 8px; border-radius: 4px; background: var(--c-border); overflow: hidden; }
.rating-bar div { height: 100%; background: #F59E0B; border-radius: 4px; }
.rating-bar-count { text-align: right; color: var(--c-muted); }
.rating-comments { display: flex; flex-direction: column; gap: 8px; }
.rating-comment-item { display: block; font-size: 13px; color: var(--c-text); text-decoration: none; padding: 8px 10px; border: 1px solid var(--c-border); border-radius: 10px; }
.rating-comment-item:hover { border-color: var(--c-primary); }
.rating-comment-item small { display: block; color: var(--c-muted); margin-top: 2px; }
.rating-comment-stars { color: #F59E0B; }
.stats-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
@media (max-width: 1099px) {
  .stats-grid-2 { grid-template-columns: 1fr; }
}
.compact-table td,
.compact-table th {
  padding: 10px 8px;
}
@media (max-width: 1099px) {
  .access-split {
    grid-template-columns: 1fr;
  }
}
</style>
