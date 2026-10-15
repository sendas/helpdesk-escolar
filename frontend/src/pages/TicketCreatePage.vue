<template>
  <div class="hd-page">
    <div style="font-size:12px;color:var(--c-muted);margin-bottom:16px">
      <router-link to="/tickets" style="color:var(--c-muted);text-decoration:none">Tickets</router-link> / Novo
    </div>

    <SupportBanner compact only-when-open style="max-width:880px" />

    <div class="hd-card ticket-create-card">
      <div style="font-weight:600;font-size:15px;margin-bottom:4px">Novo pedido de apoio</div>
      <div style="font-size:13px;color:var(--c-muted);margin-bottom:28px">Descreva o seu pedido — quanto mais detalhe, mais rápida a resolução.</div>

      <!-- School selector -->
      <div v-if="schools.length" class="hd-field" :class="{ 'field-missing': !form.school_id }" style="margin-bottom:24px">
        <label class="hd-label">Escola <span class="hd-label-hint">*</span></label>
        <div class="hd-grid-2" style="margin-top:8px">
          <div
            v-for="s in schools"
            :key="s.id"
            class="hd-sel-card"
            :class="{ selected: form.school_id === s.id }"
            @click="pickSchool(s.id)"
          >
            <div class="hd-sel-icon" style="background:#EEF1FF">
              <span class="material-icons" style="color:var(--c-primary);font-size:18px">account_balance</span>
            </div>
            <div>
              <div class="hd-sel-title">{{ s.name }}</div>
              <div class="hd-sel-sub">{{ s.address }}</div>
            </div>
          </div>
        </div>
        <p class="hd-hint">Escolha a escola onde o pedido se aplica.</p>
      </div>
      <div v-else style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px 14px;font-size:13px;color:#DC2626;margin-bottom:20px">
        Ainda não existem escolas configuradas. Peça a um administrador para adicionar escolas.
      </div>

      <!-- Room: the list of spaces of the chosen school -->
      <div v-if="form.school_id" class="hd-field" :class="{ 'field-missing': roomRequired && !form.room_id }" style="margin-bottom:24px">
        <label class="hd-label">Sala / espaço <span class="hd-label-hint">{{ roomRequired ? '*' : '(se o pedido for sobre uma sala)' }}</span></label>
        <select class="hd-select" v-model="form.room_id" style="max-width:420px;margin-top:8px" :disabled="roomsLoading || !rooms.length" @change="onRoomChange">
          <option :value="null">{{ roomsLoading ? 'A carregar as salas…' : !rooms.length ? 'Ainda não há salas configuradas para esta escola' : roomRequired ? '— Escolha a sala —' : '— Não se aplica / outro espaço —' }}</option>
          <optgroup v-for="g in roomGroups" :key="g.kind" :label="g.kind">
            <option v-for="r in g.rooms" :key="r.id" :value="r.id">{{ r.label }}</option>
          </optgroup>
        </select>
        <p v-if="!roomsLoading && !rooms.length && auth.isAdmin" class="hd-hint">
          Carregue a lista de salas em <router-link to="/admin/settings">Definições → Escolas e salas</router-link>.
        </p>
        <div v-if="recent.length" class="room-recent" role="alert">
          <div class="room-recent-title">
            <span class="material-icons">report</span>
            {{ recent.length === 1 ? 'Já foi aberto um pedido' : `Já foram abertos ${recent.length} pedidos` }} para esta sala nos últimos {{ recentDays }} dias
          </div>
          <ul>
            <li v-for="t in recent" :key="t.id">
              <router-link v-if="t.can_open" :to="`/tickets/${t.id}`" target="_blank">T-{{ t.id }} · {{ t.title }}</router-link>
              <span v-else>T-{{ t.id }} · {{ t.title }}</span>
              <small>{{ statusLabel(t.status) }} · {{ formatDay(t.created_at) }}</small>
            </li>
          </ul>
          <p>Se for o mesmo problema, não é preciso abrir outro pedido — a equipa já está a tratar. Se for um problema diferente, pode continuar.</p>
        </div>
      </div>

      <!-- Category selector -->
      <div class="hd-field" :class="{ 'field-missing': !form.category_id }" style="margin-bottom:24px">
        <label class="hd-label">Categoria <span class="hd-label-hint">*</span></label>
        <div class="hd-grid-3" style="margin-top:8px">
          <div
            v-for="cat in categories"
            :key="cat.id"
            class="hd-sel-card"
            :class="{ selected: form.category_id === cat.id }"
            @click="selectCategory(cat)"
            style="flex-direction:column;align-items:flex-start;gap:8px"
          >
            <div class="hd-sel-icon" :style="{ background: cat.color + '22' }">
              <span class="material-icons" :style="{ color: cat.color, fontSize: '20px' }">{{ cat.icon }}</span>
            </div>
            <div>
              <div class="hd-sel-title">{{ cat.name }}</div>
              <div class="hd-sel-sub">{{ cat.description }}</div>
            </div>
          </div>
        </div>
        <p v-if="!categories.length" class="hd-hint">Ainda não existem categorias configuradas.</p>
      </div>

      <!-- Category warning popup -->
      <teleport to="body">
        <div v-if="warningPopup" class="cat-warning-backdrop" @click.self="warningPopup = null">
          <div class="cat-warning-modal">
            <div class="cat-warning-header">
              <span class="material-icons" style="color:#F59E0B;font-size:22px">warning</span>
              <span style="font-weight:700;font-size:16px">Atenção</span>
            </div>
            <p style="font-size:14px;line-height:1.65;color:var(--c-text);white-space:pre-wrap">{{ warningPopup.text }}</p>
            <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:20px">
              <button class="hd-btn hd-btn-outline" @click="warningPopup = null; form.category_id = null">Escolher outra</button>
              <button class="hd-btn hd-btn-primary" @click="warningPopup = null">Compreendi</button>
            </div>
          </div>
        </div>
      </teleport>

      <!-- Title -->
      <div class="hd-field" :class="{ 'field-missing': !form.title.trim() }" style="margin-bottom:20px">
        <label class="hd-label">Assunto <span class="hd-label-hint">*</span></label>
        <input class="hd-input" v-model="form.title" placeholder="Ex: Projetor sem imagem" />
      </div>

      <!-- Description -->
      <div class="hd-field" :class="{ 'field-missing': !form.description.trim() }" style="margin-bottom:20px">
        <label class="hd-label">Descrição <span class="hd-label-hint">*</span></label>
        <textarea class="hd-textarea" v-model="form.description" rows="5"
          placeholder="Descreva o problema com o máximo de detalhe: o que aconteceu, quando começou, o que já tentou... (pode colar aqui capturas de ecrã)"
          @paste="onPasteImage"
        ></textarea>
        <p class="hd-hint">Inclua, se possível, o equipamento e o horário em que precisa de resolução.</p>
      </div>

      <!-- Priority -->
      <div class="hd-field" style="margin-bottom:20px">
        <label class="hd-label">Prioridade</label>
        <select class="hd-select" v-model="form.priority" style="max-width:320px">
          <option value="low">Baixa</option>
          <option value="medium">Média</option>
          <option value="high">Alta</option>
          <option value="urgent">Urgente</option>
        </select>
        <p class="hd-hint">A prioridade pode ser ajustada pela equipa de suporte.</p>
      </div>

      <div class="email-choice" :class="{ 'field-missing': form.creator_email_notifications === null }">
        <div>
          <div class="email-choice-title">Quer receber atualizações por email?</div>
          <div class="email-choice-sub">Escolha obrigatoriamente se pretende receber notificações deste ticket.</div>
        </div>
        <div class="email-choice-actions" role="radiogroup" aria-label="Receber atualizações por email">
          <button
            type="button"
            :class="{ active: form.creator_email_notifications === true }"
            @click="form.creator_email_notifications = true"
          >
            Sim
          </button>
          <button
            type="button"
            :class="{ active: form.creator_email_notifications === false }"
            @click="form.creator_email_notifications = false"
          >
            Não
          </button>
        </div>
      </div>

      <!-- Watchers -->
      <div class="hd-field" style="margin-bottom:24px">
        <label class="hd-label">{{ auth.isAdmin ? 'Atribuir ou dar conhecimento a pessoas' : 'Dar conhecimento a' }} <span class="hd-label-hint">(opcional)</span></label>
        <p class="hd-hint" style="margin-bottom:8px">
          Estas pessoas recebem atualizações por email e podem acompanhar, responder e anexar informação ao pedido.
        </p>
        <div class="watcher-picker">
          <span class="material-icons">search</span>
          <input
            v-model="watcherSearch"
            placeholder="Pesquisar por nome, email ou utilizador"
            @input="onWatcherSearch"
            @focus="onWatcherSearch"
          />
        </div>
        <div v-if="watcherResults.length" class="watcher-results">
          <button
            v-for="user in watcherResults"
            :key="user.id"
            type="button"
            class="watcher-result"
            @click="addWatcher(user)"
          >
            <span>{{ initials(user.display_name) }}</span>
            <div>
              <strong>{{ user.display_name }}</strong>
              <small>{{ user.email }} · @{{ user.username }}</small>
            </div>
          </button>
        </div>
        <div v-if="selectedWatchers.length" class="watcher-chips">
          <button
            v-for="user in selectedWatchers"
            :key="user.id"
            type="button"
            class="watcher-chip"
            @click="removeWatcher(user.id)"
          >
            {{ user.display_name }}
            <span class="material-icons">close</span>
          </button>
        </div>
      </div>

      <div v-if="auth.isAdmin && groups.length" class="hd-field" style="margin-bottom:24px">
        <label class="hd-label">Atribuir a equipas internas <span class="hd-label-hint">(opcional)</span></label>
        <p class="hd-hint" style="margin-bottom:8px">
          A primeira equipa escolhida fica como grupo principal do ticket. Todos os membros das equipas escolhidas recebem notificação e podem acompanhar o pedido.
        </p>
        <div class="group-picker-grid">
          <button
            v-for="group in groups"
            :key="group.id"
            type="button"
            class="group-pick-card"
            :class="{ selected: selectedGroupIds.includes(group.id) }"
            @click="toggleGroup(group.id)"
          >
            <span class="material-icons">groups</span>
            <div>
              <strong>{{ group.name }}</strong>
              <small>{{ group.members?.length || 0 }} membro{{ (group.members?.length || 0) === 1 ? '' : 's' }}</small>
            </div>
          </button>
        </div>
      </div>

      <!-- Attachments -->
      <div class="hd-field" style="margin-bottom:32px">
        <label class="hd-label">Anexos <span class="hd-label-hint">(opcional)</span></label>
        <input ref="fileInput" type="file" multiple accept=".png,.jpg,.jpeg,.gif,.webp,.heic,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.txt,.csv,.zip" style="display:none" @change="onFilesPicked" />
        <div class="hd-dropzone" style="margin-top:8px" @dragover.prevent @drop.prevent="onDrop">
          <span class="material-icons" style="font-size:28px;color:var(--c-muted);margin-bottom:8px;display:block">attach_file</span>
          <div style="font-size:13.5px;color:var(--c-muted)">
            Arrastar ficheiros para aqui ou <span style="color:var(--c-primary);cursor:pointer" @click="fileInput?.click()">procurar</span>
          </div>
          <div style="font-size:12px;color:var(--c-muted);margin-top:4px">Imagens, PDF, Word, Excel, PowerPoint, texto ou ZIP — até 10 MB</div>
        </div>
        <div v-if="files.length" style="display:flex;flex-direction:column;gap:6px;margin-top:10px">
          <div v-for="(f, idx) in files" :key="`${f.name}-${idx}`" class="hd-row" style="justify-content:space-between;border:1px solid var(--c-border);border-radius:8px;padding:8px 10px">
            <span style="font-size:13px">{{ f.name }} · {{ formatSize(f.size) }}</span>
            <button class="hd-icon-btn" @click="files.splice(idx, 1)" title="Remover">
              <span class="material-icons" style="font-size:15px">close</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Escalation (admin only) -->
      <div v-if="auth.isAdmin" class="hd-field" style="margin-bottom:24px">
        <div class="escalate-toggle" :class="{ active: escalate }" role="switch" tabindex="0" :aria-checked="escalate" @click="escalate = !escalate" @keydown.enter.prevent="escalate = !escalate" @keydown.space.prevent="escalate = !escalate">
          <div>
            <div style="font-weight:600;font-size:13px">Reportar imediatamente à empresa de apoio</div>
            <div style="font-size:12px;color:var(--c-muted);margin-top:2px">
              O ticket é enviado por email à empresa de apoio informático configurada nas definições logo após a criação.
            </div>
          </div>
          <div class="hd-toggle-wrap" style="flex-shrink:0">
            <div class="hd-toggle-track" :class="{ on: escalate }">
              <div class="hd-toggle-thumb"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div v-if="missingRequired.length" class="missing-panel" role="status">
        <div class="missing-panel-title">
          <span class="material-icons">info</span>
          Ainda falta preencher para submeter o ticket
        </div>
        <ul>
          <li v-for="item in missingRequired" :key="item">{{ item }}</li>
        </ul>
      </div>
      <div class="hd-row ticket-actions">
        <router-link to="/tickets">
          <button class="hd-btn hd-btn-outline">Cancelar</button>
        </router-link>
        <button type="button" class="hd-btn hd-btn-primary" :disabled="!canSubmit || loading" @click="onSubmit">
          <span class="material-icons" style="font-size:16px">{{ escalate ? 'upload' : 'send' }}</span>
          {{ loading ? 'A enviar...' : escalate ? 'Criar e reportar à empresa de apoio' : 'Submeter ticket' }}
        </button>
      </div>

      <div v-if="error" style="color:#DC2626;font-size:13px;margin-top:12px">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { confirmDialog, errorMessage } from '../utils/feedback'
