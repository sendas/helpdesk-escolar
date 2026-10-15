<template>
  <section class="set-card rooms-card">
    <div class="rooms-head">
      <div>
        <div class="set-card-title">Salas e espaços</div>
        <p class="rooms-desc">Quem abre um ticket escolhe a sala da lista da escola. Uma sala desativada deixa de aparecer, mas os tickets antigos mantêm-na.</p>
      </div>
      <select v-model.number="schoolId" class="hd-select rooms-school" @change="load">
        <option v-for="s in schools" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>
    </div>

    <div v-if="loading" class="rooms-empty">A carregar…</div>
    <div v-else-if="!rooms.length" class="rooms-empty">Ainda não há salas nesta escola.</div>
    <div v-else class="rooms-list">
      <div v-for="r in rooms" :key="r.id" class="rooms-item" :class="{ off: !r.active }">
        <template v-if="editing?.id === r.id">
          <input v-model="editing.code" class="hd-input rooms-code" maxlength="30" placeholder="Código" />
          <input v-model="editing.name" class="hd-input" maxlength="120" placeholder="Nome" />
          <input v-model="editing.kind" class="hd-input rooms-kind" maxlength="60" list="room-kinds" placeholder="Tipo" />
          <label class="rooms-active"><input v-model="editing.active" type="checkbox" /> Ativa</label>
          <button class="hd-btn hd-btn-primary" type="button" :disabled="!editing.name.trim()" @click="save">Guardar</button>
          <button class="hd-btn hd-btn-outline" type="button" @click="editing = null">Cancelar</button>
        </template>
        <template v-else>
          <span class="rooms-code-tag">{{ r.code || '—' }}</span>
          <span class="rooms-name">{{ r.name }}</span>
          <span class="rooms-kind-tag">{{ r.kind }}</span>
          <span v-if="!r.active" class="rooms-off">desativada</span>
          <button class="hd-icon-btn" type="button" title="Editar" @click="editing = { ...r }"><span class="material-icons">edit</span></button>
          <button class="hd-icon-btn" type="button" title="Apagar" @click="remove(r)"><span class="material-icons" style="color:#EF4444">delete</span></button>
        </template>
      </div>
    </div>

    <div v-if="editing && !editing.id" class="rooms-item rooms-new">
      <input v-model="editing.code" class="hd-input rooms-code" maxlength="30" placeholder="Código (ex.: EQ40)" />
      <input v-model="editing.name" class="hd-input" maxlength="120" placeholder="Nome (ex.: Sala 40)" />
      <input v-model="editing.kind" class="hd-input rooms-kind" maxlength="60" list="room-kinds" placeholder="Tipo" />
      <button class="hd-btn hd-btn-primary" type="button" :disabled="!editing.name.trim()" @click="save">Adicionar</button>
      <button class="hd-btn hd-btn-outline" type="button" @click="editing = null">Cancelar</button>
    </div>
    <button v-else-if="schoolId" class="hd-btn hd-btn-outline rooms-add" type="button"
            @click="editing = { school_id: schoolId, code: '', name: '', kind: 'Sala de aula', active: true }">
      <span class="material-icons">add</span> Nova sala
    </button>

    <div v-if="!loading && lists.length && !rooms.length && !editing" class="rooms-import">
      <span>Carregar a lista de espaços do agrupamento:</span>
      <select v-model="listKey" class="hd-select">
        <option v-for="l in lists" :key="l.key" :value="l.key">{{ l.name }} ({{ l.count }})</option>
      </select>
      <button class="hd-btn hd-btn-outline" type="button" :disabled="!listKey || importing" @click="doImport">
        <span class="material-icons">playlist_add</span> {{ importing ? 'A carregar…' : 'Carregar para esta escola' }}
      </button>
    </div>

    <datalist id="room-kinds">
      <option v-for="k in kinds" :key="k" :value="k" />
    </datalist>
  </section>
</template>

<script setup lang="ts">
// Rooms of each school (backend app/api/v1/rooms.py); the first list comes from app/seed/rooms.json
import { computed, ref, watch } from 'vue'
import { deleteRoom, getRoomLists, getRooms, importRooms, saveRoom, type Room } from '../api/tickets'
import { confirmDialog, notifyError, notifySuccess } from '../utils/feedback'

const props = defineProps<{ schools: { id: number; name: string }[] }>()
const schoolId = ref<number | null>(null)
const rooms = ref<Room[]>([])
const loading = ref(false)
const editing = ref<any | null>(null)
const lists = ref<{ key: string; name: string; count: number }[]>([])
const listKey = ref('')
const importing = ref(false)

