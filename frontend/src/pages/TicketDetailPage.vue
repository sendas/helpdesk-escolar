<template>
  <div class="hd-page">
    <div style="font-size:12px;color:var(--c-muted);margin-bottom:6px">
      <router-link to="/tickets" style="color:var(--c-muted);text-decoration:none">Tickets</router-link>
      / <span>T-{{ ticket?.id }}</span>
    </div>

    <div v-if="!ticket" style="padding:80px;text-align:center;color:var(--c-muted)">A carregar...</div>

    <template v-else>
      <div class="hd-row" style="align-items:flex-start;margin-bottom:24px">
        <div style="flex:1;min-width:0">
          <h1 style="font-size:22px;margin-bottom:4px">{{ ticket.title }}</h1>
          <div style="font-size:13px;color:var(--c-muted)">
            Aberto por <strong>{{ ticket.creator.display_name }}</strong> · {{ formatDate(ticket.created_at) }}
          </div>
        </div>
        <div class="hd-row" style="gap:8px;flex-shrink:0">
          <span class="hd-status" :class="ticket.status">{{ statusLabel(ticket.status) }}</span>
          <PriorityBadge :priority="ticket.priority" />
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 300px;gap:20px;align-items:start">
        <!-- Left: conversation -->
        <div>
          <!-- Description message -->
          <div class="hd-msg" style="margin-bottom:12px">
            <AvatarCircle :name="ticket.creator.display_name" size="36" />
            <div class="hd-msg-body">
              <div class="hd-msg-header">
                <span class="hd-msg-author">{{ ticket.creator.display_name }}</span>
                <span class="hd-msg-time">{{ formatDate(ticket.created_at) }}</span>
              </div>
              <div class="hd-msg-bubble">{{ ticket.description }}</div>
              <div v-if="ticket.attachments?.length" style="display:flex;flex-direction:column;gap:6px;margin-top:8px">
                <a
                  v-for="a in ticket.attachments"
                  :key="a.id"
                  class="hd-row"
                  :href="`/api/v1/tickets/${ticket.id}/attachments/${a.id}/download`"
                  target="_blank"
                  style="gap:6px;color:var(--c-primary);font-size:12.5px;text-decoration:none"
                >
                  <span class="material-icons" style="font-size:15px">attach_file</span>
                  {{ a.original_name }} · {{ formatSize(a.size) }}
                </a>
              </div>
            </div>
          </div>

          <!-- Comments -->
          <div
            v-for="c in ticket.comments"
            :key="c.id"
            class="hd-msg"
            :class="{ 'hd-msg-internal': c.is_internal }"
            style="margin-bottom:12px"
          >
            <AvatarCircle :name="c.author.display_name" size="36" />
            <div class="hd-msg-body">
              <div class="hd-msg-header">
                <span class="hd-msg-author">{{ c.author.display_name }}</span>
                <span v-if="c.is_internal" class="hd-internal-tag">NOTA INTERNA</span>
                <span class="hd-msg-time">{{ formatDate(c.created_at) }}</span>
              </div>
              <div class="hd-msg-bubble">{{ c.body }}</div>
            </div>
          </div>

          <!-- Reply box -->
          <div class="hd-card" style="padding:20px">
            <div style="font-weight:600;font-size:14px;margin-bottom:12px">Responder</div>
            <textarea
              class="hd-textarea"
              v-model="newComment"
              rows="4"
              placeholder="Escreva a sua resposta..."
            ></textarea>
            <div class="hd-row" style="justify-content:space-between;margin-top:12px">
              <label v-if="auth.isStaff" class="hd-row" style="gap:8px;cursor:pointer;font-size:13px;color:var(--c-muted)">
                <div class="hd-toggle-wrap" @click="isInternal = !isInternal">
                  <div class="hd-toggle-track" :class="{ on: isInternal }">
                    <div class="hd-toggle-thumb"></div>
                  </div>
                </div>
                Nota interna
              </label>
              <div v-else></div>
              <button
                class="hd-btn hd-btn-primary"
                :disabled="!newComment.trim() || commenting"
                @click="onAddComment"
              >
                <span class="material-icons" style="font-size:16px">send</span>
                {{ commenting ? 'A enviar...' : 'Enviar' }}
              </button>
            </div>
            <div v-if="commentError" style="color:#DC2626;font-size:13px;margin-top:8px">{{ commentError }}</div>
          </div>
        </div>

        <!-- Right: details + timeline -->
        <div style="display:flex;flex-direction:column;gap:16px">
          <!-- Details card -->
          <div class="hd-card" style="padding:20px">
            <div style="font-weight:600;font-size:14px;margin-bottom:16px">Detalhes</div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Solicitante</div>
              <div class="hd-row" style="gap:6px">
                <AvatarCircle :name="ticket.creator.display_name" size="22" />
                <span style="font-size:13px">{{ ticket.creator.display_name }}</span>
              </div>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Atribuído a</div>
              <div v-if="auth.isStaff" class="hd-row" style="gap:6px;align-items:center">
                <input
                  class="hd-input"
                  style="font-size:12px;padding:5px 8px;min-width:220px"
                  v-model="assigneeSearch"
                  list="ticket-assignees"
                  placeholder="Pesquisar técnico ou administrador"
                  @change="onAssigneeSearchChange"
                />
                <datalist id="ticket-assignees">
                  <option v-for="u in staffUsers" :key="u.id" :value="userOptionLabel(u)" />
                </datalist>
                <button class="hd-icon-btn" title="Remover atribuição" @click="clearAssignee">
                  <span class="material-icons" style="font-size:15px">close</span>
                </button>
              </div>
              <div v-else style="font-size:13px">
                {{ ticket.assignee ? ticket.assignee.display_name : '—' }}
              </div>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Estado</div>
              <div v-if="auth.isStaff">
                <select class="hd-select" style="font-size:12px;padding:4px 8px" v-model="ticketStatus" @change="onStatusChange">
                  <option v-for="o in statusOpts" :key="o.v" :value="o.v">{{ o.l }}</option>
                </select>
              </div>
              <span v-else class="hd-status" :class="ticket.status">{{ statusLabel(ticket.status) }}</span>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Prioridade</div>
              <PriorityBadge :priority="ticket.priority" />
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Categoria</div>
              <div class="hd-row" style="gap:6px">
                <span class="material-icons" :style="{ color: ticket.category.color, fontSize: '14px' }">{{ ticket.category.icon }}</span>
                <span style="font-size:13px">{{ ticket.category.name }}</span>
              </div>
            </div>

            <div v-if="ticket.school" class="hd-detail-row">
              <div class="hd-detail-label">Escola</div>
              <span style="font-size:13px">{{ ticket.school.name }}</span>
            </div>

            <div class="hd-detail-row">
              <div class="hd-detail-label">Aberto</div>
              <span style="font-size:13px">{{ formatDate(ticket.created_at) }}</span>
            </div>

            <div class="hd-detail-row" style="border-bottom:none">
              <div class="hd-detail-label">SLA</div>
              <span style="font-size:13px">{{ ticket.category.sla_hours }}h</span>
            </div>
          </div>

          <!-- Timeline -->
          <div class="hd-card" style="padding:20px">
            <div style="font-weight:600;font-size:14px;margin-bottom:16px">Histórico</div>
            <div class="hd-timeline">
              <div v-for="(step, idx) in timeline" :key="step.status" class="hd-tl-item">
                <div class="hd-tl-spine">
                  <div class="hd-tl-dot" :class="{ done: isStatusDone(step.status), active: ticket.status === step.status }"></div>
                  <div v-if="idx < timeline.length - 1" class="hd-tl-line"></div>
                </div>
                <div class="hd-tl-label" :class="{ done: isStatusDone(step.status) }">{{ step.label }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getTicket, addComment, adminUpdateTicket } from '../api/tickets'