import { ref, computed, onMounted } from 'vue'
import { groupRooms } from '../utils/rooms'
import { statusLabel } from '../utils/ticketStatus'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { createTicket, getCategories, getRoomRecent, getRooms, getSchools, uploadTicketAttachment, type RecentRoomTicket, type Room } from '../api/tickets'
import { getGroups, searchUsers, type HelpdeskGroup, type UserFull } from '../api/users'
import { getPublicSettings } from '../api/settings'
import SupportBanner from '../components/SupportBanner.vue'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const escalate = ref(false)
const categories = ref<any[]>([])
const schools = ref<any[]>([])
const files = ref<File[]>([])
const fileInput = ref<HTMLInputElement | null>(null)
const watcherSearch = ref('')
const watcherResults = ref<UserFull[]>([])
const selectedWatchers = ref<UserFull[]>([])
const groups = ref<HelpdeskGroup[]>([])
const selectedGroupIds = ref<number[]>([])
const warningPopup = ref<{ text: string } | null>(null)
const categoryWarningsEnabled = ref(true)
const rooms = ref<Room[]>([])
const selectedCategory = computed(() => categories.value.find((c: any) => c.id === form.value.category_id))
// Required only where there is a list to choose from (a school without rooms never blocks a ticket)
const roomRequired = computed(() => !!selectedCategory.value?.room_required && rooms.value.length > 0)
const roomsLoading = ref(false)
const roomGroups = computed(() => groupRooms(rooms.value))
const recent = ref<RecentRoomTicket[]>([])
const recentDays = ref(7)

