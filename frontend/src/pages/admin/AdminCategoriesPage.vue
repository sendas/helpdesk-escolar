<template>
  <div class="hd-page">

    <!-- Header -->
    <div class="hd-row" style="margin-bottom:28px;align-items:center">
      <div>
        <h1 style="font-size:22px;margin:0 0 4px">Categorias</h1>
        <p class="hd-hint" style="margin:0">
          Organize os pedidos de suporte por tipo e defina os tempos de resposta (SLA).
        </p>
      </div>
      <div class="hd-spacer"></div>
      <button class="hd-btn hd-btn-primary" @click="openCreate">
        <span class="material-icons" style="font-size:16px">add</span>
        Nova categoria
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="empty-state">
      <span class="material-icons" style="font-size:40px;color:var(--c-muted)">hourglass_empty</span>
      <p style="color:var(--c-muted);margin:8px 0 0">A carregar...</p>
    </div>

    <!-- Empty -->
    <div v-else-if="!categories.length" class="empty-state">
      <span class="material-icons" style="font-size:48px;color:var(--c-muted)">category</span>
      <p style="color:var(--c-muted);margin:8px 0 0">Ainda não existem categorias.</p>
      <button class="hd-btn hd-btn-primary" style="margin-top:16px" @click="openCreate">
        <span class="material-icons" style="font-size:16px">add</span>
        Criar a primeira categoria
      </button>
    </div>

    <!-- Category card grid -->
    <div v-else class="cat-grid">
      <article v-for="cat in categories" :key="cat.id" class="cat-card hd-card">

        <!-- Top: icon + name + description -->
        <div class="cat-card-top">
          <div
            class="cat-icon-circle"
            :style="{ background: cat.color + '22', borderColor: cat.color + '44' }"
          >
            <span class="material-icons" :style="{ color: cat.color }">{{ cat.icon }}</span>
          </div>
          <div class="cat-info">
            <div class="cat-name">{{ cat.name }}</div>
            <div v-if="cat.description" class="cat-desc">{{ cat.description }}</div>
          </div>
        </div>

        <!-- Meta pills -->
        <div class="cat-card-meta">
          <span
            class="sla-badge"
            :style="{ background: cat.color + '18', color: cat.color, borderColor: cat.color + '44' }"
          >
            <span class="material-icons" style="font-size:12px">schedule</span>
            SLA {{ cat.sla_hours }}h
          </span>
          <span v-if="cat.email_to" class="meta-pill">
            <span class="material-icons" style="font-size:12px">email</span>
            {{ cat.email_to }}
          </span>
        </div>

        <!-- Actions -->
        <div class="cat-card-actions">
          <button
            class="hd-btn hd-btn-outline"
            style="font-size:12px;padding:5px 12px"
            @click="openEdit(cat)"
          >
            <span class="material-icons" style="font-size:14px">edit</span>
            Editar
          </button>
          <button
            class="hd-btn"
            :class="cat.warning_enabled ? 'hd-btn-warning-on' : 'hd-btn-outline'"
            style="font-size:12px;padding:5px 12px"
            :title="cat.warning_enabled ? 'Desativar aviso de categoria' : 'Ativar aviso de categoria'"
            @click="toggleWarning(cat)"
          >
            <span class="material-icons" style="font-size:14px">{{ cat.warning_enabled ? 'warning' : 'warning_amber' }}</span>
            {{ cat.warning_enabled ? 'Aviso ativo' : 'Aviso inativo' }}
          </button>
          <button class="hd-icon-btn" @click="onDelete(cat)" title="Eliminar categoria">
            <span class="material-icons" style="font-size:16px;color:#EF4444">delete</span>
          </button>
        </div>

      </article>
    </div>

    <!-- ── Modal overlay (no Quasar dialog) ── -->
    <div v-if="showDialog" class="modal-backdrop" @click.self="closeDialog">
      <div class="modal-card hd-card">

        <!-- Modal header -->
        <div class="modal-head">
          <div style="font-weight:700;font-size:17px">
            {{ editingId !== null ? 'Editar categoria' : 'Nova categoria' }}
          </div>
          <button class="hd-icon-btn" @click="closeDialog" title="Fechar">
            <span class="material-icons">close</span>
          </button>
        </div>

        <!-- Modal form -->
        <form @submit.prevent="onSave" class="modal-body">

          <!-- Name -->
          <div class="hd-field">
            <label class="hd-label">
              Nome <span style="color:#EF4444">*</span>
            </label>
            <input
              class="hd-input"
              v-model="form.name"
              placeholder="Ex: Equipamento TI"
              required
              autofocus
            />
          </div>

          <!-- Description -->
          <div class="hd-field">
            <label class="hd-label">Descrição</label>
            <textarea
              class="hd-textarea"
              v-model="form.description"
              rows="2"
              placeholder="Breve descrição da categoria"
            ></textarea>
          </div>

          <!-- Email notification -->
          <div class="hd-field">
            <label class="hd-label">Email de notificação</label>
            <input
              class="hd-input"
              type="email"
              v-model="form.email_to"
              placeholder="ti@escola.pt"
            />
            <p class="hd-hint">
              Endereço que recebe notificações quando um ticket desta categoria é criado.
            </p>
          </div>

          <!-- Color + Icon side by side -->
          <div class="hd-grid-2">
            <div class="hd-field">
              <label class="hd-label">Cor (hex)</label>
              <div class="hd-row" style="gap:8px;align-items:center">
                <input
                  class="hd-input"
                  v-model="form.color"
                  placeholder="#3D52D5"
                  style="flex:1;min-width:0"
                />
                <div
                  class="color-preview"
                  :style="{ background: form.color }"
                  title="Pré-visualização da cor"
                ></div>
                <input
                  type="color"
                  :value="form.color"
                  @input="form.color = ($event.target as HTMLInputElement).value"
                  style="width:36px;height:36px;border:none;background:none;cursor:pointer;padding:0"
                  title="Escolher cor"
                />
              </div>
            </div>

            <div class="hd-field">
              <label class="hd-label">Ícone (Material Icons)</label>
              <div class="hd-row" style="gap:8px;align-items:center">
                <input
                  class="hd-input"
                  v-model="form.icon"
                  placeholder="computer"
                  style="flex:1;min-width:0"
                />
                <div
                  class="icon-preview"
                  :style="{ background: form.color + '22', borderColor: form.color + '55' }"
                >
                  <span class="material-icons" :style="{ color: form.color }">
                    {{ form.icon || 'help' }}
                  </span>
                </div>
              </div>
              <p class="hd-hint">Ex: <em>computer, email, settings, build, school</em></p>
            </div>
          </div>

          <!-- SLA hours -->
          <div class="hd-field">
            <label class="hd-label">Tempo de resposta (SLA) em horas</label>
            <input
              class="hd-input"
              type="number"
              min="1"
              v-model.number="form.sla_hours"
              placeholder="48"
              style="max-width:140px"
            />
          </div>

          <!-- Warning toggle -->
          <div class="hd-field">
            <label class="toggle-row">
              <div class="hd-toggle-wrap" @click="form.warning_enabled = !form.warning_enabled">
                <div class="hd-toggle" :class="{ active: form.warning_enabled }"></div>
              </div>
              <span style="font-size:13px;font-weight:600">Aviso ao selecionar esta categoria</span>
            </label>
          </div>

          <!-- Warning text (only when toggle is on) -->
          <div v-if="form.warning_enabled" class="hd-field">
            <label class="hd-label">Texto do aviso</label>
            <textarea
              class="hd-textarea"
              v-model="form.warning_text"
              rows="3"
              placeholder="Ex: Esta categoria destina-se exclusivamente a pedidos urgentes de infraestrutura..."
            ></textarea>
          </div>

          <!-- Actions -->
          <div class="modal-actions">
            <button type="button" class="hd-btn hd-btn-outline" @click="closeDialog">
              Cancelar
            </button>
            <button
              type="submit"
              class="hd-btn hd-btn-primary"
              :disabled="saving || !form.name.trim()"
            >
              <span v-if="saving" class="material-icons spin" style="font-size:15px">sync</span>
              {{ saving ? 'A guardar...' : (editingId !== null ? 'Guardar alterações' : 'Criar categoria') }}
            </button>
          </div>

        </form>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Notify } from 'quasar'
