<template>
  <div class="hd-page">
    <div style="font-size:12px;color:var(--c-muted);margin-bottom:6px">
      <router-link to="/tickets" style="color:var(--c-muted);text-decoration:none">Tickets</router-link>
      / <span>T-{{ ticket?.id }}</span>
    </div>

    <div v-if="!ticket" style="padding:80px;text-align:center;color:var(--c-muted)">A carregar...</div>

    <template v-else>
      <div style="margin-bottom:24px">
        <div class="hd-row" style="align-items:flex-start;gap:8px;margin-bottom:4px">
          <div style="flex:1;min-width:0">
            <h1 v-if="!editingContent" style="font-size:22px;margin:0">{{ ticket.title }}</h1>
            <input v-else class="hd-input" v-model="editTitle" style="font-size:18px;font-weight:600;width:100%" />
          </div>
          <div class="hd-row" style="gap:6px;flex-shrink:0;margin-top:4px">
            <template v-if="!editingContent">
              <button v-if="auth.isAdmin" class="hd-icon-btn" title="Editar assunto e descrição" @click="startEditContent">
                <span class="material-icons" style="font-size:18px">edit</span>
              </button>
              <span class="hd-status" :class="ticket.status">{{ statusLabel(ticket.status) }}</span>
              <PriorityBadge :priority="ticket.priority" />
              <span v-if="isEscalated && !isDeescalated" class="escalated-badge" title="Ticket escalado para o fornecedor externo">
                <span class="material-icons" style="font-size:13px;vertical-align:middle">open_in_new</span>
                Fornecedor
              </span>
              <button
                v-if="isEscalated && !isDeescalated && auth.isStaff"
                class="hd-btn hd-btn-outline"
                style="font-size:12px;padding:3px 10px"
                :disabled="deescalating"
                title="Marcar como resolvido pelo fornecedor"
                @click="onDeescalate"
              >
                <span class="material-icons" style="font-size:13px">check_circle</span>
                {{ deescalating ? '...' : 'Fornecedor resolveu' }}
              </button>
              <span v-if="isDeescalated" class="deescalated-badge">
                <span class="material-icons" style="font-size:13px;vertical-align:middle">check_circle</span>
                Resolvido pelo fornecedor
              </span>
            </template>
            <template v-else>
              <button class="hd-btn hd-btn-outline" @click="cancelEditContent">Cancelar</button>
              <button class="hd-btn hd-btn-primary" :disabled="savingContent" @click="saveContent">
                {{ savingContent ? 'A guardar...' : 'Guardar' }}
              </button>
            </template>
          </div>
        </div>
        <div style="font-size:13px;color:var(--c-muted)">
          Aberto por <strong>{{ ticket.creator.display_name }}</strong> · {{ formatDate(ticket.created_at) }}
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
              <div v-if="!editingContent" class="hd-msg-bubble">{{ ticket.description }}</div>
              <textarea v-else class="hd-textarea" v-model="editDescription" rows="6" style="margin-top:4px"></textarea>
              <div v-if="contentError" style="color:#DC2626;font-size:12px;margin-top:6px">{{ contentError }}</div>
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
              <button
                v-for="reply in quickReplies"
                :key="reply.label"
                class="quick-reply"
                :class="{ 'quick-reply-active': reply.autoClose && autoCloseOnSend }"
                type="button"
                @click="newComment = reply.body; autoCloseOnSend = !!reply.autoClose"
              >
                {{ reply.label }}
              </button>
            </div>
            <textarea
              class="hd-textarea"
              v-model="newComment"
              rows="4"
              placeholder="Escreva a sua resposta..."
            ></textarea>
            <!-- Hidden file input -->
            <input
              ref="commentFileInput"
              type="file"
              style="display:none"
              accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip"
              @change="commentFile = ($event.target as HTMLInputElement).files?.[0] ?? null"
            />
            <!-- Selected file preview -->
            <div v-if="commentFile" class="reply-file-preview">
              <span class="material-icons" style="font-size:15px;color:var(--c-primary)">attach_file</span>
              <span style="font-size:12px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ commentFile.name }}</span>
              <button type="button" class="hd-icon-btn" style="padding:2px" title="Remover" @click="commentFile = null; if (commentFileInput) commentFileInput.value = ''">
                <span class="material-icons" style="font-size:14px">close</span>
              </button>
            </div>
            <div class="hd-row" style="justify-content:space-between;margin-top:12px">
              <div class="hd-row" style="gap:8px">
                <label v-if="auth.isStaff" class="hd-row" style="gap:8px;cursor:pointer;font-size:13px;color:var(--c-muted)">
                  <div class="hd-toggle-wrap" @click="isInternal = !isInternal">
                    <div class="hd-toggle-track" :class="{ on: isInternal }">
                      <div class="hd-toggle-thumb"></div>
                    </div>
                  </div>
                  Nota interna
                </label>
                <button
                  type="button"
                  class="hd-btn hd-btn-outline"
                  style="font-size:12px;padding:5px 10px"
                  title="Anexar ficheiro"
                  @click="commentFileInput?.click()"
                >
                  <span class="material-icons" style="font-size:15px">attach_file</span>
                  Anexar
                </button>
              </div>
              <button
                class="hd-btn hd-btn-primary"
                :disabled="(!newComment.trim() && !commentFile) || commenting"
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
                <div class="person-search">
                  <input
                    class="hd-input"
                    v-model="watcherSearch"
                    placeholder="Pesquisar por nome ou email..."
                    autocomplete="off"
                  />
                  <div v-if="watcherSearch.trim().length >= 2 && (watcherLoading || filteredWatcherUsers.length)" class="person-search-menu">
                    <div v-if="watcherLoading" class="person-search-empty">A pesquisar...</div>
                    <button v-for="u in filteredWatcherUsers" :key="u.id" type="button" @mousedown.prevent="addWatcherCandidate(u)">
                      <AvatarCircle :name="u.display_name" size="22" />
                      <span>
                        <strong>{{ u.display_name }}</strong>
                        <small>{{ u.email }}</small>
                      </span>
                    </button>
                  </div>
                </div>
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
              <div v-if="auth.isStaff" class="assignee-editor">
                <div v-if="assignedTechnicians.length" class="assignee-chip-list">
                  <span v-for="user in assignedTechnicians" :key="user.id" class="assignee-chip">
                    <AvatarCircle :name="user.display_name" size="20" />
                    {{ user.display_name }}
                    <button type="button" title="Remover técnico" @click="removeAssignee(user.id)">
                      <span class="material-icons">close</span>
                    </button>
                  </span>
                </div>
                <span v-else class="muted-mini">— Nenhum técnico atribuído</span>
                <div class="person-search">
                  <input
                    class="hd-input"
                    v-model="assigneeSearch"
                    placeholder="Adicionar técnico..."
                    autocomplete="off"
                    @focus="assigneeSearchOpen = true"
                    @click="assigneeSearchOpen = true"
                    @keydown.escape="assigneeSearchOpen = false"
                  />
                  <div v-if="assigneeSearchOpen && filteredAssigneeUsers.length" class="person-search-menu">
                    <button v-for="u in filteredAssigneeUsers" :key="u.id" type="button" @mousedown.prevent="addAssignee(u)">
                      <AvatarCircle :name="u.display_name" size="22" />
                      <span>
                        <strong>{{ u.display_name }}</strong>
                        <small>{{ u.email }}</small>
                      </span>
                    </button>
                  </div>
                </div>
              </div>
              <div v-else style="font-size:13px">
                {{ assignedTechnicianNames || '—' }}
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
              <div class="hd-detail-label">Tempo de resposta</div>
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
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getTicket, addComment, adminUpdateTicket, updateTicket, updateComment, deleteComment, escalateTicket, deescalateTicket, addWatcher, removeWatcher, downloadAttachment, fetchAttachmentBlob, uploadTicketAttachment } from '../api/tickets'
import { getGroups, getUsers, searchUsers } from '../api/users'
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
const assigneeSearch = ref('')
const assigneeSearchOpen = ref(false)
const groupId = ref('')
const ticketStatus = ref('')
const editingCommentId = ref<number | null>(null)
const editingCommentBody = ref('')
const escalating = ref(false)
const escalationMessage = ref('')
const escalationError = ref(false)
const savingEmailPreference = ref(false)
const watcherSearch = ref('')
const watcherResults = ref<any[]>([])
const watcherLoading = ref(false)
const addingWatcher = ref(false)
let watcherSearchTimer: ReturnType<typeof setTimeout> | null = null
const attachBlobUrls = ref<Record<number, string>>({})
const lightboxSrc = ref<string | null>(null)
const autoCloseOnSend = ref(false)
const commentFile = ref<File | null>(null)
const commentFileInput = ref<HTMLInputElement | null>(null)
const editingContent = ref(false)
const editTitle = ref('')
const editDescription = ref('')
const savingContent = ref(false)
const contentError = ref('')

