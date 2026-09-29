<template>
  <article class="tcard" :class="{ unread: ticket.is_unread, done }" @click="$router.push(`/tickets/${ticket.id}`)">
    <div class="tcard-top">
      <span class="tcard-dot" :class="{ on: ticket.is_unread }" :title="ticket.is_unread ? 'Tem novidades que ainda não leu' : ''"></span>
      <span class="tcard-id">T-{{ ticket.id }}</span>
      <ReminderChip :at="ticket.reminder_at" />
      <span class="tcard-time">{{ timeAgo(ticket.updated_at) }}</span>
      <TicketActions :ticket="ticket" @read-changed="(u) => emit('read-changed', u)" @deleted="emit('deleted')" />
    </div>
    <div class="tcard-title">{{ ticket.title }}</div>
    <div class="tcard-meta">
      <span class="hd-status" :class="ticket.status">{{ statusLabel }}</span>
      <PriorityBadge :priority="ticket.priority" />
      <span v-if="ticket.school" class="tcard-school" :title="ticket.school.name">{{ schoolInitials(ticket.school.name) }}</span>
      <span class="tcard-cat" :title="ticket.category?.name">{{ ticket.category?.name }}</span>
    </div>
    <div class="tcard-person"><PersonName :name="ticket.creator?.display_name" /></div>
  </article>
</template>

<script setup lang="ts">
// One ticket as a card, for tablets and phones (the table is used on wide screens)
import { statusLabel as labelFor } from '../utils/ticketStatus'
import { computed } from 'vue'
import PriorityBadge from './PriorityBadge.vue'
import ReminderChip from './ReminderChip.vue'
import PersonName from './PersonName.vue'
import TicketActions from './TicketActions.vue'
import { timeAgo } from '../utils/dates'
import { schoolInitials } from '../utils/names'

const props = defineProps<{ ticket: any; done?: boolean }>()
const emit = defineEmits<{ (e: 'read-changed', unread: boolean): void; (e: 'deleted'): void }>()
const statusLabel = computed(() => labelFor(props.ticket.status))
</script>

<style scoped>
.tcard { min-width: 0; padding: 12px 14px; border: 1px solid var(--c-border); border-radius: 14px; background: var(--c-surface); cursor: pointer; display: flex; flex-direction: column; gap: 8px; }
.tcard:hover { border-color: var(--c-primary); }
.tcard.unread { background: rgba(37, 99, 235, .06); border-color: rgba(37, 99, 235, .35); }
.dark .tcard.unread { background: rgba(96, 165, 250, .09); }
.tcard.done { opacity: .8; }
.tcard-top { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--c-muted); min-width: 0; }
.tcard-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; background: transparent; }
.tcard-dot.on { background: #2563EB; box-shadow: 0 0 0 3px rgba(37, 99, 235, .18); }
.tcard-id { font-weight: 600; }
.tcard.unread .tcard-id { color: var(--c-text); font-weight: 800; }
.tcard-top :deep(.reminder-chip) { margin-left: 2px; }
.tcard-time { margin-left: auto; white-space: nowrap; }
.tcard-title { font-size: 14.5px; font-weight: 600; color: var(--c-text); line-height: 1.35; overflow-wrap: anywhere; }
.tcard.unread .tcard-title { font-weight: 800; }
.tcard-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
.tcard-school { font-size: 11.5px; font-weight: 800; letter-spacing: .04em; color: #0E7490; background: #CFFAFE; border: 1px solid #A5F3FC; border-radius: 8px; padding: 1px 7px; }
.dark .tcard-school { color: #A5F3FC; background: rgba(8, 145, 178, .2); border-color: rgba(34, 211, 238, .35); }
.tcard-cat { font-size: 12px; font-weight: 600; color: var(--c-primary); background: rgba(64, 87, 216, .08); border-radius: 999px; padding: 2px 9px; max-width: 160px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dark .tcard-cat { background: rgba(99, 125, 255, .16); color: #A5B4FC; }
.tcard-person { font-size: 13px; color: var(--c-muted); min-width: 0; display: flex; }
</style>
