<template>
  <span class="tact" @click.stop>
    <button
      type="button"
      class="tact-btn"
      :title="ticket.is_unread ? 'Marcar como lido' : 'Marcar como não lido'"
      :disabled="busy"
      @click="toggleRead"
    >
      <span class="material-icons">{{ ticket.is_unread ? 'mark_email_read' : 'mark_email_unread' }}</span>
      <span v-if="labels">{{ ticket.is_unread ? 'Marcar como lido' : 'Marcar como não lido' }}</span>
    </button>
    <button v-if="auth.isAdmin" type="button" class="tact-btn danger" title="Apagar ticket" :disabled="busy" @click="remove">
      <span class="material-icons">delete</span>
      <span v-if="labels">Apagar ticket</span>
    </button>
  </span>
</template>

<script setup lang="ts">
// Per-ticket actions: read/unread (everyone) and delete (administrators)
import { ref } from 'vue'
import { adminBulkActionTickets, markTicketUnread, markTicketsRead } from '../api/tickets'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ ticket: any; labels?: boolean }>()
const emit = defineEmits<{ (e: 'read-changed', unread: boolean): void; (e: 'deleted'): void }>()
const auth = useAuthStore()
const busy = ref(false)

async function toggleRead() {
  busy.value = true
  try {
    const unread = !props.ticket.is_unread
    if (unread) await markTicketUnread(props.ticket.id)
    else await markTicketsRead([props.ticket.id])
    emit('read-changed', unread)
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!confirm(`Apagar definitivamente o ticket T-${props.ticket.id} ("${props.ticket.title}")?\n\nApaga também as respostas e os anexos. Não é possível desfazer.`)) return
  busy.value = true
  try {
    await adminBulkActionTickets({ ids: [props.ticket.id], action: 'delete' })
    emit('deleted')
  } catch (e: any) {
    alert(e?.response?.data?.detail || 'Não foi possível apagar o ticket.')
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.tact { display: inline-flex; align-items: center; gap: 2px; }
.tact-btn { display: inline-flex; align-items: center; gap: 6px; border: 0; background: transparent; color: var(--c-muted); border-radius: 8px; padding: 5px; cursor: pointer; font-size: 12.5px; font-weight: 600; }
.tact-btn .material-icons { font-size: 18px; }
.tact-btn:hover { background: var(--c-primary-soft); color: var(--c-primary); }
.tact-btn.danger:hover { background: rgba(220, 38, 38, .1); color: #DC2626; }
.tact-btn:disabled { opacity: .5; cursor: default; }
</style>
