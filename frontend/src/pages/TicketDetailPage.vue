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

      <div class="ticket-detail-grid">
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
              <div v-if="ticket.attachments?.length" style="margin-top:10px">
                <!-- image thumbnails -->
                <div v-if="imageAttachments.length" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px">
                  <button
                    v-for="a in imageAttachments"
                    :key="a.id"
                    type="button"
                    class="attach-thumb"
                    :title="a.original_name"
                    @click="openLightbox(a)"
                  >
                    <img v-if="attachBlobUrls[a.id]" :src="attachBlobUrls[a.id]" :alt="a.original_name" style="width:100%;height:100%;object-fit:cover" />
                    <span v-else class="material-icons" style="color:var(--c-muted);font-size:28px">image</span>
                  </button>
                </div>
                <!-- pdf / other files -->
                <div v-for="a in fileAttachments" :key="a.id" style="margin-bottom:4px">
                  <button
                    type="button"
                    class="hd-row"
                    style="gap:6px;color:var(--c-primary);font-size:12.5px;background:none;border:none;cursor:pointer;padding:0;text-align:left"
                    @click="openFile(a)"
                  >
                    <span class="material-icons" style="font-size:15px">picture_as_pdf</span>
                    {{ a.original_name }} · {{ formatSize(a.size) }}
                  </button>
                </div>
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
                <button v-if="canEditComment(c)" class="msg-action" @click="startEditComment(c)">Editar</button>
                <button v-if="canEditComment(c)" class="msg-action danger" @click="onDeleteComment(c)">Apagar</button>
              </div>
              <div v-if="editingCommentId === c.id" class="comment-edit-box">
                <textarea class="hd-textarea" v-model="editingCommentBody" rows="3"></textarea>
                <div class="hd-row" style="justify-content:flex-end;gap:8px;margin-top:8px">
                  <button class="hd-btn hd-btn-outline" @click="cancelEditComment">Cancelar</button>
                  <button class="hd-btn hd-btn-primary" @click="saveEditedComment(c)">Guardar</button>
                </div>
              </div>
              <div v-else class="hd-msg-bubble">{{ c.body }}</div>
            </div>
          </div>

          <!-- Reply box -->
          <div class="hd-card" style="padding:20px">
            <div style="font-weight:600;font-size:14px;margin-bottom:12px">Responder</div>
            <div v-if="auth.isStaff" class="quick-replies">
              <button v-for="reply in quickReplies" :key="reply.label" class="quick-reply" type="button" @click="newComment = reply.body">
                {{ reply.label }}
              </button>
            </div>
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
        <div class="ticket-side-panel">
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

            <div v-if="canManageEmailNotifications" class="email-notification-panel">
              <div>
                <strong>Atualizações por email</strong>
                <span>{{ ticket.creator_email_notifications ? 'Ativas para o autor' : 'Desativadas para o autor' }}</span>
              </div>
              <button
                class="email-toggle-btn"
                :class="{ active: ticket.creator_email_notifications }"
                :disabled="savingEmailPreference"
                @click="toggleEmailNotifications"
              >
                <span class="material-icons">{{ ticket.creator_email_notifications ? 'notifications_active' : 'notifications_off' }}</span>
                {{ ticket.creator_email_notifications ? 'Desativar emails' : 'Ativar emails' }}
              </button>
            </div>

            <div class="hd-detail-row" style="flex-direction:column;align-items:flex-start;gap:8px">
              <div class="hd-detail-label">Em conhecimento</div>
              <div v-if="ticket.watchers?.length" class="watcher-list" style="width:100%">
                <div v-for="user in ticket.watchers" :key="user.id" class="watcher-mini">
                  <AvatarCircle :name="user.display_name" size="22" />
                  <span>{{ user.display_name }}</span>
                  <button
                    v-if="canEditWatchers"
                    class="watcher-remove-btn"
                    @click="onRemoveWatcher(user.id)"
                    title="Remover"
                  >
                    <span class="material-icons" style="font-size:14px">close</span>
                  </button>
                </div>
              </div>
              <span v-else style="font-size:13px;color:var(--c-muted)">Nenhuma pessoa adicionada.</span>
              <div v-if="canEditWatchers" class="watcher-add-row">
                <input
                  class="hd-input"
                  style="flex:1;font-size:12px;padding:5px 8px"
                  v-model="watcherSearch"
                  list="watcher-users-list"
                  placeholder="Pesquisar por email..."
                  autocomplete="off"
                />
                <datalist id="watcher-users-list">
                  <option v-for="u in filteredWatcherUsers" :key="u.id" :value="u.email" :label="u.display_name" />
                </datalist>
                <button
                  class="hd-btn hd-btn-primary"
                  style="padding:5px 12px;font-size:12px;white-space:nowrap"
                  :disabled="!resolvedWatcherId || addingWatcher"
                  @click="onAddWatcher"
                >
                  Adicionar
                </button>
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
                  placeholder="Pesquisar técnico"
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
              <div class="hd-detail-label">Grupo</div>
              <div v-if="auth.isStaff">
                <select class="hd-select" style="font-size:12px;padding:4px 8px" v-model="groupId" @change="onGroupChange">
                  <option :value="''">— Sem grupo</option>
                  <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
                </select>
              </div>
              <div v-else style="font-size:13px">{{ ticket.group?.name || '—' }}</div>
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

            <div v-if="auth.isStaff" class="provider-escalation">
              <button class="hd-btn hd-btn-outline" style="width:100%;justify-content:center" :disabled="escalating" @click="onEscalateTicket">
                <span class="material-icons" style="font-size:16px">outgoing_mail</span>
                {{ escalating ? 'A escalar...' : 'Escalar para fornecedor' }}
              </button>
              <p v-if="escalationMessage" :class="{ error: escalationError }">{{ escalationMessage }}</p>
            </div>
          </div>

          <!-- Timeline -->
          <div class="hd-card" style="padding:20px">
            <div style="font-weight:600;font-size:14px;margin-bottom:16px">Histórico</div>
            <div v-if="ticket.events?.length" class="event-list">
              <div v-for="event in ticket.events" :key="event.id" class="event-item">
                <div class="event-dot"></div>
                <div>
                  <div class="event-message">{{ event.message }}</div>
                  <div class="event-meta">
                    {{ formatDate(event.created_at) }}
                    <span v-if="event.actor"> · {{ event.actor.display_name }}</span>
                  </div>
                </div>
              </div>
            </div>
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

  <!-- Lightbox -->
  <Teleport to="body">
    <div v-if="lightboxSrc" class="hd-lightbox" @click="lightboxSrc = null">
      <button class="hd-lightbox-close" @click="lightboxSrc = null">
        <span class="material-icons">close</span>
      </button>
      <img :src="lightboxSrc" class="hd-lightbox-img" @click.stop />
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { getTicket, addComment, adminUpdateTicket, updateTicket, updateComment, deleteComment, escalateTicket, addWatcher, removeWatcher, downloadAttachment, fetchAttachmentBlob } from '../api/tickets'
import { getGroups, getUsers } from '../api/users'
import { useAuthStore } from '../stores/auth'
import AvatarCircle from '../components/AvatarCircle.vue'
import PriorityBadge from '../components/PriorityBadge.vue'
import { formatDateTime } from '../utils/dates'

