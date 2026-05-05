<template>
  <div class="hd-page">
    <h1 style="font-size:26px;margin-bottom:24px">Olá, {{ auth.user?.display_name?.split(' ')[0] }}</h1>

    <!-- Stat cards -->
    <div class="hd-grid-4" style="margin-bottom:24px">
      <div class="hd-stat" v-for="s in stats" :key="s.label">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div class="hd-stat-label">{{ s.label }}</div>
          <span class="material-icons hd-stat-icon" style="font-size:20px">{{ s.icon }}</span>
        </div>
        <div class="hd-stat-value">{{ s.count }}</div>
        <div class="hd-stat-trend" style="color:var(--c-muted)">{{ s.sub }}</div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 300px;gap:20px">
      <!-- Recent tickets -->
      <div class="hd-card">
        <div style="display:flex;align-items:center;padding:16px 20px;border-bottom:1px solid var(--c-border)">
          <div style="font-weight:600;font-size:14px">Os meus tickets recentes</div>
          <div style="font-size:12px;color:var(--c-muted);margin-left:8px">Últimos pedidos submetidos</div>
          <div class="hd-spacer"></div>
          <router-link to="/tickets" style="font-size:13px;color:var(--c-primary);text-decoration:none;font-weight:500">Ver todos</router-link>
        </div>
        <table class="hd-table">
          <thead>
            <tr>
              <th>ID</th><th>ASSUNTO</th><th>ESTADO</th><th>PRIORIDADE</th><th>ATUALIZADO</th>
            </tr>
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

      <!-- Categories sidebar -->
      <div class="hd-card" style="padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:4px">Categorias mais comuns</div>
        <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">Para que tipo de pedido?</div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <div
            v-for="cat in categories"
            :key="cat.id"
            class="hd-sel-card"
            style="padding:10px 12px"
            @click="$router.push('/tickets/new')"
          >
            <div class="hd-sel-icon" :style="{ background: cat.color + '22' }">
              <span class="material-icons" :style="{ color: cat.color, fontSize: '16px' }">{{ cat.icon }}</span>
            </div>
            <div style="flex:1;min-width:0">
              <div class="hd-sel-title" style="font-size:12.5px">{{ cat.name }}</div>
              <div style="font-size:11px;color:var(--c-muted)">SLA: {{ cat.sla_hours }}h</div>
            </div>
            <span class="material-icons" style="font-size:14px;color:var(--c-muted)">chevron_right</span>
          </div>
        </div>
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
  { label: 'Em Análise', count: tickets.value.filter(t => ['assigned','in_progress'].includes(t.status)).length, icon: 'schedule', sub: 'em curso' },
  { label: 'Resolvidos', count: tickets.value.filter(t => t.status === 'resolved').length, icon: 'check_circle', sub: 'resolvidos' },
  { label: 'Tempo Médio', count: '—', icon: 'bar_chart', sub: 'até resposta' },
])

function statusLabel(s: string) {
  return { open: 'Aberto', assigned: 'Atribuído', in_progress: 'Em Curso', resolved: 'Resolvido', closed: 'Fechado' }[s] ?? s
}

</script>