import { getCategories, createCategory, updateCategory, deleteCategory } from '../../api/tickets'
import type { Category } from '../../api/tickets'

// Extend the shared Category type with warning fields
interface CategoryFull extends Category {
  warning_enabled?: boolean
  warning_text?: string
}

interface CategoryForm {
  name: string
  description: string
  email_to: string
  color: string
  icon: string
  sla_hours: number
  warning_enabled: boolean
  warning_text: string
}

const DEFAULT_FORM: CategoryForm = {
  name: '',
  description: '',
  email_to: '',
  color: '#3D52D5',
  icon: 'help',
  sla_hours: 48,
  warning_enabled: false,
  warning_text: '',
}

const categories = ref<CategoryFull[]>([])
const loading    = ref(false)
const saving     = ref(false)
const showDialog = ref(false)
const editingId  = ref<number | null>(null)
const form       = ref<CategoryForm>({ ...DEFAULT_FORM })

onMounted(load)

async function load() {
  loading.value = true
  try {
    categories.value = (await getCategories()) as CategoryFull[]
  } catch {
    Notify.create({ type: 'negative', message: 'Erro ao carregar categorias' })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { ...DEFAULT_FORM }
  showDialog.value = true
}

function openEdit(cat: CategoryFull) {
  editingId.value = cat.id
  form.value = {
    name:            cat.name,
    description:     cat.description     ?? '',
    email_to:        cat.email_to        ?? '',
    color:           cat.color,
    icon:            cat.icon,
    sla_hours:       cat.sla_hours,
    warning_enabled: cat.warning_enabled ?? false,
    warning_text:    cat.warning_text    ?? '',
  }
  showDialog.value = true
}

function closeDialog() {
  if (saving.value) return
  showDialog.value = false
}

async function onSave() {
  if (!form.value.name.trim()) return
  saving.value = true
  try {
    const payload = {
      name:            form.value.name.trim(),
      description:     form.value.description.trim() || undefined,
      email_to:        form.value.email_to.trim()    || undefined,
      color:           form.value.color,
      icon:            form.value.icon || 'help',
      sla_hours:       form.value.sla_hours,
      warning_enabled: form.value.warning_enabled,
      warning_text:    form.value.warning_text.trim() || undefined,
    }

    if (editingId.value !== null) {
      const updated = (await updateCategory(editingId.value, payload)) as CategoryFull
      const idx = categories.value.findIndex(c => c.id === editingId.value)
      if (idx !== -1) categories.value[idx] = { ...categories.value[idx], ...updated }
      Notify.create({ type: 'positive', message: 'Categoria atualizada' })
    } else {
      const created = (await createCategory(payload)) as CategoryFull
      categories.value.push(created)
      Notify.create({ type: 'positive', message: 'Categoria criada' })
    }

    showDialog.value = false
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    Notify.create({
      type: 'negative',
      message: err?.response?.data?.detail || 'Erro ao guardar categoria',
    })
  } finally {
    saving.value = false
  }
}

async function toggleWarning(cat: CategoryFull) {
  const next = !cat.warning_enabled
  try {
    const updated = (await updateCategory(cat.id, { warning_enabled: next })) as CategoryFull
    const idx = categories.value.findIndex(c => c.id === cat.id)
    if (idx !== -1) categories.value[idx] = { ...categories.value[idx], ...updated }
  } catch {
    Notify.create({ type: 'negative', message: 'Erro ao atualizar aviso' })
  }
}

async function onDelete(cat: CategoryFull) {
  if (!window.confirm(`Eliminar a categoria "${cat.name}"? Esta ação não pode ser desfeita.`)) return
  try {
    await deleteCategory(cat.id)
    categories.value = categories.value.filter(c => c.id !== cat.id)
    Notify.create({ type: 'positive', message: 'Categoria eliminada' })
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    Notify.create({
      type: 'negative',
      message: err?.response?.data?.detail || 'Erro ao eliminar categoria',
    })
  }
}
</script>

<style scoped>
/* ── Card grid ── */
.cat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.cat-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px;
}