const auth = useAuthStore()
const route = useRoute()
const ticket = ref<any>(null)
const newComment = ref('')
const isInternal = ref(false)
const commenting = ref(false)
const commentError = ref('')
const staffUsers = ref<any[]>([])
const groups = ref<any[]>([])
const assigneeId = ref<number | null>(null)
const assigneeSearch = ref('')
const groupId = ref('')
const ticketStatus = ref('')
const editingCommentId = ref<number | null>(null)
const editingCommentBody = ref('')
const escalating = ref(false)
const escalationMessage = ref('')
const escalationError = ref(false)
const savingEmailPreference = ref(false)
const watcherSearch = ref('')
const addingWatcher = ref(false)
const allUsers = ref<any[]>([])
const attachBlobUrls = ref<Record<number, string>>({})
const lightboxSrc = ref<string | null>(null)

const imageAttachments = computed(() =>
  (ticket.value?.attachments ?? []).filter((a: any) => (a.content_type as string).startsWith('image/'))
)
const fileAttachments = computed(() =>
  (ticket.value?.attachments ?? []).filter((a: any) => !(a.content_type as string).startsWith('image/'))
)

const canManageEmailNotifications = computed(() => {
  if (!ticket.value || !auth.user) return false
  return auth.isAdmin || ticket.value.creator?.id === auth.user.id
})

