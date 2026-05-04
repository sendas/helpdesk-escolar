<template>
  <div class="hd-page">
    <div style="font-size:12px;color:var(--c-muted);margin-bottom:6px">
      <router-link to="/tickets" style="color:var(--c-muted);text-decoration:none">Tickets</router-link> / Novo
    </div>
    <h1 style="font-size:26px;margin-bottom:24px">Novo pedido</h1>

    <div class="hd-card ticket-create-card">
      <div style="font-weight:600;font-size:15px;margin-bottom:4px">Novo pedido de apoio</div>
      <div style="font-size:13px;color:var(--c-muted);margin-bottom:28px">Descreva o seu pedido — quanto mais detalhe, mais rápida a resolução.</div>

      <!-- School selector -->
      <div v-if="schools.length" class="hd-field" style="margin-bottom:24px">
        <label class="hd-label">Escola <span class="hd-label-hint">*</span></label>
        <div class="hd-grid-2" style="margin-top:8px">
          <div
            v-for="s in schools"
            :key="s.id"
            class="hd-sel-card"
            :class="{ selected: form.school_id === s.id }"
            @click="form.school_id = s.id"
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

      <!-- Category selector -->
      <div class="hd-field" style="margin-bottom:24px">
        <label class="hd-label">Categoria <span class="hd-label-hint">*</span></label>
        <div class="hd-grid-3" style="margin-top:8px">
          <div
            v-for="cat in categories"
            :key="cat.id"
            class="hd-sel-card"
            :class="{ selected: form.category_id === cat.id }"
            @click="form.category_id = cat.id"
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

      <!-- Title -->
      <div class="hd-field" style="margin-bottom:20px">
        <label class="hd-label">Assunto <span class="hd-label-hint">*</span></label>
        <input class="hd-input" v-model="form.title" placeholder="Ex: Projetor da sala B-12 sem imagem" />
      </div>

      <!-- Description -->
      <div class="hd-field" style="margin-bottom:20px">
        <label class="hd-label">Descrição <span class="hd-label-hint">*</span></label>
        <textarea class="hd-textarea" v-model="form.description" rows="5"
          placeholder="Descreva o problema com o máximo de detalhe: o que aconteceu, quando começou, o que já tentou..."
        ></textarea>
        <p class="hd-hint">Inclua, se possível, número da sala, equipamento e horário em que precisa de resolução.</p>
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

      <!-- Attachments -->
      <div class="hd-field" style="margin-bottom:32px">
        <label class="hd-label">Anexos <span class="hd-label-hint">(opcional)</span></label>
        <input ref="fileInput" type="file" multiple accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf" style="display:none" @change="onFilesPicked" />
        <div class="hd-dropzone" style="margin-top:8px" @dragover.prevent @drop.prevent="onDrop">
          <span class="material-icons" style="font-size:28px;color:var(--c-muted);margin-bottom:8px;display:block">attach_file</span>
          <div style="font-size:13.5px;color:var(--c-muted)">
            Arrastar ficheiros para aqui ou <span style="color:var(--c-primary);cursor:pointer" @click="fileInput?.click()">procurar</span>
          </div>
          <div style="font-size:12px;color:var(--c-muted);margin-top:4px">PNG, JPG, PDF até 10 MB</div>
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

      <!-- Actions -->
      <div class="hd-row ticket-actions">
        <router-link to="/tickets">
          <button class="hd-btn hd-btn-outline">Cancelar</button>
        </router-link>
        <button class="hd-btn hd-btn-primary" :disabled="!canSubmit || loading" @click="onSubmit">
          <span class="material-icons" style="font-size:16px">send</span>
          {{ loading ? 'A enviar...' : 'Submeter ticket' }}
        </button>
      </div>

      <div v-if="error" style="color:#DC2626;font-size:13px;margin-top:12px">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { createTicket, getCategories, getSchools, uploadTicketAttachment } from '../api/tickets'

const router = useRouter()
const loading = ref(false)
const error = ref('')
const categories = ref<any[]>([])
const schools = ref<any[]>([])
const files = ref<File[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

const form = ref({ title: '', description: '', category_id: null as number | null, school_id: null as number | null, priority: 'medium' })

const canSubmit = computed(() => form.value.title.trim() && form.value.description.trim() && form.value.category_id && form.value.school_id)

onMounted(async () => {
  const [cats, schs] = await Promise.all([getCategories(), getSchools()])
  categories.value = cats
  schools.value = schs
})

async function onSubmit() {
  if (!form.value.category_id || !form.value.school_id) return
  loading.value = true
  error.value = ''
  try {
    const t = await createTicket({
      title: form.value.title,
      description: form.value.description,
      category_id: form.value.category_id,
      school_id: form.value.school_id,
      priority: form.value.priority,
    })
    for (const file of files.value) {
      await uploadTicketAttachment(t.id, file)
    }
    router.push(`/tickets/${t.id}`)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Erro ao criar ticket'
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

function addFiles(list: FileList | null) {
  if (!list) return
  const next = Array.from(list).filter(f => {
    const allowed = ['image/png', 'image/jpeg', 'application/pdf'].includes(f.type)
    return allowed && f.size <= 10 * 1024 * 1024
  })
  files.value.push(...next)
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
.ticket-actions {
  justify-content: flex-end;
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
