<template>
  <article
    class="trow"
    :class="{ unread: ticket.is_unread, done }"
    :style="{ '--row-color': statusColor(ticket.status) }"
    @click="$router.push(`/tickets/${ticket.id}`)"
  >
    <div class="trow-dot" :class="{ on: ticket.is_unread }" :title="ticket.is_unread ? 'Tem novidades que ainda não leu' : ''"></div>
    <div class="trow-main">
      <div class="trow-title">{{ ticket.title }}</div>
      <div class="trow-meta">
        <span class="trow-id">T-{{ ticket.id }}</span>
        <ReminderChip :at="ticket.reminder_at" />
        <span v-if="ticket.is_escalated" class="trow-esc" title="Reportado à empresa de apoio">E</span>
        <span v-if="ticket.school" class="trow-school" :title="ticket.school.name">{{ schoolInitials(ticket.school.name) }}</span>
        <span class="trow-cat">{{ ticket.category?.name || 'Sem categoria' }}</span>
        <span class="trow-sep">·</span>
        <span class="trow-person"><PersonName :name="ticket.creator?.display_name" /></span>
        <span class="trow-sep">·</span>
        <span class="trow-time" :title="formatDateTime(ticket.updated_at)">{{ timeAgo(ticket.updated_at) }}</span>
      </div>
    </div>
    <div class="trow-badges">
      <span class="trow-status" :title="statusLabel(ticket.status)">{{ statusLabel(ticket.status, true) }}</span>
      <PriorityBadge :priority="ticket.priority" />
      <TicketActions :ticket="ticket" @read-changed="(u) => emit('read-changed', u)" @deleted="emit('deleted')" />
    </div>
  </article>
</template>

<script setup lang="ts">
// One ticket in "Os meus tickets", in the style of the Painel inicial's recent tickets
import PriorityBadge from './PriorityBadge.vue'
import ReminderChip from './ReminderChip.vue'
import PersonName from './PersonName.vue'
import TicketActions from './TicketActions.vue'
import { formatDateTime, timeAgo } from '../utils/dates'
import { schoolInitials } from '../utils/names'
import { statusColor, statusLabel } from '../utils/ticketStatus'

defineProps<{ ticket: any; done?: boolean }>()
const emit = defineEmits<{ (e: 'read-changed', unread: boolean): void; (e: 'deleted'): void }>()
</script>

<style scoped>
.trow {
  display: flex; align-items: center; gap: 12px; padding: 12px 14px; min-width: 0;
  border-radius: 12px; border: 1px solid var(--c-border); border-left: 4px solid var(--row-color);
  background: var(--c-surface); cursor: pointer;
  transition: transform .12s ease, box-shadow .12s ease, background .12s ease;
}
.trow:hover { transform: translateX(2px); box-shadow: 0 6px 16px rgba(15, 23, 42, .08); background: color-mix(in srgb, var(--row-color) 6%, var(--c-surface)); }
.trow.done { opacity: .78; }
.trow-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; background: var(--row-color); box-shadow: 0 0 0 4px color-mix(in srgb, var(--row-color) 20%, transparent); }
.trow-dot.on { background: #2563EB; box-shadow: 0 0 0 4px rgba(37, 99, 235, .25); }
.trow-main { flex: 1; min-width: 0; }
.trow-title { font-size: 14.5px; font-weight: 600; color: var(--c-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.trow.unread .trow-title { font-weight: 800; }
.trow.unread { background: color-mix(in srgb, #2563EB 5%, var(--c-surface)); }
.trow-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; font-size: 12px; color: var(--c-muted); margin-top: 4px; min-width: 0; }
.trow-id { font-weight: 700; }
.trow.unread .trow-id { color: var(--c-text); }
.trow-sep { opacity: .6; }
.trow-school { font-size: 11px; font-weight: 800; letter-spacing: .04em; color: #0E7490; background: #CFFAFE; border: 1px solid #A5F3FC; border-radius: 7px; padding: 0 6px; }
.dark .trow-school { color: #A5F3FC; background: rgba(8, 145, 178, .2); border-color: rgba(34, 211, 238, .35); }
.trow-esc { font-size: 10.5px; font-weight: 800; color: #fff; background: #EA580C; border-radius: 50%; width: 17px; height: 17px; display: inline-flex; align-items: center; justify-content: center; }
.trow-cat { font-weight: 600; color: var(--c-primary); }
.trow-person { display: inline-flex; min-width: 0; max-width: 260px; }
.trow-badges { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.trow-status { font-size: 11.5px; font-weight: 700; padding: 3px 10px; border-radius: 999px; color: var(--row-color); background: color-mix(in srgb, var(--row-color) 14%, transparent); white-space: nowrap; }
.trow-badges :deep(.tact) { opacity: .45; }
.trow:hover .trow-badges :deep(.tact) { opacity: 1; }
@media (max-width: 700px) {
  .trow { flex-wrap: wrap; align-items: flex-start; }
  .trow-dot { margin-top: 5px; }
  .trow-main { flex-basis: calc(100% - 30px); }
  .trow-badges { width: 100%; padding-left: 22px; }
  .trow-badges :deep(.tact) { margin-left: auto; opacity: 1; }
}
</style>