const canEditWatchers = computed(() => {
  if (!ticket.value || !auth.user) return false
  return auth.isStaff || ticket.value.creator?.id === auth.user.id
})

const availableWatcherUsers = computed(() => {
  const addedIds = new Set((ticket.value?.watchers ?? []).map((w: any) => w.id))
  return allUsers.value.filter(u => !addedIds.has(u.id) && u.id !== ticket.value?.creator?.id)
})

const filteredWatcherUsers = computed(() => {
  const term = watcherSearch.value.trim().toLowerCase()
  if (!term) return availableWatcherUsers.value
  return availableWatcherUsers.value.filter(u => String(u.email || '').toLowerCase().includes(term))
})

const resolvedWatcherId = computed(() => {
  const term = watcherSearch.value.trim().toLowerCase()
  const exactMatch = availableWatcherUsers.value.find(u => String(u.email || '').toLowerCase() === term)
  if (exactMatch) return exactMatch.id
  if (filteredWatcherUsers.value.length === 1) return filteredWatcherUsers.value[0].id
  return null
})

const statusOpts = [
  { v: 'open', l: 'Aberto' }, { v: 'assigned', l: 'Atribuído' },
  { v: 'in_progress', l: 'Em Curso' }, { v: 'waiting_user', l: 'A aguardar utilizador' },
  { v: 'resolved', l: 'Resolvido' }, { v: 'closed', l: 'Fechado' },
]

const timeline = [
  { status: 'open', label: 'Aberto' },
  { status: 'assigned', label: 'Atribuído' },
  { status: 'in_progress', label: 'Em Curso' },
  { status: 'waiting_user', label: 'A aguardar utilizador' },
  { status: 'resolved', label: 'Resolvido' },
  { status: 'closed', label: 'Fechado' },
]

const statusOrder = ['open', 'assigned', 'in_progress', 'waiting_user', 'resolved', 'closed']
const quickReplies = [
  { label: 'Pedido recebido', body: 'O pedido foi recebido e está em análise. Daremos feedback assim que possível.' },
  { label: 'Preciso de mais dados', body: 'Para conseguirmos avançar, pode indicar mais detalhes sobre o problema e, se possível, anexar uma captura de ecrã?' },
  { label: 'Resolvido', body: 'A situação foi resolvida. Se o problema voltar a ocorrer, responda a este ticket com mais informação.' },
]

function isStatusDone(status: string) {
  const current = statusOrder.indexOf(ticket.value?.status)
  return statusOrder.indexOf(status) <= current
}

onMounted(async () => {
  await load()
  loadImageBlobs()
  const isCreator = ticket.value?.creator?.id === auth.user?.id
  if (auth.isStaff) {
    const [users, grps] = await Promise.all([getUsers(), getGroups()])
    staffUsers.value = users.filter((u: any) => u.is_active && u.role === 'technician')
    groups.value = grps
    allUsers.value = users.filter((u: any) => u.is_active)
  } else if (isCreator) {
    allUsers.value = (await getUsers()).filter((u: any) => u.is_active)
  }
})

onUnmounted(() => {
  Object.values(attachBlobUrls.value).forEach(url => URL.revokeObjectURL(url))
})

async function load() {
  const t = await getTicket(Number(route.params.id))
  ticket.value = t
  assigneeId.value = t.assignee?.id ?? null
  assigneeSearch.value = t.assignee ? userOptionLabel(t.assignee) : ''
  groupId.value = t.group?.id ? String(t.group.id) : ''
  ticketStatus.value = t.status
}

