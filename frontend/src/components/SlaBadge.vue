<template>
  <span v-if="slaHours && !isDone" class="sla-badge" :class="urgency" :title="title">
    <span class="material-icons" style="font-size:12px;vertical-align:middle">schedule</span>
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  createdAt: string
  slaHours?: number | null
  status?: string
}>()

const DONE = new Set(['resolved', 'closed'])

const isDone = computed(() => DONE.has(props.status ?? ''))

const dueAt = computed(() => {
  if (!props.createdAt) return 0
  const due = new Date(new Date(props.createdAt).getTime() + (props.slaHours ?? 0) * 3_600_000)
  while (due.getDay() === 0 || due.getDay() === 6) {
    due.setDate(due.getDate() + 1)
    due.setHours(9, 0, 0, 0)
  }
  return due.getTime()
})

const remaining = computed(() => (dueAt.value - Date.now()) / 3_600_000)

const urgency = computed(() => {
  if (remaining.value < 0) return 'breached'
  if (remaining.value < (props.slaHours ?? 0) * 0.25) return 'critical'
  if (remaining.value < (props.slaHours ?? 0) * 0.5) return 'warning'
  return 'ok'
})

const label = computed(() => {
  const r = remaining.value
  if (r < 0) {
    const over = Math.abs(r)
    return over < 1 ? `+${Math.round(over * 60)}m` : `+${Math.round(over)}h`
  }
  return r < 1 ? `${Math.round(r * 60)}m` : `${Math.round(r)}h`
})

const title = computed(() => {
  if (remaining.value < 0) return `Tempo de resposta ultrapassado há ${label.value.slice(1)}`
  return `${label.value} restantes (tempo de resposta: ${props.slaHours}h)`
})
</script>

<style scoped>
.sla-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 700;
  border-radius: 5px;
  padding: 2px 7px;
  white-space: nowrap;
}
.sla-badge.ok { background: #DCFCE7; color: #166534; }
.sla-badge.warning { background: #FEF9C3; color: #854D0E; }
.sla-badge.critical { background: #FFEDD5; color: #9A3412; }
.sla-badge.breached { background: #FEE2E2; color: #991B1B; }
:root.dark .sla-badge.ok { background: #14532D; color: #86EFAC; }
:root.dark .sla-badge.warning { background: #422006; color: #FDE68A; }
:root.dark .sla-badge.critical { background: #431407; color: #FDBA74; }
:root.dark .sla-badge.breached { background: #450A0A; color: #FCA5A5; }
</style>