import { getUsers } from '../api/users'
import { useAuthStore } from '../stores/auth'
import AvatarCircle from '../components/AvatarCircle.vue'
import PriorityBadge from '../components/PriorityBadge.vue'

const auth = useAuthStore()
const route = useRoute()
const ticket = ref<any>(null)
const newComment = ref('')
const isInternal = ref(false)
const commenting = ref(false)
const commentError = ref('')
const staffUsers = ref<any[]>([])
const assigneeId = ref<number | null>(null)
const assigneeSearch = ref('')
const ticketStatus = ref('')

const statusOpts = [
  { v: 'open', l: 'Aberto' }, { v: 'assigned', l: 'Atribuído' },
  { v: 'in_progress', l: 'Em Curso' }, { v: 'resolved', l: 'Resolvido' }, { v: 'closed', l: 'Fechado' },
]

const timeline = [
  { status: 'open', label: 'Aberto' },
  { status: 'assigned', label: 'Atribuído' },
  { status: 'in_progress', label: 'Em Curso' },
  { status: 'resolved', label: 'Resolvido' },
  { status: 'closed', label: 'Fechado' },
]

const statusOrder = ['open', 'assigned', 'in_progress', 'resolved', 'closed']

function isStatusDone(status: string) {
  const current = statusOrder.indexOf(ticket.value?.status)
  return statusOrder.indexOf(status) <= current
}

