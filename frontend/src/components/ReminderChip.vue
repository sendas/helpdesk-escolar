<template>
  <span v-if="at" class="reminder-chip" :class="{ compact }" :title="'Lembrete seu: ' + long">
    <span class="material-icons">alarm</span><template v-if="!compact">{{ short }}</template>
  </span>
</template>

<script setup lang="ts">
// The viewer's own pending reminder on a ticket (reminders are private). Dates arrive in UTC without a time zone.
import { computed } from 'vue'

// compact: only the alarm icon (the date shows on hover), for narrow table columns
const props = defineProps<{ at?: string | null; compact?: boolean }>()
const date = computed(() => props.at ? new Date(/Z|[+-]\d\d:\d\d$/.test(props.at) ? props.at : props.at + 'Z') : null)
const short = computed(() => {
  const d = date.value
  if (!d) return ''
  const time = d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
  const today = new Date()
  const tomorrow = new Date(); tomorrow.setDate(today.getDate() + 1)
  if (d.toDateString() === today.toDateString()) return `hoje ${time}`
  if (d.toDateString() === tomorrow.toDateString()) return `amanhã ${time}`
  return `${d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' })} ${time}`
})
const long = computed(() => date.value?.toLocaleString('pt-PT', { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }) ?? '')
</script>

<style scoped>
.reminder-chip { display: inline-flex; align-items: center; gap: 3px; margin-left: 6px; padding: 1px 7px 1px 5px; border-radius: 999px; font-size: 11px; font-weight: 700; white-space: nowrap; color: #B45309; background: #FEF3C7; border: 1px solid #FDE68A; vertical-align: 1px; }
.reminder-chip .material-icons { font-size: 13px; }
.reminder-chip.compact { padding: 2px; margin-left: 4px; border-radius: 50%; }
.reminder-chip.compact .material-icons { font-size: 14px; }
.dark .reminder-chip { color: #FCD34D; background: rgba(245, 158, 11, .15); border-color: rgba(245, 158, 11, .35); }
</style>
