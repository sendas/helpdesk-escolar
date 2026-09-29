<template>
  <div class="hd-card rp-card">
    <div class="rp-row">
      <div>
        <div class="rp-title">Relatório mensal por email</div>
        <p class="rp-desc">No dia 1 de cada mês é enviado um resumo do mês anterior: pedidos novos e resolvidos, tempo médio de resolução,
          escolas, categorias, técnicos e satisfação dos utilizadores. Pensado para a Direção.</p>
      </div>
      <div class="hd-toggle-wrap" role="switch" tabindex="0" :aria-checked="enabled" @click="enabled = !enabled"
           @keydown.enter.prevent="enabled = !enabled" @keydown.space.prevent="enabled = !enabled">
        <div class="hd-toggle-track" :class="{ on: enabled }"><div class="hd-toggle-thumb"></div></div>
      </div>
    </div>
    <div class="hd-field" style="margin-top:14px">
      <label class="hd-label">Enviar para (separe por vírgulas)</label>
      <input v-model="recipientsRaw" class="hd-input" placeholder="direcao@escola.pt, subdiretor@escola.pt" />
    </div>
    <p v-if="lastSent" class="rp-desc">Último relatório automático enviado: {{ lastSent }}.</p>
    <div class="rp-actions">
      <label class="rp-month">Mês <input v-model="month" type="month" class="hd-input" /></label>
      <button class="hd-btn hd-btn-outline" type="button" @click="preview"><span class="material-icons">visibility</span> Pré-visualizar</button>
      <button class="hd-btn hd-btn-outline" type="button" :disabled="sending" @click="sendNow"><span class="material-icons">send</span> {{ sending ? 'A enviar…' : 'Enviar agora' }}</button>
      <span v-if="saved" class="rp-ok">Guardado!</span>
      <button class="hd-btn hd-btn-primary" type="button" :disabled="saving" @click="save"><span class="material-icons">save</span> Guardar</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../boot/axios'
import { notifyError, notifySuccess } from '../utils/feedback'

const enabled = ref(false)
const recipientsRaw = ref('')
const lastSent = ref('')
const saving = ref(false)
const saved = ref(false)
const sending = ref(false)
const prev = new Date(); prev.setDate(1); prev.setMonth(prev.getMonth() - 1)
const month = ref(`${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, '0')}`)

function apply(d: any) {
  enabled.value = d.enabled
  recipientsRaw.value = (d.recipients || []).join(', ')
  lastSent.value = d.last_sent
}

onMounted(async () => {
  try { apply((await api.get('/api/v1/settings/report')).data) } catch (e) { notifyError(e) }
})

async function save() {
  saving.value = true
  try {
    const recipients = recipientsRaw.value.split(',').map((e) => e.trim()).filter(Boolean)
    apply((await api.put('/api/v1/settings/report', { enabled: enabled.value, recipients })).data)
    saved.value = true
    setTimeout(() => { saved.value = false }, 2500)
  } catch (e) {
    notifyError(e, 'Não foi possível guardar.')
  } finally {
    saving.value = false
  }
}

async function preview() {
  const win = window.open('', '_blank')
  try {
    const { data } = await api.get('/api/v1/admin/report/html', { params: { month: month.value }, responseType: 'text' })
    if (win) { win.document.open(); win.document.write(data); win.document.close() }
  } catch (e) {
    win?.close()
    notifyError(e, 'Não foi possível gerar o relatório.')
  }
}

async function sendNow() {
  sending.value = true
  try {
    await save()
    const { data } = await api.post('/api/v1/admin/report/send', null, { params: { month: month.value } })
    notifySuccess(`Relatório de ${data.month_label} enviado para ${data.sent_to.join(', ')}.`)
  } catch (e) {
    notifyError(e, 'Não foi possível enviar.')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.rp-card { padding: 22px 24px; max-width: 820px; }
.rp-row { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.rp-title { font-weight: 700; font-size: 14.5px; }
.rp-desc { font-size: 12.5px; color: var(--c-muted); margin: 3px 0 0; line-height: 1.5; }
.rp-actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; justify-content: flex-end; margin-top: 16px; }
.rp-actions .material-icons { font-size: 16px; }
.rp-month { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; margin-right: auto; }
.rp-month .hd-input { width: auto; padding: 5px 10px; }
.rp-ok { color: #16A34A; font-weight: 700; font-size: 13px; }
</style>
