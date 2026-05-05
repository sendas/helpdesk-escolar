<template>
  <q-badge :color="color" :label="label" class="ticket-status-badge" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const map: Record<string, { color: string; label: string }> = {
  open: { color: 'orange', label: 'Aberto' },
  assigned: { color: 'purple', label: 'Atribuído' },
  in_progress: { color: 'blue', label: 'Em Curso' },
  waiting_user: { color: 'cyan', label: 'A aguardar utilizador' },
  resolved: { color: 'green', label: 'Resolvido' },
  closed: { color: 'grey', label: 'Fechado' },
}

const color = computed(() => map[props.status]?.color ?? 'grey')
const label = computed(() => map[props.status]?.label ?? props.status)
</script>
