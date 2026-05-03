<template>
  <q-page padding>
    <div class="text-h5 q-mb-lg">Painel de Administração</div>

    <div class="row q-col-gutter-md q-mb-lg">
      <div class="col-6 col-md-3" v-for="item in statCards" :key="item.label">
        <q-card>
          <q-card-section class="text-center">
            <q-icon :name="item.icon" :color="item.color" size="36px" />
            <div class="text-h4 text-weight-bold q-mt-xs" :class="`text-${item.color}`">{{ item.count }}</div>
            <div class="text-caption text-grey">{{ item.label }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card>
      <q-card-section class="row items-center">
        <div class="text-subtitle1">Tickets Recentes</div>
        <q-space />
        <q-btn flat dense color="primary" label="Ver todos" to="/admin/tickets" />
      </q-card-section>
      <q-separator />
      <q-list>
        <q-item v-for="t in recentTickets" :key="t.id" clickable :to="`/tickets/${t.id}`">
          <q-item-section>
            <q-item-label>{{ t.title }}</q-item-label>
            <q-item-label caption>{{ t.creator.display_name }} · {{ t.category.name }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <StatusBadge :status="t.status" />
          </q-item-section>
        </q-item>
      </q-list>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getAdminStats, getTickets } from '../../api/tickets'
import StatusBadge from '../../components/StatusBadge.vue'

const stats = ref<any>({ total: 0, by_status: {} })
const recentTickets = ref<any[]>([])

onMounted(async () => {
  stats.value = await getAdminStats()
  const data = await getTickets({ page: 1, size: 5, admin: true })
  recentTickets.value = data.items
})

const statCards = computed(() => [
  { label: 'Total', count: stats.value.total, icon: 'inbox', color: 'grey-8' },
  { label: 'Abertos', count: stats.value.by_status.open ?? 0, icon: 'fiber_new', color: 'orange' },
  { label: 'Em Progresso', count: stats.value.by_status.in_progress ?? 0, icon: 'pending', color: 'blue' },
  { label: 'Resolvidos', count: stats.value.by_status.resolved ?? 0, icon: 'check_circle', color: 'green' },
])
</script>