async function pickSchool(id: number) {
  if (form.value.school_id === id) return
  form.value.school_id = id
  form.value.room_id = null
  recent.value = []
  rooms.value = []
  roomsLoading.value = true
  try { rooms.value = await getRooms(id) } catch { rooms.value = [] } finally { roomsLoading.value = false }
}

// Someone may already have asked for help with this room: show it before a second ticket is opened
async function onRoomChange() {
  recent.value = []
  if (!form.value.room_id) return
  try {
    const r = await getRoomRecent(form.value.room_id)
    recentDays.value = r.days
    recent.value = r.tickets
  } catch { recent.value = [] }
}

function formatDay(iso: string) {
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z')
  return d.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' }) + ' às ' + d.toLocaleTimeString('pt-PT', { hour: '2-digit', minute: '2-digit' })
}

async function confirmSameRoom(list: RecentRoomTicket[]) {
  const room = rooms.value.find((r) => r.id === form.value.room_id)
  const lines = list.map((t) => `• T-${t.id} · ${t.title} (${statusLabel(t.status)}, ${formatDay(t.created_at)})`).join('\n')
  return confirmDialog(
    `Nos últimos ${recentDays.value} dias já foi aberto um pedido para ${room?.label ?? 'esta sala'}:\n\n${lines}\n\nSe for o mesmo problema, não é preciso abrir outro. Quer mesmo criar um novo pedido para esta sala?`,
    { title: 'Pedido para a mesma sala', ok: 'Sim, é outro problema', cancel: 'Não criar' },
  )
}

