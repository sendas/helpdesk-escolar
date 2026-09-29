<template>
  <div class="hd-card nw-card">
    <div class="nw-row">
      <div>
        <div class="nw-title">Aviso de novidades</div>
        <p class="nw-desc">Uma janela com as alterações mais importantes, mostrada <strong>uma vez</strong> a cada pessoa quando entra
          (em qualquer dispositivo). Escreva a pensar no utilizador comum: frases curtas e o que muda para ele.</p>
      </div>
      <div class="hd-toggle-wrap" role="switch" tabindex="0" :aria-checked="enabled" @click="enabled = !enabled"
           @keydown.enter.prevent="enabled = !enabled" @keydown.space.prevent="enabled = !enabled">
        <div class="hd-toggle-track" :class="{ on: enabled }"><div class="hd-toggle-thumb"></div></div>
      </div>
    </div>

    <div class="nw-grid">
      <label>Título <input v-model="title" class="hd-input" maxlength="80" /></label>
      <label>Mostrar a
        <select v-model="audience" class="hd-select">
          <option value="all">Todas as pessoas</option>
          <option value="users">Só a quem não é da equipa de apoio</option>
        </select>
      </label>
    </div>

    <div v-for="(it, i) in items" :key="i" class="nw-item">
      <div class="nw-item-row">
        <select v-model="it.icon" class="hd-select nw-icon-select" :title="'Ícone'">
          <option v-for="ic in ICONS" :key="ic.v" :value="ic.v">{{ ic.l }}</option>
        </select>
        <span class="material-icons nw-icon-preview">{{ it.icon }}</span>
        <input v-model="it.title" class="hd-input" maxlength="80" placeholder="Título (ex.: Avalie o atendimento)" />
        <button class="hd-icon-btn" type="button" title="Subir" :disabled="i === 0" @click="move(i, -1)"><span class="material-icons">arrow_upward</span></button>
        <button class="hd-icon-btn" type="button" title="Descer" :disabled="i === items.length - 1" @click="move(i, 1)"><span class="material-icons">arrow_downward</span></button>
        <button class="hd-icon-btn" type="button" title="Apagar" @click="items.splice(i, 1)"><span class="material-icons" style="color:#EF4444">delete</span></button>
      </div>
      <textarea v-model="it.text" class="hd-textarea" rows="2" maxlength="400" placeholder="Explicação curta"></textarea>
    </div>
    <button class="hd-btn hd-btn-outline" type="button" :disabled="items.length >= 10" @click="items.push({ icon: 'new_releases', title: '', text: '' })">
      <span class="material-icons">add</span> Acrescentar novidade
    </button>

    <div class="nw-actions">
      <button class="hd-btn hd-btn-outline" type="button" :disabled="!items.length" @click="previewing = true"><span class="material-icons">visibility</span> Pré-visualizar</button>
      <span v-if="saved" class="nw-ok">{{ saved }}</span>
      <button class="hd-btn hd-btn-outline" type="button" :disabled="saving" title="Guarda e volta a mostrar o aviso a todos, mesmo a quem já o fechou" @click="save(true)">
        <span class="material-icons">campaign</span> Publicar como novas
      </button>
      <button class="hd-btn hd-btn-primary" type="button" :disabled="saving" @click="save(false)"><span class="material-icons">save</span> Guardar</button>
    </div>
    <NewsPopup v-if="previewing" :title="title" :items="items" @close="previewing = false" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../boot/axios'
import { getPublicSettings } from '../api/settings'
import { notifyError } from '../utils/feedback'
import NewsPopup from './NewsPopup.vue'

const ICONS = [
  { v: 'new_releases', l: 'Novidade' }, { v: 'auto_awesome', l: 'Destaque' }, { v: 'badge', l: 'Perfil' },
  { v: 'view_agenda', l: 'Lista' }, { v: 'star', l: 'Estrela' }, { v: 'content_paste', l: 'Colar' },
  { v: 'photo_camera', l: 'Foto' }, { v: 'notifications', l: 'Notificação' }, { v: 'mail', l: 'Email' },
  { v: 'lock', l: 'Privado' }, { v: 'alarm', l: 'Lembrete' }, { v: 'chat', l: 'Chat' },
  { v: 'dark_mode', l: 'Modo escuro' }, { v: 'school', l: 'Escola' }, { v: 'build', l: 'Técnico' },
  { v: 'speed', l: 'Rapidez' }, { v: 'security', l: 'Segurança' }, { v: 'help', l: 'Ajuda' },
]
const enabled = ref(false)
const audience = ref('all')
const title = ref('Novidades no Helpdesk')
const items = ref<{ icon: string; title: string; text: string }[]>([])
const saving = ref(false)
const saved = ref('')
const previewing = ref(false)

onMounted(async () => {
  try {
    const s: any = await getPublicSettings()
    enabled.value = !!s.news_enabled
    audience.value = s.news_audience || 'all'
    title.value = s.news_title || 'Novidades no Helpdesk'
    items.value = (s.news_items || []).map((it: any) => ({ ...it }))
  } catch (e) {
    notifyError(e)
  }
})

function move(i: number, d: number) {
  const list = items.value
  ;[list[i], list[i + d]] = [list[i + d], list[i]]
}

async function save(republish: boolean) {
  saving.value = true
  try {
    await api.put('/api/v1/settings/news', { enabled: enabled.value, audience: audience.value, title: title.value, items: items.value, republish })
    saved.value = republish ? 'Publicado — volta a aparecer a todos.' : 'Guardado!'
    setTimeout(() => { saved.value = '' }, 3000)
  } catch (e) {
    notifyError(e, 'Não foi possível guardar.')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.nw-card { padding: 22px 24px; max-width: 860px; }
.nw-row { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.nw-title { font-weight: 700; font-size: 14.5px; }
.nw-desc { font-size: 12.5px; color: var(--c-muted); margin: 3px 0 16px; line-height: 1.5; }
.nw-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 14px; }
.nw-grid label { display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; font-weight: 700; color: var(--c-muted); }
@media (max-width: 640px) { .nw-grid { grid-template-columns: 1fr; } }
.nw-item { border: 1px solid var(--c-border); border-radius: 12px; padding: 10px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px; }
.nw-item-row { display: flex; gap: 6px; align-items: center; }
.nw-item-row .hd-input { flex: 1; min-width: 0; }
.nw-icon-select { width: 130px; }
.nw-icon-preview { color: var(--c-primary); background: var(--c-primary-soft); border-radius: 10px; padding: 6px; font-size: 20px; }
.nw-actions { display: flex; justify-content: flex-end; align-items: center; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.nw-actions .hd-btn:first-child { margin-right: auto; }
.nw-card .material-icons { font-size: 16px; }
.nw-card .nw-icon-preview { font-size: 20px; }
.nw-ok { color: #16A34A; font-weight: 700; font-size: 13px; }
</style>