// Suggest the list whose school name looks like the chosen school
function guessList() {
  const school = props.schools.find((s) => s.id === schoolId.value)
  const name = (school?.name || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  const hit = lists.value.find((l) => (l.key === 'EQ' && /queiro/.test(name)) || (l.key === 'VG' && /vasco|gama/.test(name)) || (l.key === 'PN' && /parque|nacoes/.test(name)))
  listKey.value = hit?.key || lists.value[0]?.key || ''
}

async function doImport() {
  if (!schoolId.value || !listKey.value) return
  importing.value = true
  try {
    const r = await importRooms(schoolId.value, listKey.value)
    notifySuccess(r.added ? `${r.added} salas carregadas.` : 'Todas as salas desta lista já existiam.')
    await load()
  } catch (e) {
    notifyError(e, 'Não foi possível carregar a lista.')
  } finally {
    importing.value = false
  }
}
const kinds = computed(() => [...new Set(['Sala de aula', 'Sala TIC', 'Sala específica', 'Laboratório', 'Biblioteca', 'Espaço M',
  'Sala CAA', 'Sala de estudo', 'Educação Física', 'Auditório', ...rooms.value.map((r) => r.kind)])])

async function load() {
  editing.value = null
  if (!schoolId.value) return
  loading.value = true
  guessList()
  try {
    rooms.value = await getRooms(schoolId.value, true)
  } catch (e) {
    notifyError(e, 'Não foi possível carregar as salas.')
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!editing.value) return
  try {
    await saveRoom({ ...editing.value, kind: editing.value.kind || 'Sala de aula' })
    await load()
  } catch (e) {
    notifyError(e, 'Não foi possível guardar a sala.')
  }
}

async function remove(r: Room) {
  const ok = await confirmDialog(`Apagar "${r.label}"? Os tickets dessa sala ficam sem sala indicada. Para a esconder sem perder a ligação, desative-a.`,
    { ok: 'Apagar', danger: true })
  if (!ok) return
  try {
    await deleteRoom(r.id)
    await load()
  } catch (e) {
    notifyError(e, 'Não foi possível apagar a sala.')
  }
}

getRoomLists().then((l) => { lists.value = l; guessList() }).catch(() => {})

watch(() => props.schools, (list) => {
  if (!schoolId.value && list.length) {
    schoolId.value = list[0].id
    load()
  }
}, { immediate: true })
</script>

<style scoped>
.rooms-card { margin-top: 16px; }
.rooms-head { display: flex; gap: 16px; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; margin-bottom: 12px; }
.rooms-desc { color: var(--c-muted); font-size: 13px; margin: 4px 0 0; max-width: 560px; }
.rooms-school { max-width: 320px; }
.rooms-empty { color: var(--c-muted); font-size: 13px; padding: 12px 0; }
.rooms-list { display: flex; flex-direction: column; border: 1px solid var(--c-border); border-radius: 10px; max-height: 460px; overflow: auto; }
.rooms-item { display: flex; align-items: center; gap: 10px; padding: 7px 10px; border-bottom: 1px solid var(--c-border); flex-wrap: wrap; }
.rooms-item:last-child { border-bottom: 0; }
.rooms-item.off { opacity: .55; }
.rooms-code-tag { font-size: 11.5px; font-weight: 800; color: var(--c-primary); min-width: 86px; }
.rooms-name { flex: 1; min-width: 140px; font-size: 13.5px; }
.rooms-kind-tag { font-size: 11.5px; color: var(--c-muted); border: 1px solid var(--c-border); border-radius: 6px; padding: 1px 6px; }
.rooms-off { font-size: 11px; font-weight: 700; color: #B45309; }
.rooms-code { max-width: 130px; }
.rooms-kind { max-width: 180px; }
.rooms-item .hd-input { flex: 1; min-width: 110px; padding: 6px 9px; font-size: 13px; }
.rooms-item .rooms-code, .rooms-item .rooms-kind { flex: 0 1 auto; }
.rooms-active { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; }
.rooms-new { border: 1px dashed var(--c-border); border-radius: 10px; margin-top: 10px; }
.rooms-add { margin-top: 10px; }
.rooms-import { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 13px; color: var(--c-muted); margin: 0 0 12px; }
.rooms-import .hd-select { max-width: 320px; }
</style>