const form = ref({
  title: '',
  description: '',
  category_id: null as number | null,
  school_id: null as number | null,
  room_id: null as number | null,
  priority: 'medium',
  creator_email_notifications: true as boolean | null,
})

const missingRequired = computed(() => {
  const missing: string[] = []
  if (!form.value.school_id) missing.push('Escolher a escola')
  if (!form.value.category_id) missing.push('Escolher a categoria')
  if (roomRequired.value && !form.value.room_id) missing.push(`Escolher a sala (obrigatório em "${selectedCategory.value?.name}")`)
  if (!form.value.title.trim()) missing.push('Preencher o assunto')
  if (!form.value.description.trim()) missing.push('Preencher a descrição')
  if (form.value.creator_email_notifications === null) missing.push('Responder se quer receber atualizações por email')
  return missing
})

const canSubmit = computed(() => missingRequired.value.length === 0)

onMounted(async () => {
  const [cats, schs, grps, settings] = await Promise.all([
    getCategories(), getSchools(),
    auth.isAdmin ? getGroups() : Promise.resolve([]),
    getPublicSettings(),
  ])
  categories.value = cats
  schools.value = schs
  if (schs.length === 1) pickSchool(schs[0].id)
  groups.value = grps as HelpdeskGroup[]
  categoryWarningsEnabled.value = settings?.category_warnings_enabled !== false
  const preselected = Number(route.query.categoria)
  const preselectedCat = preselected ? cats.find((c: any) => c.id === preselected) : null
  if (preselectedCat) selectCategory(preselectedCat)
})