function loadImageBlobs() {
  const attachments: any[] = ticket.value?.attachments ?? []
  for (const a of attachments) {
    if ((a.content_type as string).startsWith('image/') && !attachBlobUrls.value[a.id]) {
      fetchAttachmentBlob(ticket.value.id, a.id)
        .then(url => { attachBlobUrls.value[a.id] = url })
        .catch(() => {})
    }
  }
}

async function openLightbox(a: { id: number; content_type: string }) {
  let url = attachBlobUrls.value[a.id]
  if (!url) {
    url = await fetchAttachmentBlob(ticket.value.id, a.id)
    attachBlobUrls.value[a.id] = url
  }
  lightboxSrc.value = url
}

async function openFile(a: { id: number; original_name: string }) {
  const url = await fetchAttachmentBlob(ticket.value.id, a.id)
  window.open(url, '_blank')
  setTimeout(() => URL.revokeObjectURL(url), 30000)
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

async function onGroupChange() {
  try {
    await adminUpdateTicket(ticket.value.id, { group_id: groupId.value ? Number(groupId.value) : null })
    await load()
  } catch {
    groupId.value = ticket.value.group?.id ? String(ticket.value.group.id) : ''
  }
}

async function toggleEmailNotifications() {
  if (!ticket.value || savingEmailPreference.value) return
  savingEmailPreference.value = true
  try {
    const payload = { creator_email_notifications: !ticket.value.creator_email_notifications }
    ticket.value = auth.isAdmin
      ? await adminUpdateTicket(ticket.value.id, payload)
      : await updateTicket(ticket.value.id, payload)
  } finally {
    savingEmailPreference.value = false
  }
}

function canEditComment(comment: any) {
  return auth.isStaff || comment.author?.id === auth.user?.id
}

function startEditComment(comment: any) {
  editingCommentId.value = comment.id
  editingCommentBody.value = comment.body
}

function cancelEditComment() {
  editingCommentId.value = null
  editingCommentBody.value = ''
}

async function saveEditedComment(comment: any) {
  if (!editingCommentBody.value.trim()) return
  await updateComment(ticket.value.id, comment.id, editingCommentBody.value)
  cancelEditComment()
  await load()
}

async function onDeleteComment(comment: any) {
  if (!confirm('Apagar esta resposta?')) return
  await deleteComment(ticket.value.id, comment.id)
  await load()
}

async function onAddWatcher() {
  if (!resolvedWatcherId.value || addingWatcher.value) return
  addingWatcher.value = true
  try {
    ticket.value = await addWatcher(ticket.value.id, resolvedWatcherId.value)
    watcherSearch.value = ''
  } finally {
    addingWatcher.value = false
  }
}

async function onRemoveWatcher(userId: number) {
  ticket.value = await removeWatcher(ticket.value.id, userId)
}

async function onEscalateTicket() {
  if (!confirm('Escalar este ticket para o fornecedor externo configurado?')) return
  escalating.value = true
  escalationMessage.value = ''
  escalationError.value = false
  try {
    ticket.value = await escalateTicket(ticket.value.id)
    escalationMessage.value = 'Ticket escalado e email enviado ao fornecedor.'
  } catch (error: any) {
    escalationError.value = true
    escalationMessage.value = error?.response?.data?.detail || 'Não foi possível escalar o ticket. Verifica o email do fornecedor nas configurações.'
  } finally {
    escalating.value = false
  }
}

function userOptionLabel(u: any) {
  return `${u.display_name} — ${u.email} (Técnico)`
}

function watcherOptionLabel(u: any) {
  return `${u.display_name} — ${u.email} (@${u.username})`
}

function watcherSearchText(u: any) {
  const emailPrefix = String(u.email || '').split('@')[0]
  return `${u.display_name} ${u.email} ${emailPrefix} ${u.username}`.toLowerCase()
}

function statusLabel(s: string) {
  return { open: 'Aberto', assigned: 'Atribuído', in_progress: 'Em Curso', waiting_user: 'A aguardar utilizador', resolved: 'Resolvido', closed: 'Fechado' }[s] ?? s
}

function formatDate(d: string) {
  return formatDateTime(d)
}

async function onDownloadAttachment(a: { id: number; original_name: string }) {
  await downloadAttachment(ticket.value.id, a.id, a.original_name)
}

function formatSize(size: number) {
  return size >= 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)} MB` : `${Math.round(size / 1024)} KB`
}
</script>

<style scoped>
.ticket-detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 20px;
  align-items: start;
}

.ticket-side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.msg-action {
  border: 0;
  background: transparent;
  color: var(--c-primary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  padding: 2px 4px;
}

.msg-action.danger {
  color: #dc2626;
}

.comment-edit-box {
  margin-top: 8px;
}

.quick-replies {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.quick-reply {
  border: 1px solid var(--c-border);
  background: var(--c-surface);
  color: var(--c-text);
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 9px;
}

.quick-reply:hover {
  border-color: var(--c-primary);
  color: var(--c-primary);
}

.watcher-list {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 0;
}

.watcher-mini {
  align-items: center;
  display: grid;
  gap: 6px;
  grid-template-columns: 22px minmax(0, 1fr) auto;
}

.watcher-mini span {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.watcher-remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--c-muted);
  padding: 2px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  line-height: 1;
  transition: background .15s, color .15s;
}

.watcher-remove-btn:hover {
  background: #FEE2E2;
  color: #DC2626;
}

.watcher-add-row {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.provider-escalation {
  border-top: 1px solid var(--c-border);
  margin-top: 4px;
  padding-top: 16px;
}

.email-notification-panel {
  align-items: center;
  background: rgba(61, 82, 213, 0.06);
  border: 1px solid rgba(61, 82, 213, 0.18);
  border-radius: 9px;
  display: grid;
  gap: 10px;
  margin: 0 0 14px;
  padding: 12px;
}

.email-notification-panel strong,
.email-notification-panel span {
  display: block;
}

.email-notification-panel strong {
  font-size: 13px;
}

.email-notification-panel span {
  color: var(--c-muted);
  font-size: 12px;
  margin-top: 2px;
}

.email-toggle-btn {
  align-items: center;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  color: var(--c-muted);
  cursor: pointer;
  display: inline-flex;
  font-size: 12px;
  font-weight: 800;
  gap: 7px;
  justify-content: center;
  padding: 9px 10px;
  width: 100%;
}

.email-toggle-btn.active {
  background: rgba(22, 163, 74, 0.1);
  border-color: rgba(22, 163, 74, 0.24);
  color: #15803D;
}

.email-toggle-btn .material-icons {
  font-size: 16px;
}

.provider-escalation p {
  color: #16A34A;
  font-size: 12px;
  margin: 8px 0 0;
}

.provider-escalation p.error {
  color: #DC2626;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--c-border);
}

.event-item {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.event-dot {
  width: 8px;
  height: 8px;
  margin-top: 7px;
  border-radius: 50%;
  background: var(--c-primary);
}

.event-message {
  font-size: 13px;
  font-weight: 700;
}

.event-meta {
  color: var(--c-muted);
  font-size: 12px;
}

@media (max-width: 900px) {
  .ticket-detail-grid {
    grid-template-columns: 1fr;
  }

  .ticket-side-panel {
    order: -1;
  }

  :deep(.hd-msg) {
    grid-template-columns: 32px minmax(0, 1fr);
  }

  :deep(.hd-msg-header) {
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 6px;
  }
}

.attach-thumb {
  width: 80px;
  height: 80px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  background: var(--c-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: opacity .15s;
}

.attach-thumb:hover {
  opacity: .85;
}

</style>

<style>
.hd-lightbox {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, .88);
  display: flex;
  align-items: center;
  justify-content: center;
}

.hd-lightbox-img {
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 6px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, .5);
  object-fit: contain;
}

.hd-lightbox-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(255, 255, 255, .15);
  border: none;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  transition: background .15s;
}

.hd-lightbox-close:hover {
  background: rgba(255, 255, 255, .25);
}
</style>
