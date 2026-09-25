<template>
  <div class="hd-card" style="padding:28px;max-width:820px">
    <div class="ts-head">
      <div class="ts-logo"><span class="material-icons">groups</span></div>
      <div>
        <div style="font-weight:700;font-size:15px">Avisos num canal do Microsoft Teams</div>
        <div style="font-size:12.5px;color:var(--c-muted);margin-top:2px">O helpdesk publica cartões num canal (por exemplo "Equipa TIC › Helpdesk"), com um botão para abrir o ticket.</div>
      </div>
      <span class="ts-state" :class="{ on: configured }">{{ configured ? 'Ligado' : 'Não configurado' }}</span>
    </div>

    <details class="ts-howto" :open="!configured">
      <summary>Como obter o endereço no Teams (2 minutos)</summary>
      <ol>
        <li>No Teams, abra o canal onde quer receber os avisos e clique em <strong>⋯ (Mais opções) → Fluxos de trabalho</strong>.</li>
        <li>Escolha o modelo <strong>"Publicar num canal quando é recebido um pedido de webhook"</strong> (<em>Post to a channel when a webhook request is received</em>).</li>
        <li>Dê um nome (ex.: "Helpdesk"), confirme a equipa e o canal e clique em <strong>Adicionar fluxo de trabalho</strong>.</li>
        <li>Copie o endereço que aparece no fim e cole-o aqui em baixo. Depois clique em <strong>Enviar teste</strong>.</li>
      </ol>
      <p>O endereço funciona como uma chave: quem o tiver pode publicar no canal. Não o partilhe.</p>
    </details>

    <div class="hd-field" style="margin-top:18px">
      <label class="hd-label">Endereço do fluxo de trabalho (webhook)</label>
      <input v-model="url" class="hd-input" type="url" placeholder="https://…logic.azure.com/workflows/…" />
    </div>

    <div style="font-weight:600;font-size:13px;margin:18px 0 8px">O que publicar no canal</div>
    <div class="ts-events">
      <label v-for="e in eventOptions" :key="e.key" class="ts-event" :class="{ on: events.includes(e.key) }" @click.prevent="toggle(e.key)">
        <span class="hd-toggle-wrap"><span class="hd-toggle-track" :class="{ on: events.includes(e.key) }"><span class="hd-toggle-thumb"></span></span></span>
        <span><strong>{{ e.label }}</strong><small>{{ e.hint }}</small></span>
      </label>
    </div>

    <div class="hd-row" style="gap:10px;align-items:center;margin-top:18px;flex-wrap:wrap">
      <button class="hd-btn hd-btn-primary" :disabled="saving" @click="save"><span class="material-icons" style="font-size:16px">save</span> Guardar</button>
      <button class="hd-btn hd-btn-outline" :disabled="testing || !url.trim()" @click="test"><span class="material-icons" style="font-size:16px">send</span> {{ testing ? 'A enviar…' : 'Enviar teste' }}</button>
      <span v-if="message" :style="{ fontSize: '13px', color: ok ? '#16A34A' : '#DC2626' }">{{ message }}</span>
    </div>

    <p class="hd-hint" style="margin-top:16px">
      Responder aos tickets diretamente a partir do Teams (com um bot) é um passo seguinte: precisa de registar uma aplicação no Azure e de o helpdesk estar acessível pela internet.
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../boot/axios'

const eventOptions = [
  { key: 'ticket_created', label: 'Novo ticket', hint: 'Assunto, solicitante, escola, categoria e responsável.' },
  { key: 'support_waiting', label: 'Apoio ao vivo à espera', hint: 'Um docente abriu o balão de apoio; botão "Atender".' },
  { key: 'ticket_overdue', label: 'Ticket fora do prazo', hint: 'Uma vez por ticket, quando passa o tempo de resposta.' },
  { key: 'requester_reply', label: 'Resposta de quem fez o pedido', hint: 'O docente respondeu no ticket ou por email.' },
]
const url = ref('')
const events = ref<string[]>([])
const configured = ref(false)
const saving = ref(false)
const testing = ref(false)
const message = ref('')
const ok = ref(false)

function toggle(key: string) {
  events.value = events.value.includes(key) ? events.value.filter((e) => e !== key) : [...events.value, key]
}

onMounted(async () => {
  const { data } = await api.get('/api/v1/settings/teams')
  url.value = data.webhook_url
  events.value = data.events
  configured.value = data.configured
})

async function save() {
  saving.value = true
  message.value = ''
  try {
    const { data } = await api.put('/api/v1/settings/teams', { webhook_url: url.value, events: events.value })
    configured.value = data.configured
    ok.value = true
    message.value = 'Guardado!'
  } catch (e: any) {
    ok.value = false
    message.value = e?.response?.data?.detail || 'Erro ao guardar.'
  } finally {
    saving.value = false
  }
}

async function test() {
  testing.value = true
  message.value = ''
  try {
    await api.post('/api/v1/settings/teams/test', { webhook_url: url.value, events: events.value })
    ok.value = true
    message.value = 'Mensagem de teste enviada — veja o canal no Teams.'
  } catch (e: any) {
    ok.value = false
    message.value = e?.response?.data?.detail || 'Não foi possível enviar o teste.'
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.ts-head { display: flex; gap: 12px; align-items: center; }
.ts-logo { width: 42px; height: 42px; border-radius: 12px; display: grid; place-items: center; color: #fff; background: linear-gradient(135deg, #4B53BC, #7B83EB); flex-shrink: 0; }
.ts-state { margin-left: auto; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: var(--c-bg); color: var(--c-muted); border: 1px solid var(--c-border); white-space: nowrap; }
.ts-state.on { color: #15803D; background: rgba(34, 197, 94, .1); border-color: rgba(34, 197, 94, .3); }
.ts-howto { margin-top: 18px; border: 1px solid var(--c-border); border-radius: 12px; padding: 12px 16px; background: var(--c-bg); font-size: 13px; }
.ts-howto summary { cursor: pointer; font-weight: 700; }
.ts-howto ol { margin: 10px 0 6px; padding-left: 20px; line-height: 1.6; }
.ts-howto p { margin: 0; color: var(--c-muted); font-size: 12px; }
.ts-events { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 8px; }
.ts-event { display: flex; gap: 10px; align-items: flex-start; padding: 10px; border: 1px solid var(--c-border); border-radius: 10px; cursor: pointer; }
.ts-event.on { border-color: var(--c-primary); background: var(--c-primary-soft); }
.ts-event strong { display: block; font-size: 13px; }
.ts-event small { display: block; font-size: 12px; color: var(--c-muted); margin-top: 2px; }
</style>
