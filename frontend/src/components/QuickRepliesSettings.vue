<template>
  <div class="hd-card qr-card">
    <div class="qr-title">Respostas-modelo</div>
    <p class="qr-desc">Botões por cima da caixa de resposta de cada ticket: preenchem o texto e, se indicar, também mudam o estado ao enviar.</p>
    <div v-if="loading" class="qr-empty">A carregar…</div>
    <template v-else>
      <div v-for="(r, i) in replies" :key="i" class="qr-item">
        <div class="qr-row">
          <input v-model="r.label" class="hd-input qr-label" maxlength="40" placeholder="Nome do botão" />
          <select v-model="r.status" class="hd-select qr-status">
            <option value="">Não mudar o estado</option>
            <option v-for="(label, key) in STATUS_LABELS" :key="key" :value="key">Mudar para: {{ label }}</option>
          </select>
          <button class="hd-icon-btn" type="button" title="Subir" :disabled="i === 0" @click="move(i, -1)"><span class="material-icons">arrow_upward</span></button>
          <button class="hd-icon-btn" type="button" title="Descer" :disabled="i === replies.length - 1" @click="move(i, 1)"><span class="material-icons">arrow_downward</span></button>
          <button class="hd-icon-btn" type="button" title="Apagar" @click="replies.splice(i, 1)"><span class="material-icons" style="color:#EF4444">delete</span></button>
        </div>
        <textarea v-model="r.body" class="hd-textarea" rows="2" placeholder="Texto da resposta"></textarea>
      </div>
      <div class="qr-actions">
        <button class="hd-btn hd-btn-outline" type="button" :disabled="replies.length >= 20" @click="replies.push({ label: '', body: '', status: '' })">
          <span class="material-icons">add</span> Nova resposta-modelo
        </button>
        <span v-if="saved" class="qr-ok">Guardado!</span>
        <button class="hd-btn hd-btn-primary" type="button" :disabled="saving" @click="save"><span class="material-icons">save</span> Guardar</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../boot/axios'
import { notifyError } from '../utils/feedback'
import { STATUS_LABELS } from '../utils/ticketStatus'

const replies = ref<{ label: string; body: string; status: string }[]>([])
const loading = ref(true)
const saving = ref(false)
const saved = ref(false)

onMounted(async () => {
  try { replies.value = (await api.get('/api/v1/settings/quick-replies')).data.replies } catch (e) { notifyError(e) } finally { loading.value = false }
})

function move(i: number, d: number) {
  const list = replies.value
  ;[list[i], list[i + d]] = [list[i + d], list[i]]
}

async function save() {
  saving.value = true
  try {
    replies.value = (await api.put('/api/v1/settings/quick-replies', { replies: replies.value })).data.replies
    saved.value = true
    setTimeout(() => { saved.value = false }, 2500)
  } catch (e) {
    notifyError(e, 'Não foi possível guardar as respostas-modelo.')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.qr-card { padding: 22px 24px; max-width: 860px; }
.qr-title { font-weight: 700; font-size: 14.5px; }
.qr-desc { font-size: 12.5px; color: var(--c-muted); margin: 3px 0 16px; }
.qr-item { border: 1px solid var(--c-border); border-radius: 12px; padding: 10px; margin-bottom: 10px; display: flex; flex-direction: column; gap: 8px; }
.qr-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.qr-label { flex: 1; min-width: 160px; }
.qr-status { width: auto; }
.qr-actions { display: flex; align-items: center; gap: 10px; justify-content: flex-end; flex-wrap: wrap; }
.qr-actions .hd-btn:first-child { margin-right: auto; }
.qr-actions .material-icons { font-size: 16px; }
.qr-ok { color: #16A34A; font-weight: 700; font-size: 13px; }
.qr-empty { color: var(--c-muted); padding: 20px 0; }
</style>
