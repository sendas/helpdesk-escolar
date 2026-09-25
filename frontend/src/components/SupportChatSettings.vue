<template>
  <div class="hd-card" style="padding:28px;max-width:760px">
    <div class="scs-status" :class="realtimeStatus">
      <span class="material-icons">{{ realtimeStatus === 'live' ? 'bolt' : realtimeStatus === 'polling' ? 'sync' : 'cloud_off' }}</span>
      <div>
        <strong>{{ statusTitle }}</strong>
        <small>{{ statusHint }}</small>
      </div>
    </div>

    <div class="hd-row" style="justify-content:space-between;align-items:center;margin:24px 0 14px">
      <div>
        <div style="font-weight:600;font-size:14px">Apoio ao vivo (balão de chat)</div>
        <div style="font-size:12px;color:var(--c-muted);margin-top:2px">Os docentes veem um balão de chat no canto do ecrã e falam em tempo real com a equipa de apoio</div>
      </div>
      <div class="hd-toggle-wrap" @click="enabled = !enabled">
        <div class="hd-toggle-track" :class="{ on: enabled }"><div class="hd-toggle-thumb"></div></div>
      </div>
    </div>

    <div :style="{ opacity: enabled ? 1 : 0.5 }">
      <div style="font-weight:600;font-size:13px;margin-bottom:8px">Horário de atendimento</div>
      <div class="scs-days">
        <div v-for="d in days" :key="d.key" class="scs-day" :class="{ off: !hours[d.key].enabled }">
          <span class="hd-toggle-wrap" @click="hours[d.key].enabled = !hours[d.key].enabled">
            <span class="hd-toggle-track" :class="{ on: hours[d.key].enabled }"><span class="hd-toggle-thumb"></span></span>
          </span>
          <strong>{{ d.label }}</strong>
          <input v-model="hours[d.key].start" type="time" class="hd-input" :disabled="!hours[d.key].enabled" />
          <span>às</span>
          <input v-model="hours[d.key].end" type="time" class="hd-input" :disabled="!hours[d.key].enabled" />
        </div>
      </div>

      <div class="hd-field" style="margin-top:18px;max-width:420px">
        <label class="hd-label">Minutos de espera antes de passar a ticket</label>
        <input v-model.number="waitMinutes" type="number" min="1" max="120" class="hd-input" style="max-width:120px" />
        <p class="hd-hint">Se nenhum técnico aceitar o pedido neste tempo, a conversa é convertida num ticket automaticamente. Fora do horário, a mensagem passa logo a ticket.</p>
      </div>
      <p class="hd-hint">Quem responde ao apoio ao vivo e quem usa o chat da equipa define-se em Utilizadores → Papéis e permissões ("Responder ao apoio ao vivo" e "Usar o chat da equipa").</p>
    </div>

    <div class="hd-row" style="gap:10px;align-items:center;margin-top:16px">
      <button class="hd-btn hd-btn-primary" :disabled="saving" @click="save">
        <span class="material-icons" style="font-size:16px">save</span> Guardar
      </button>
      <span v-if="saved" style="font-size:13px;color:#22C55E">Guardado!</span>
      <span v-if="error" style="font-size:13px;color:#EF4444">{{ error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { getPublicSettings, updateSupportChatSettings } from '../api/settings'
import { realtimeStatus } from '../services/realtime'

const days = [
  { key: '1', label: 'Segunda' }, { key: '2', label: 'Terça' }, { key: '3', label: 'Quarta' }, { key: '4', label: 'Quinta' },
  { key: '5', label: 'Sexta' }, { key: '6', label: 'Sábado' }, { key: '7', label: 'Domingo' },
]
const enabled = ref(true)
const waitMinutes = ref(5)
const hours = reactive<Record<string, { enabled: boolean; start: string; end: string }>>(
  Object.fromEntries(days.map((d) => [d.key, { enabled: false, start: '10:00', end: '13:00' }])),
)
const saving = ref(false)
const saved = ref(false)
const error = ref('')

const statusTitle = computed(() => ({
  live: 'Tempo real ativo',
  polling: 'Tempo real em modo compatível',
  connecting: 'A ligar ao tempo real…',
  offline: 'Tempo real desligado',
}[realtimeStatus.value]))
const statusHint = computed(() => ({
  live: 'Ligação WebSocket direta: mensagens e atualizações chegam no instante.',
  polling: 'A rede ou o proxy à frente do helpdesk bloqueia WebSockets; as atualizações chegam a cada poucos segundos. Para tempo real total, ative "Websockets Support" no proxy.',
  connecting: 'Aguarde um momento.',
  offline: 'Sem ligação ao servidor de tempo real.',
}[realtimeStatus.value]))

onMounted(async () => {
  const s: any = await getPublicSettings()
  enabled.value = s.support_chat_enabled !== false
  waitMinutes.value = s.support_wait_minutes ?? 5
  Object.entries(s.support_hours ?? {}).forEach(([k, v]: [string, any]) => { if (hours[k]) Object.assign(hours[k], v) })
})

async function save() {
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    await updateSupportChatSettings({ enabled: enabled.value, wait_minutes: waitMinutes.value, hours })
    saved.value = true
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Erro ao guardar.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.scs-status { display: flex; gap: 12px; align-items: center; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--c-border); }
.scs-status .material-icons { font-size: 22px; }
.scs-status strong { display: block; font-size: 14px; }
.scs-status small { display: block; font-size: 12px; color: var(--c-muted); margin-top: 2px; }
.scs-status.live { border-color: rgba(34, 197, 94, .4); background: rgba(34, 197, 94, .08); }
.scs-status.live .material-icons { color: #16A34A; }
.scs-status.polling { border-color: rgba(245, 158, 11, .4); background: rgba(245, 158, 11, .08); }
.scs-status.polling .material-icons { color: #D97706; }
.scs-days { display: flex; flex-direction: column; gap: 6px; }
.scs-day { display: grid; grid-template-columns: 44px 90px 110px 24px 110px; align-items: center; gap: 8px; font-size: 13px; }
.scs-day.off strong, .scs-day.off span { color: var(--c-muted); }
.scs-day .hd-input { padding: 6px 8px; }
@media (max-width: 560px) { .scs-day { grid-template-columns: 44px 1fr; } .scs-day input, .scs-day > span:not(.hd-toggle-wrap) { grid-column: 2; } }
</style>