function selectCategory(cat: any) {
  form.value.category_id = cat.id
  if (categoryWarningsEnabled.value && cat.warning_enabled) {
    warningPopup.value = { text: cat.warning_text?.trim() || 'Esta categoria pode requerer informação adicional. Certifique-se de que o seu pedido está correcto antes de submeter.' }
  }
}

async function onSubmit() {
  if (!canSubmit.value || !form.value.category_id || !form.value.school_id) {
    error.value = `Ainda falta: ${missingRequired.value.join(', ')}.`
    return
  }
  let confirmDuplicate = false
  if (form.value.room_id) {
    await onRoomChange()
    if (recent.value.length) {
      if (!(await confirmSameRoom(recent.value))) return
      confirmDuplicate = true
    }
  }
  await submit(confirmDuplicate)
}

async function submit(confirmDuplicate: boolean) {
  if (!form.value.category_id || !form.value.school_id) return
  loading.value = true
  error.value = ''
  try {
    const t = await createTicket({
      title: form.value.title,
      description: form.value.description,
      category_id: form.value.category_id,
      school_id: form.value.school_id,
      room_id: form.value.room_id,
      confirm_duplicate: confirmDuplicate,
      priority: form.value.priority,
      watcher_ids: selectedWatchers.value.map(user => user.id),
      group_ids: selectedGroupIds.value,
      creator_email_notifications: form.value.creator_email_notifications === true,
      escalate: escalate.value,
    })
    const attachErrors: string[] = []
    for (const file of files.value) {
      try {
        await uploadTicketAttachment(t.id, file)
      } catch (e: any) {
        attachErrors.push(file.name)
      }
    }
    router.push(`/tickets/${t.id}`)
    if (attachErrors.length) {
      error.value = `Ticket criado, mas os seguintes anexos falharam: ${attachErrors.join(', ')}`
    }
  } catch (e: any) {
    // Someone opened a ticket for the same room in the meantime: show it and ask again
    const detail = e?.response?.status === 409 ? e.response.data?.detail : null
    if (detail?.recent?.length && !confirmDuplicate) {
      recent.value = detail.recent
      loading.value = false
      if (await confirmSameRoom(detail.recent)) await submit(true)
      return
    }
    error.value = errorMessage(e, 'Erro ao criar ticket')
  } finally {
    loading.value = false
  }
}