/* Top section: icon circle + text */
.cat-card-top {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.cat-icon-circle {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1.5px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cat-icon-circle .material-icons {
  font-size: 22px;
}

.cat-info {
  flex: 1;
  min-width: 0;
}

.cat-name {
  font-weight: 700;
  font-size: 15px;
  line-height: 1.3;
  color: var(--c-text);
  margin-bottom: 4px;
}

.cat-desc {
  font-size: 13px;
  color: var(--c-muted);
  line-height: 1.4;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* Meta pills row */
.cat-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.sla-badge,
.meta-pill,
.warning-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border-radius: 999px;
  border: 1px solid;
  padding: 3px 10px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.meta-pill {
  background: var(--c-bg);
  border-color: var(--c-border);
  color: var(--c-muted);
  font-weight: 400;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.warning-pill {
  background: rgba(245, 158, 11, 0.10);
  border-color: rgba(245, 158, 11, 0.35);
  color: #B45309;
}

.dark .warning-pill {
  color: #FCD34D;
}

/* Action row at card bottom */
.cat-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px solid var(--c-border);
}

/* ── Empty / loading state ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

/* ── Modal overlay ── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(0, 0, 0, 0.50);
  display: grid;
  place-items: center;
  padding: 20px;
}

.modal-card {
  width: min(520px, 100%);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  border-radius: 14px;
  padding: 28px;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 22px;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--c-border);
  margin-top: 4px;
}

/* ── Color + icon preview ── */
.color-preview {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid var(--c-border);
  flex-shrink: 0;
  transition: background 0.15s;
}

.icon-preview {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1.5px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.icon-preview .material-icons {
  font-size: 20px;
}

/* ── Warning toggle ── */
.toggle-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

/* Toggle thumb — driven by .active class (no hidden checkbox needed) */
.hd-toggle {
  position: relative;
  width: 40px;
  height: 22px;
  border-radius: 999px;
  background: var(--c-border);
  transition: background 0.18s;
  flex-shrink: 0;
}

.hd-toggle::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.18s;
  box-shadow: 0 1px 3px rgba(0,0,0,.25);
}

.hd-toggle.active {
  background: var(--c-primary);
}

.hd-toggle.active::after {
  transform: translateX(18px);
}

/* ── Warning toggle button on card ── */
.hd-btn-warning-on {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.5);
  color: #B45309;
}

.dark .hd-btn-warning-on {
  color: #FCD34D;
}

.hd-btn-warning-on:hover {
  background: rgba(245, 158, 11, 0.22);
}

/* ── Saving spinner ── */
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.spin {
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

/* ── Responsive ── */
@media (max-width: 680px) {
  .cat-grid {
    grid-template-columns: 1fr;
  }

  .modal-card {
    padding: 20px;
  }
}
</style>
