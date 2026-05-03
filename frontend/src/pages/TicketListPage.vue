<template>
  <div class="hd-page">
    <div class="hd-row" style="margin-bottom:20px">
      <h1 style="font-size:22px">Os meus tickets</h1>
      <div class="hd-spacer"></div>
      <router-link to="/tickets/new">
        <button class="hd-btn hd-btn-primary"><span class="material-icons" style="font-size:16px">add</span> Novo ticket</button>
      </router-link>
    </div>

    <div class="hd-card">
      <div style="display:flex;gap:10px;padding:14px 16px;border-bottom:1px solid var(--c-border);flex-wrap:wrap">
        <select class="hd-select" style="width:auto" v-model="filterStatus" @change="load">
          <option value="">Todos os estados</option>
          <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
        </select>
        <select class="hd-select" style="width:auto" v-model="filterCat" @change="load">
          <option value="">Todas as categorias</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>

      <div v-if="loading" style="padding:48px;text-align:center;color:var(--c-muted)">A carregar...</div>
      <table v-else class="hd-table">
        <thead>
          <tr><th>ID</th><th>ASSUNTO</th><th>ESTADO</th><th>PRIORIDADE</th><th>ATUALIZADO</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in tickets" :key="t.id" @click="$router.push(`/tickets/${t.id}`)">
            <td style="color:var(--c-muted);font-size:12px;white-space:nowrap">T-{{ t.id }}</td>
            <td style="font-weight:500">{{ t.title }}</td>
            <td><span class="hd-status" :class="t.status">{{ statusLabel(t.status) }}</span></td>
            <td><PriorityBadge :priority="t.priority" /></td>
            <td style="color:var(--c-muted)">{{ timeAgo(t.updated_at) }}</td>
          </tr>
          <tr v-if="!tickets.length">
            <td colspan="5" style="text-align:center;color:var(--c-muted);padding:40px">Sem tickets.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getTickets, getCategories } from '../api/tickets'
import PriorityBadge from '../components/PriorityBadge.vue'

const tickets = ref<any[]>([])
const categories = ref<any[]>([])
const loading = ref(false)
const filterStatus = ref('')
const filterCat = ref<number | ''>('')

const statusOpts = [
  { v: 'open', l: 'Aberto' }, { v: 'assigned', l: 'Atribuído' },
  { v: 'in_progress', l: 'Em Curso' }, { v: 'resolved', l: 'Resolvido' }, { v: 'closed', l: 'Fechado' },
]

onMounted(async () => {
  categories.value = await getCategories()
  await load()
})

async function load() {
  loading.value = true
  try {
    const p: any = { page: 1, size: 50 }
    if (filterStatus.value) p.status = filterStatus.value
    if (filterCat.value) p.category_id = filterCat.value
    const d = await getTickets(p)
    tickets.value = d.items
  } finally { loading.value = false }
}

function statusLabel(s: string) {
  return { open:'Aberto', assigned:'Atribuído', in_progress:'Em Curso', resolved:'Resolvido', closed:'Fechado' }[s] ?? s
}
function timeAgo(d: string) {
  const h = Math.floor((Date.now() - new Date(d).getTime()) / 3600000)
  if (h < 1) return 'agora'
  if (h < 24) return `há ${h}h`
  return `há ${Math.floor(h/24)} d`
}
</script>