function onFilesPicked(event: Event) {
  const input = event.target as HTMLInputElement
  addFiles(input.files)
  input.value = ''
}

function onDrop(event: DragEvent) {
  addFiles(event.dataTransfer?.files ?? null)
}

// A screenshot pasted into the description becomes an attachment
function onPasteImage(e: ClipboardEvent) {
  const item = Array.from(e.clipboardData?.items ?? []).find((i) => i.kind === 'file' && i.type.startsWith('image/'))
  const file = item?.getAsFile()
  if (!file) return
  e.preventDefault()
  const ext = file.type.split('/')[1]?.replace('jpeg', 'jpg') || 'png'
  files.value.push(new File([file], `captura-${files.value.length + 1}.${ext}`, { type: file.type }))
}

function addFiles(list: FileList | null) {
  if (!list) return
  const next = Array.from(list).filter(f => {
    // Same list the server accepts (backend tickets.py ALLOWED_ATTACHMENTS)
    const allowed = /\.(png|jpe?g|gif|webp|heic|pdf|docx?|xlsx?|pptx?|odt|ods|txt|csv|zip)$/i.test(f.name)
    return allowed && f.size <= 10 * 1024 * 1024
  })
  files.value.push(...next)
}

let watcherSearchTimer: number | undefined

function onWatcherSearch() {
  window.clearTimeout(watcherSearchTimer)
  watcherSearchTimer = window.setTimeout(async () => {
    const term = watcherSearch.value.trim()
    if (term.length < 2) {
      watcherResults.value = []
      return
    }
    const selectedIds = new Set(selectedWatchers.value.map(user => user.id))
    const results = await searchUsers(term)
    watcherResults.value = results.filter(user => !selectedIds.has(user.id)).slice(0, 8)
  }, 220)
}

function addWatcher(user: UserFull) {
  if (!selectedWatchers.value.some(existing => existing.id === user.id)) {
    selectedWatchers.value.push(user)
  }
  watcherSearch.value = ''
  watcherResults.value = []
}

function removeWatcher(userId: number) {
  selectedWatchers.value = selectedWatchers.value.filter(user => user.id !== userId)
}

