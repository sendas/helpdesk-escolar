<template>
  <div class="hd-page plan-page">
    <div class="plan-head">
      <p class="plan-intro">
        Tickets criados automaticamente na data marcada e depois a cada semana, mês, período ou ano —
        por exemplo "Verificar os projetores" no início de cada período.
      </p>
      <button class="hd-btn hd-btn-primary" type="button" @click="startNew"><span class="material-icons">add</span> Nova manutenção</button>
    </div>

    <section v-if="editing" class="hd-card plan-form">
      <div class="plan-form-title">{{ editing.id ? 'Editar manutenção' : 'Nova manutenção' }}</div>
      <div class="plan-grid">
        <label class="span-2">Assunto do ticket
          <input v-model="editing.title" class="hd-input" maxlength="200" placeholder="ex.: Verificar projetores das salas" />
        </label>
        <label class="span-2">Descrição
          <textarea v-model="editing.description" class="hd-textarea" rows="3" placeholder="O que deve ser feito"></textarea>
        </label>
        <label>Categoria
          <select v-model.number="editing.category_id" class="hd-select">
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
        <label>Escola
          <select v-model.number="editing.school_id" class="hd-select">
            <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
          </select>
        </label>
        <label>Responsável
          <select v-model="editing.assignee_id" class="hd-select">
            <option :value="null">Automático (regras de encaminhamento)</option>
            <option v-for="u in technicians" :key="u.id" :value="u.id">{{ u.display_name }}</option>
          </select>
        </label>
        <label>Prioridade
          <select v-model="editing.priority" class="hd-select">
            <option value="low">Baixa</option><option value="medium">Média</option><option value="high">Alta</option><option value="urgent">Urgente</option>
          </select>
        </label>
        <label>Repetir
          <select v-model="editing.frequency" class="hd-select">
            <option v-for="(label, key) in frequencies" :key="key" :value="key">{{ label }}</option>
          </select>
        </label>
        <label>Próxima data
          <input v-model="editing.next_run" type="date" class="hd-input" />
        </label>
      </div>
      <div class="plan-actions">
        <label class="plan-active"><input v-model="editing.active" type="checkbox" /> Ativa</label>
        <button class="hd-btn hd-btn-outline" type="button" @click="editing = null">Cancelar</button>
        <button class="hd-btn hd-btn-primary" type="button" :disabled="saving" @click="save">{{ saving ? 'A guardar…' : 'Guardar' }}</button>
      </div>
    </section>

    <div v-if="loading" class="plan-empty">A carregar…</div>
    <div v-else-if="!items.length && !editing" class="plan-empty">
      <span class="material-icons">event_repeat</span>
      Ainda não há manutenções planeadas.
    </div>
    <div v-else class="plan-list">
      <article v-for="p in items" :key="p.id" class="hd-card plan-item" :class="{ off: !p.active }">
        <div class="plan-date">
          <div class="plan-day">{{ day(p.next_run) }}</div>
          <div class="plan-month">{{ month(p.next_run) }}</div>
        </div>
        <div class="plan-main">
          <div class="plan-title">{{ p.title }} <span v-if="!p.active" class="plan-paused">pausada</span></div>
          <div class="plan-meta">
            <span><span class="material-icons">repeat</span>{{ p.frequency_label }}</span>
            <span>{{ p.category }}</span>
            <span v-if="p.school">{{ p.school }}</span>
            <span><span class="material-icons">person</span>{{ p.assignee || 'automático' }}</span>
            <router-link v-if="p.last_ticket_id" :to="`/tickets/${p.last_ticket_id}`" @click.stop>último: T-{{ p.last_ticket_id }}</router-link>
          </div>
        </div>
        <div class="plan-buttons">
          <button class="hd-btn hd-btn-outline" type="button" title="Criar o ticket agora" @click="runNow(p)"><span class="material-icons">play_arrow</span> Criar agora</button>
          <button class="hd-icon-btn" type="button" title="Editar" @click="edit(p)"><span class="material-icons">edit</span></button>
          <button class="hd-icon-btn" type="button" title="Apagar" @click="remove(p)"><span class="material-icons" style="color:#EF4444">delete</span></button>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
// Manutenção planeada: recurring tickets (backend app/api/v1/planning.py)
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../../boot/axios'
import { getCategories, getSchools } from '../../api/tickets'
import { searchUsers } from '../../api/users'
import { confirmDialog, notifyError, notifySuccess } from '../../utils/feedback'

const router = useRouter()
const items = ref<any[]>([])
const frequencies = ref<Record<string, string>>({})
const categories = ref<any[]>([])
const schools = ref<any[]>([])
const technicians = ref<any[]>([])
const loading = ref(true)
const saving = ref(false)
const editing = ref<any | null>(null)

