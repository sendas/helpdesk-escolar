<template>
  <div class="hd-page">
    <h1 style="font-size:22px;margin-bottom:24px">Estatísticas</h1>

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

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">
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

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
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

      <!-- Team performance -->
      <div class="hd-card" style="padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:4px">Desempenho da equipa</div>
        <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">Tickets resolvidos por técnico</div>
        <div v-if="loading" style="color:var(--c-muted)">A carregar...</div>
        <table v-else class="hd-table">
          <thead>
            <tr>
              <th>TÉCNICO</th>
              <th style="text-align:center">RESOLVIDOS</th>
              <th style="text-align:center">EM CURSO</th>
              <th>AVALIAÇÃO</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in teamStats" :key="m.name">
              <td>
                <div class="hd-row" style="gap:6px">
                  <AvatarCircle :name="m.name" size="24" />
                  <span style="font-size:13px">{{ m.name }}</span>
                </div>
              </td>
              <td style="text-align:center;font-weight:600">{{ m.resolved }}</td>
              <td style="text-align:center;color:var(--c-muted)">{{ m.in_progress }}</td>
              <td>
                <div style="display:flex;gap:2px">
                  <span v-for="i in 5" :key="i" class="material-icons"
                    :style="{ fontSize: '12px', color: i <= m.rating ? '#F59E0B' : 'var(--c-border)' }">star</span>
                </div>
              </td>
            </tr>
            <tr v-if="!teamStats.length">
              <td colspan="4" style="text-align:center;color:var(--c-muted);padding:24px">Sem dados.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, ArcElement,
  Tooltip, Legend, Title,
} from 'chart.js'
import { getAdminStats } from '../../api/tickets'
import AvatarCircle from '../../components/AvatarCircle.vue'

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
    { label: 'Resolvidos', value: s.resolved ?? '—', icon: 'check_circle', trend: 'total', up: true },
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
      { label: 'Resolvidos', data: resolved, backgroundColor: '#22C55Ecc', borderRadius: 4 },
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
const statusLabels: Record<string, string> = {
  open: 'Aberto', assigned: 'Atribuído', in_progress: 'Em Curso', waiting_user: 'A aguardar utilizador', resolved: 'Resolvido', closed: 'Fechado',
}

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

const teamStats = computed(() => stats.value?.by_assignee ?? [])
</script>