function toggleGroup(groupId: number) {
  selectedGroupIds.value = selectedGroupIds.value.includes(groupId)
    ? selectedGroupIds.value.filter(id => id !== groupId)
    : [...selectedGroupIds.value, groupId]
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase())
    .join('') || 'U'
}

function formatSize(size: number) {
  return size >= 1024 * 1024 ? `${(size / 1024 / 1024).toFixed(1)} MB` : `${Math.round(size / 1024)} KB`
}
</script>

<style scoped>
.ticket-create-card {
  padding: 28px;
  max-width: 800px;
}

.escalate-toggle {
  border: 1px solid var(--c-border);
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  gap: 16px;
  justify-content: space-between;
  padding: 12px 14px;
  transition: border-color .15s, background .15s;
}

.escalate-toggle.active {
  background: #FFF7ED;
  border-color: #F97316;
}

.dark .escalate-toggle.active {
  background: #431407;
  border-color: #EA580C;
}
.ticket-actions {
  justify-content: flex-end;
}

.missing-panel {
  background: #FFF7ED;
  border: 1px solid #FDBA74;
  border-radius: 10px;
  color: #9A3412;
  margin-bottom: 18px;
  padding: 12px 14px;
}

.missing-panel-title {
  align-items: center;
  display: flex;
  font-size: 13px;
  font-weight: 800;
  gap: 8px;
}

.missing-panel-title .material-icons {
  font-size: 18px;
}

.missing-panel ul {
  margin: 8px 0 0 26px;
  padding: 0;
}

.missing-panel li {
  font-size: 13px;
  line-height: 1.55;
}

.field-missing :deep(.hd-input),
.field-missing :deep(.hd-textarea),
.field-missing :deep(.hd-select),
.field-missing.email-choice {
  border-color: #F97316;
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.12);
}

.field-missing :deep(.hd-sel-card:not(.selected)) {
  border-color: rgba(249, 115, 22, 0.5);
}

.field-missing .hd-label::after {
  color: #EA580C;
  content: " obrigatório";
  font-size: 11px;
  font-weight: 700;
  margin-left: 6px;
}

.dark .missing-panel {
  background: rgba(154, 52, 18, 0.18);
  border-color: #C2410C;
  color: #FDBA74;
}

.email-choice {
  align-items: center;
  background: rgba(61, 82, 213, 0.06);
  border: 1px solid rgba(61, 82, 213, 0.18);
  border-radius: 10px;
  display: flex;
  gap: 18px;
  justify-content: space-between;
  margin-bottom: 24px;
  padding: 16px;
}

.email-choice-title {
  font-size: 14px;
  font-weight: 800;
}

.email-choice-sub {
  color: var(--c-muted);
  font-size: 12px;
  margin-top: 3px;
}

.email-choice-actions {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  display: grid;
  flex-shrink: 0;
  grid-template-columns: 1fr 1fr;
  overflow: hidden;
  width: 180px;
}

.email-choice-actions button {
  background: transparent;
  border: 0;
  color: var(--c-muted);
  cursor: pointer;
  font-weight: 800;
  padding: 10px 0;
}

.email-choice-actions button.active {
  background: var(--c-primary);
  color: #fff;
}

.watcher-picker {
  align-items: center;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  display: flex;
  gap: 8px;
  padding: 0 12px;
}

.watcher-picker .material-icons {
  color: var(--c-muted);
  font-size: 18px;
}

.watcher-picker input {
  background: transparent;
  border: 0;
  color: var(--c-text);
  flex: 1;
  font: inherit;
  min-height: 42px;
  outline: none;
}

.watcher-results {
  border: 1px solid var(--c-border);
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  margin-top: 6px;
  max-height: 260px;
  overflow: auto;
}

.watcher-result {
  align-items: center;
  background: var(--c-surface);
  border: 0;
  border-bottom: 1px solid var(--c-border);
  color: var(--c-text);
  cursor: pointer;
  display: grid;
  gap: 10px;
  grid-template-columns: 32px minmax(0, 1fr);
  padding: 10px 12px;
  text-align: left;
}

