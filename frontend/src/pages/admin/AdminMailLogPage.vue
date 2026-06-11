<template>
  <div class="hd-page mail-log-page">
    <div class="page-heading">
      <button class="hd-btn hd-btn-outline" :disabled="loading" @click="load">
        <span class="material-icons">{{ loading ? 'hourglass_empty' : 'refresh' }}</span>
        Atualizar
      </button>
    </div>

    <section class="hd-card">
      <div class="card-title">
        <span class="material-icons">email</span>
        Log de processamento de emails
      </div>
      <p class="card-copy">
        Mostra os últimos 200 eventos gerados pelo processamento de emails — respostas recebidas e tickets fechados automaticamente.
      </p>

      <div v-if="loading" class="log-loading">A carregar...</div>
      <div v-else-if="!entries.length" class="log-empty">
        Nenhum evento registado. Certifique-se de que a sincronização de emails está ativa e que já foram processados emails.
      </div>
      <div v-else class="log-table-wrap">
        <table class="log-table">
          <thead>
            <tr>
              <th>Data / hora</th>
              <th>Ticket</th>
              <th>Tipo</th>
              <th>Mensagem</th>
              <th>Ator</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in entries" :key="e.id" :class="rowClass(e)">
              <td class="log-date">{{ formatDate(e.created_at) }}</td>
              <td class="log-ticket">
                <router-link :to="`/tickets/${e.ticket_id}`" class="log-ticket-link">
                  #{{ e.ticket_id }}
                  <span v-if="e.ticket_title" class="log-ticket-title">{{ e.ticket_title }}</span>
                </router-link>
              </td>
              <td class="log-type">
                <span class="log-badge" :class="badgeClass(e.event_type)">{{ typeLabel(e.event_type) }}</span>
              </td>
              <td class="log-msg">{{ e.message }}</td>
              <td class="log-actor">{{ e.actor_name || e.actor_email || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMailLog, type MailLogEntry } from '../../api/tickets'

const loading = ref(false)
const entries = ref<MailLogEntry[]>([])

async function load() {
  loading.value = true
  try {
    entries.value = await getMailLog(200)
  } finally {
    loading.value = false
  }
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit', year: 'numeric' })
    + ' ' + d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function typeLabel(t: string) {
  if (t === 'email_reply') return 'Resposta'
  if (t === 'status_changed') return 'Estado'
  return t
}

function badgeClass(t: string) {
  if (t === 'status_changed') return 'badge-status'
  if (t === 'email_reply') return 'badge-reply'
  return 'badge-other'
}

function rowClass(e: MailLogEntry) {
  if (e.event_type === 'status_changed') return 'row-status'
  return ''
}

onMounted(load)
</script>

<style scoped>
.mail-log-page { max-width: 1100px; }
.page-heading { display: flex; gap: 10px; margin-bottom: 18px; }
.card-copy { color: var(--c-muted); font-size: 13px; margin: 0 0 16px; }
.log-loading, .log-empty { color: var(--c-muted); font-size: 14px; padding: 24px 0; text-align: center; }
.log-table-wrap { overflow-x: auto; }
.log-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.log-table th {
  text-align: left; padding: 8px 10px;
  border-bottom: 2px solid var(--c-border);
  font-size: 11px; text-transform: uppercase; color: var(--c-muted); white-space: nowrap;
}
.log-table td { padding: 8px 10px; border-bottom: 1px solid var(--c-border); vertical-align: top; }
.log-table tr:last-child td { border-bottom: none; }
.row-status td { background: rgba(34, 197, 94, 0.16); }
.row-status td:first-child { border-left: 3px solid #22c55e; }
.log-date { white-space: nowrap; color: var(--c-muted); font-size: 12px; }
.log-ticket-link { color: var(--c-accent); text-decoration: none; font-weight: 600; }
.log-ticket-link:hover { text-decoration: underline; }
.log-ticket-title { display: block; font-size: 11px; color: var(--c-muted); font-weight: 400; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log-msg { max-width: 380px; word-break: break-word; }
.log-actor { white-space: nowrap; color: var(--c-muted); font-size: 12px; }
.log-badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.badge-reply { background: rgba(59, 130, 246, 0.15); color: #2563eb; }
.badge-status { background: rgba(34, 197, 94, 0.18); color: #16a34a; }
.badge-other { background: var(--c-border); color: var(--c-muted); }
</style>