async function load() {
  try {
    const { data } = await api.get('/api/v1/planning')
    items.value = data.items
    frequencies.value = data.frequencies
  } catch (e) {
    notifyError(e, 'Não foi possível carregar as manutenções.')
  } finally {
    loading.value = false
  }
}

function startNew() {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  editing.value = {
    title: '', description: '', category_id: categories.value[0]?.id, school_id: schools.value[0]?.id,
    assignee_id: null, priority: 'medium', frequency: 'monthly', next_run: d.toISOString().slice(0, 10), active: true,
  }
}

function edit(p: any) {
  editing.value = { ...p }
}

async function save() {
  const p = editing.value
  if (!p) return
  saving.value = true
  try {
    const body = { title: p.title, description: p.description, category_id: p.category_id, school_id: p.school_id, priority: p.priority,
      assignee_id: p.assignee_id, frequency: p.frequency, next_run: p.next_run, active: p.active }
    if (p.id) await api.put(`/api/v1/planning/${p.id}`, body)
    else await api.post('/api/v1/planning', body)
    editing.value = null
    notifySuccess('Manutenção guardada.')
    await load()
  } catch (e) {
    notifyError(e, 'Não foi possível guardar.')
  } finally {
    saving.value = false
  }
}

async function remove(p: any) {
  if (!(await confirmDialog(`Apagar a manutenção "${p.title}"? Os tickets já criados ficam.`, { ok: 'Apagar', danger: true }))) return
  try {
    await api.delete(`/api/v1/planning/${p.id}`)
    await load()
  } catch (e) {
    notifyError(e, 'Não foi possível apagar.')
  }
}

async function runNow(p: any) {
  if (!(await confirmDialog(`Criar agora o ticket "${p.title}"? A próxima data marcada mantém-se.`, { ok: 'Criar ticket' }))) return
  try {
    const { data } = await api.post(`/api/v1/planning/${p.id}/run`)
    router.push(`/tickets/${data.ticket_id}`)
  } catch (e) {
    notifyError(e, 'Não foi possível criar o ticket.')
  }
}

const MONTHS = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
const day = (iso: string) => Number(iso.slice(8, 10))
const month = (iso: string) => `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${iso.slice(0, 4)}`

onMounted(async () => {
  const [c, s, t] = await Promise.allSettled([getCategories(), getSchools(), searchUsers('', { technicians_only: true, limit: 100 })])
  if (c.status === 'fulfilled') categories.value = c.value
  if (s.status === 'fulfilled') schools.value = s.value
  if (t.status === 'fulfilled') technicians.value = t.value
  await load()
})
</script>

<style scoped>
.plan-page { max-width: 1000px; }
.plan-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 18px; flex-wrap: wrap; }
.plan-intro { color: var(--c-muted); font-size: 14px; margin: 0; max-width: 620px; }
.plan-form { padding: 18px 20px; margin-bottom: 18px; }
.plan-form-title { font-weight: 800; margin-bottom: 12px; }
.plan-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.plan-grid label { display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; font-weight: 700; color: var(--c-muted); }
.plan-grid .span-2 { grid-column: 1 / -1; }
@media (max-width: 640px) { .plan-grid { grid-template-columns: 1fr; } }
.plan-actions { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-top: 14px; }
.plan-active { margin-right: auto; display: inline-flex; gap: 6px; align-items: center; font-size: 13px; font-weight: 600; }
.plan-empty { padding: 50px; text-align: center; color: var(--c-muted); display: flex; flex-direction: column; align-items: center; gap: 8px; }
.plan-empty .material-icons { font-size: 38px; }
.plan-list { display: flex; flex-direction: column; gap: 10px; }
.plan-item { display: flex; align-items: center; gap: 16px; padding: 14px 16px; }
.plan-item.off { opacity: .6; }
.plan-date { width: 58px; text-align: center; border-radius: 12px; background: var(--c-primary-soft); color: var(--c-primary); padding: 6px 0; flex-shrink: 0; }
.plan-day { font-size: 22px; font-weight: 800; line-height: 1.1; }
.plan-month { font-size: 11px; font-weight: 700; text-transform: uppercase; }
.plan-main { flex: 1; min-width: 0; }
.plan-title { font-weight: 700; color: var(--c-text); }
.plan-paused { font-size: 11px; font-weight: 700; color: var(--c-muted); border: 1px solid var(--c-border); border-radius: 6px; padding: 0 6px; margin-left: 6px; }
.plan-meta { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12.5px; color: var(--c-muted); margin-top: 4px; }
.plan-meta span { display: inline-flex; align-items: center; gap: 3px; }
.plan-meta .material-icons { font-size: 15px; }
.plan-buttons { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
@media (max-width: 640px) { .plan-item { flex-wrap: wrap; } .plan-buttons { width: 100%; justify-content: flex-end; } }
</style>