const imageAttachments = computed(() =>
  (ticket.value?.attachments ?? []).filter((a: any) => (a.content_type as string).startsWith('image/'))
)
const fileAttachments = computed(() =>
  (ticket.value?.attachments ?? []).filter((a: any) => !(a.content_type as string).startsWith('image/'))
)

const isEscalated = computed(() =>
  (ticket.value?.events ?? []).some((e: any) => e.event_type === 'escalated')
)
const isDeescalated = computed(() =>
  (ticket.value?.events ?? []).some((e: any) => e.event_type === 'deescalated')
)
const deescalating = ref(false)

const canManageEmailNotifications = computed(() => {
  if (!ticket.value || !auth.user) return false
  return auth.isAdmin || ticket.value.creator?.id === auth.user.id
})

const canEditWatchers = computed(() => {
  if (!ticket.value || !auth.user) return false
  return auth.isStaff || ticket.value.creator?.id === auth.user.id
})

const filteredWatcherUsers = computed(() => {
  const addedIds = new Set((ticket.value?.watchers ?? []).map((w: any) => w.id))
  return watcherResults.value.filter(u => !addedIds.has(u.id) && u.id !== ticket.value?.creator?.id).slice(0, 8)
})

const resolvedWatcherId = computed(() => {
  const term = watcherSearch.value.trim().toLowerCase()
  const exactMatch = filteredWatcherUsers.value.find(u =>
    String(u.email || '').toLowerCase() === term || String(u.username || '').toLowerCase() === term
  )
  if (exactMatch) return exactMatch.id
  if (filteredWatcherUsers.value.length === 1) return filteredWatcherUsers.value[0].id
  return null
})