.watcher-result:last-child {
  border-bottom: 0;
}

.watcher-result:hover {
  background: rgba(61, 82, 213, 0.06);
}

.watcher-result > span {
  align-items: center;
  background: #eef1ff;
  border-radius: 50%;
  color: var(--c-primary);
  display: flex;
  font-size: 12px;
  font-weight: 800;
  height: 32px;
  justify-content: center;
  width: 32px;
}

.watcher-result strong,
.watcher-result small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.watcher-result strong {
  font-size: 13px;
}

.watcher-result small {
  color: var(--c-muted);
  font-size: 12px;
}

.watcher-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.watcher-chip {
  align-items: center;
  background: #eef1ff;
  border: 1px solid #dbe2ff;
  border-radius: 999px;
  color: var(--c-primary);
  cursor: pointer;
  display: flex;
  font-size: 12px;
  font-weight: 800;
  gap: 6px;
  padding: 7px 10px;
}

.watcher-chip .material-icons {
  font-size: 14px;
}

.group-picker-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.group-pick-card {
  align-items: center;
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  color: var(--c-text);
  cursor: pointer;
  display: grid;
  gap: 10px;
  grid-template-columns: 34px minmax(0, 1fr);
  padding: 12px;
  text-align: left;
}

.group-pick-card.selected {
  border-color: var(--c-primary);
  box-shadow: inset 0 0 0 1px var(--c-primary);
}

.group-pick-card .material-icons {
  align-items: center;
  background: rgba(61, 82, 213, 0.1);
  border-radius: 8px;
  color: var(--c-primary);
  display: flex;
  height: 34px;
  justify-content: center;
  width: 34px;
}

.group-pick-card strong,
.group-pick-card small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-pick-card small {
  color: var(--c-muted);
  font-size: 12px;
}

.room-recent {
  background: #FFF7ED;
  border: 1px solid #FDBA74;
  border-radius: 10px;
  color: #9A3412;
  margin-top: 10px;
  max-width: 620px;
  padding: 12px 14px;
}
.room-recent-title { align-items: center; display: flex; font-size: 13px; font-weight: 800; gap: 8px; }
.room-recent-title .material-icons { font-size: 18px; }
.room-recent ul { list-style: none; margin: 8px 0 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.room-recent li { display: flex; flex-direction: column; font-size: 13px; }
.room-recent li a { color: inherit; font-weight: 700; }
.room-recent li small { opacity: .8; font-size: 12px; }
.room-recent p { font-size: 12.5px; margin: 10px 0 0; line-height: 1.45; }
.dark .room-recent { background: rgba(154, 52, 18, 0.18); border-color: #C2410C; color: #FDBA74; }

.cat-warning-backdrop {
  position: fixed; inset: 0; z-index: 9999;
  background: rgba(0,0,0,.5);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.cat-warning-modal {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 14px;
  padding: 28px;
  max-width: 480px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0,0,0,.3);
}
.cat-warning-header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
}

@media (max-width: 820px) {
  .ticket-create-card {
    padding: 18px;
    border-radius: 8px;
  }
  .ticket-create-card :deep(.hd-grid-2),
  .ticket-create-card :deep(.hd-grid-3) {
    grid-template-columns: 1fr;
  }
  .ticket-create-card :deep(.hd-sel-card) {
    padding: 12px;
  }
  .ticket-create-card :deep(.hd-dropzone) {
    padding: 22px 14px;
  }
  .email-choice {
    align-items: stretch;
    flex-direction: column;
  }
  .email-choice-actions {
    width: 100%;
  }
  .group-picker-grid {
    grid-template-columns: 1fr;
  }
  .ticket-actions {
    display: grid;
    grid-template-columns: 1fr;
  }
  .ticket-actions a,
  .ticket-actions button {
    width: 100%;
    justify-content: center;
  }
}
</style>