onMounted(async () => {
  await load()
  if (auth.isStaff) {
    const users = await getUsers()
    staffUsers.value = users.filter((u: any) => u.is_active && (u.role === 'technician' || u.role === 'admin'))
  }
})

async function load() {
  const t = await getTicket(Number(route.params.id))
  ticket.value = t
  assigneeId.value = t.assignee?.id ?? null
  assigneeSearch.value = t.assignee ? userOptionLabel(t.assignee) : ''
  ticketStatus.value = t.status
}

async function onAddComment() {
  if (!newComment.value.trim()) return
  commenting.value = true
  commentError.value = ''
  try {
    await addComment(ticket.value.id, newComment.value, isInternal.value)
    newComment.value = ''
    isInternal.value = false
    await load()
  } catch {
    commentError.value = 'Erro ao enviar resposta'
  } finally {
    commenting.value = false
  }
}

async function onStatusChange() {
  try {
    await adminUpdateTicket(ticket.value.id, { status: ticketStatus.value })
    await load()
  } catch { ticketStatus.value = ticket.value.status }
}

async function onAssigneeChange() {
  try {
    await adminUpdateTicket(ticket.value.id, { assignee_id: assigneeId.value })
    await load()
  } catch { assigneeId.value = ticket.value.assignee?.id ?? null }
}

async function onAssigneeSearchChange() {
  const selected = staffUsers.value.find((u: any) => userOptionLabel(u) === assigneeSearch.value)
  if (!selected) {
    assigneeSearch.value = ticket.value.assignee ? userOptionLabel(ticket.value.assignee) : ''
    return
  }
  assigneeId.value = selected.id
  await onAssigneeChange()
}

async function clearAssignee() {
  assigneeId.value = null
  assigneeSearch.value = ''
  await onAssigneeChange()
}

function userOptionLabel(u: any) {
  const role = u.role === 'admin' ? 'Administrador' : 'Técnico'
  return `${u.display_name} — ${u.email} (${role})`
}

function statusLabel(s: string) {
  return { open: 'Aberto', assigned: 'Atribuído', in_progress: 'Em Curso', resolved: 'Resolvido', closed: 'Fechado' }[s] ?? s
}

function formatDate(d: string) {
  return new Date(d).toLocaleString('pt-PT', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatSize(size: number) {
  return size >= 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)} MB` : `${Math.round(size / 1024)} KB`
}
</script>