const assignedTechnicians = computed(() => {
  const assignees = ticket.value?.assignees?.length ? ticket.value.assignees : (ticket.value?.assignee ? [ticket.value.assignee] : [])
  const seen = new Set<number>()
  return assignees.filter((user: any) => {
    if (!user?.id || seen.has(user.id)) return false
    seen.add(user.id)
    return true
  })
})

const assignedTechnicianNames = computed(() =>
  assignedTechnicians.value.map((user: any) => user.display_name).join(', ')
)

const filteredAssigneeUsers = computed(() => {
  const term = assigneeSearch.value.trim().toLowerCase()
  const assignedIds = new Set(assignedTechnicians.value.map((user: any) => user.id))
  return staffUsers.value
    .filter((user: any) => !assignedIds.has(user.id))
    .filter((user: any) => !term || userSearchText(user).includes(term))
    .slice(0, 12)
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
  { label: 'Resolvido ✓', body: 'A situação foi resolvida. Se o problema voltar a ocorrer, responda a este ticket com mais informação.', autoClose: true },
]

function isStatusDone(status: string) {
  const current = statusOrder.indexOf(ticket.value?.status)
  return statusOrder.indexOf(status) <= current
}

onMounted(async () => {
  await load()
  loadImageBlobs()
  if (auth.isStaff) {
    const [users, grps] = await Promise.all([getUsers(), getGroups()])
    staffUsers.value = users.filter(isAssignableTechnician)
    groups.value = grps
  }
})

onUnmounted(() => {
  if (watcherSearchTimer) clearTimeout(watcherSearchTimer)
  Object.values(attachBlobUrls.value).forEach(url => URL.revokeObjectURL(url))
})

watch(watcherSearch, value => {
  if (watcherSearchTimer) clearTimeout(watcherSearchTimer)
  const term = value.trim()
  if (term.length < 2) {
    watcherResults.value = []
    watcherLoading.value = false
    return
  }
  watcherLoading.value = true
  watcherSearchTimer = setTimeout(async () => {
    try {
      const results = await searchUsers(term, { limit: 8 })
      if (watcherSearch.value.trim() === term) watcherResults.value = results
    } finally {
      if (watcherSearch.value.trim() === term) watcherLoading.value = false
    }
  }, 250)
})

async function load() {
  const t = await getTicket(Number(route.params.id))
  ticket.value = t
  assigneeSearch.value = ''
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

function startEditContent() {
  editTitle.value = ticket.value.title
  editDescription.value = ticket.value.description
  contentError.value = ''
  editingContent.value = true
}

function cancelEditContent() {
  editingContent.value = false
  contentError.value = ''
}

async function saveContent() {
  if (!editTitle.value.trim() || !editDescription.value.trim()) {
    contentError.value = 'O assunto e a descrição não podem estar vazios.'
    return
  }
  savingContent.value = true
  contentError.value = ''
  try {
    ticket.value = await adminUpdateTicket(ticket.value.id, {
      title: editTitle.value.trim(),
      description: editDescription.value.trim(),
    })
    editingContent.value = false
  } catch (e: any) {
    contentError.value = e?.response?.data?.detail || 'Erro ao guardar as alterações.'
  } finally {
    savingContent.value = false
  }
}

async function onAddComment() {
  if (!newComment.value.trim() && !commentFile.value) return
  commenting.value = true
  commentError.value = ''
  const shouldClose = autoCloseOnSend.value && auth.isStaff
  autoCloseOnSend.value = false
  try {
    await addComment(ticket.value.id, newComment.value || '📎 Ficheiro anexado.', isInternal.value)
    newComment.value = ''
    isInternal.value = false
    if (commentFile.value) {
      await uploadTicketAttachment(ticket.value.id, commentFile.value)
      commentFile.value = null
      if (commentFileInput.value) commentFileInput.value.value = ''
    }
    if (shouldClose && ticket.value.status !== 'closed') {
      await adminUpdateTicket(ticket.value.id, { status: 'closed' })
    }
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

async function saveAssignees(ids: number[]) {
  try {
    ticket.value = await adminUpdateTicket(ticket.value.id, { assignee_ids: ids })
    assigneeSearch.value = ''
    assigneeSearchOpen.value = false
    await load()
  } catch {
    assigneeSearch.value = ''
    assigneeSearchOpen.value = false
  }
}

async function addAssignee(user: any) {
  const ids = Array.from(new Set([...assignedTechnicians.value.map((u: any) => u.id), user.id]))
  await saveAssignees(ids)
}

async function removeAssignee(userId: number) {
  await saveAssignees(assignedTechnicians.value.map((u: any) => u.id).filter((id: number) => id !== userId))
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

async function addWatcherCandidate(user: any) {
  if (!user?.id || addingWatcher.value) return
  addingWatcher.value = true
  try {
    ticket.value = await addWatcher(ticket.value.id, user.id)
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

async function onDeescalate() {
  if (!ticket.value) return
  deescalating.value = true
  try {
    ticket.value = await deescalateTicket(ticket.value.id)
  } finally {
    deescalating.value = false
  }
}

function userSearchText(u: any) {
  const emailPrefix = String(u.email || '').split('@')[0]
  return `${u.display_name} ${u.email} ${emailPrefix} ${u.username}`.toLowerCase()
}

function isAssignableTechnician(u: any) {
  return u?.is_active && (u.role === 'technician' || u.is_technician)
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
.escalated-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .4px;
  background: #FFF7ED;
  color: #C2410C;
  border: 1px solid #FED7AA;
  border-radius: 5px;
  padding: 3px 8px;
  white-space: nowrap;
}
:root.dark .escalated-badge {
  background: #431407;
  color: #FB923C;
  border-color: #7C2D12;
}
.deescalated-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .4px;
  background: #DCFCE7;
  color: #166534;
  border: 1px solid #BBF7D0;
  border-radius: 5px;
  padding: 3px 8px;
  white-space: nowrap;
}
:root.dark .deescalated-badge {
  background: #14532D;
  color: #86EFAC;
  border-color: #166534;
}

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

.quick-reply-active {
  background: #22C55E;
  border-color: #16A34A;
  color: #fff;
}

.quick-reply-active:hover {
  background: #16A34A;
  border-color: #15803D;
  color: #fff;
}

.reply-file-preview {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  min-width: 0;
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

.person-search {
  flex: 1;
  min-width: 0;
  position: relative;
  width: 100%;
}

.person-search .hd-input {
  font-size: 12px;
  padding: 6px 9px;
  width: 100%;
}

.person-search-menu {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.16);
  left: 0;
  max-height: 250px;
  overflow-y: auto;
  padding: 4px;
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  z-index: 30;
}

.person-search-menu button {
  align-items: center;
  background: transparent;
  border: 0;
  border-radius: 8px;
  color: var(--c-text);
  cursor: pointer;
  display: grid;
  gap: 8px;
  grid-template-columns: 22px minmax(0, 1fr);
  padding: 8px;
  text-align: left;
  width: 100%;
}

.person-search-menu button:hover {
  background: var(--c-surface-soft);
}

.person-search-menu strong,
.person-search-menu small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.person-search-menu strong {
  font-size: 12px;
}

.person-search-menu small {
  color: var(--c-muted);
  font-size: 11px;
  margin-top: 1px;
}

.person-search-empty {
  color: var(--c-muted);
  font-size: 12px;
  padding: 8px;
}

.assignee-editor {
  display: grid;
  gap: 8px;
  min-width: 0;
  width: 100%;
}

.assignee-chip-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.assignee-chip {
  align-items: center;
  background: rgba(61, 82, 213, 0.10);
  border: 1px solid rgba(61, 82, 213, 0.18);
  border-radius: 999px;
  color: var(--c-text);
  display: inline-flex;
  font-size: 12px;
  font-weight: 700;
  gap: 6px;
  max-width: 100%;
  padding: 4px 7px 4px 4px;
}

.assignee-chip button {
  align-items: center;
  background: transparent;
  border: 0;
  color: var(--c-muted);
  cursor: pointer;
  display: inline-flex;
  padding: 0;
}

.assignee-chip .material-icons {
  font-size: 14px;
}

.muted-mini {
  color: var(--c-muted);
  font-size: 13px;
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
