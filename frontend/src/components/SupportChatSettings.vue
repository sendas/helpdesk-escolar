<template>
  <div class="scs">
    <!-- Main switch: saved immediately -->
    <section class="scs-switch" :class="{ on: enabled }">
      <div class="scs-switch-icon"><span class="material-icons">support_agent</span></div>
      <div class="scs-switch-text">
        <strong>Apoio ao vivo {{ enabled ? 'ligado' : 'desligado' }}</strong>
        <span v-if="enabled">Os docentes veem o balão "Apoio ao vivo", a faixa no Painel inicial e a entrada no menu.</span>
        <span v-else>Ninguém vê o balão de chat. Ligue quando a equipa estiver pronta para atender.</span>
      </div>
      <button class="scs-switch-btn" :class="{ on: enabled }" :disabled="saving" @click="toggleEnabled">
        <span class="hd-toggle-track" :class="{ on: enabled }"><span class="hd-toggle-thumb"></span></span>
        {{ enabled ? 'Desligar' : 'Ligar' }}
      </button>
    </section>
    <p v-if="error" class="scs-error">{{ error }}</p>

    <section class="scs-card" :class="{ dim: !enabled }">
      <div class="scs-title">Horário de atendimento</div>
      <p class="scs-desc">Fora deste horário, a mensagem do docente passa logo a ticket.</p>
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

      <div class="hd-field" style="margin-top:18px;max-width:440px">
        <label class="hd-label">Minutos de espera antes de passar a ticket</label>
        <input v-model.number="waitMinutes" type="number" min="1" max="120" class="hd-input" style="max-width:120px" />
        <p class="hd-hint">Se nenhum técnico aceitar o pedido neste tempo, a conversa é convertida num ticket automaticamente.</p>
      </div>
      <div class="scs-actions">
        <span v-if="saved" style="font-size:13px;color:#16A34A">Guardado!</span>
        <button class="hd-btn hd-btn-primary" :disabled="saving" @click="save()">
          <span class="material-icons" style="font-size:16px">save</span> Guardar horário
        </button>
      </div>
    </section>

    <section class="scs-card">
      <div class="scs-title">Quem responde e quem usa o chat</div>
      <p class="scs-desc">Define-se por papel em <router-link to="/admin/users">Utilizadores → Papéis e permissões</router-link>: "Responder ao apoio ao vivo" e "Usar o chat da equipa".</p>
    </section>

    <section class="scs-status" :class="realtimeStatus">
      <span class="material-icons">{{ realtimeStatus === 'live' ? 'bolt' : realtimeStatus === 'polling' ? 'sync' : 'cloud_off' }}</span>
      <div>
        <strong>{{ statusTitle }}</strong>
        <small>{{ statusHint }}</small>
      </div>
    </section>
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
const enabled = ref(false)
const emit = defineEmits<{ (e: 'changed'): void }>()
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
  enabled.value = s.support_chat_enabled === true
  waitMinutes.value = s.support_wait_minutes ?? 5
  Object.entries(s.support_hours ?? {}).forEach(([k, v]: [string, any]) => { if (hours[k]) Object.assign(hours[k], v) })
})

async function toggleEnabled() {
  const previous = enabled.value
  enabled.value = !previous
  if (!(await save(false))) enabled.value = previous
}

async function save(showSaved = true) {
  saving.value = true
  saved.value = false
  error.value = ''
  try {
    await updateSupportChatSettings({ enabled: enabled.value, wait_minutes: waitMinutes.value, hours })
    saved.value = showSaved
    if (showSaved) setTimeout(() => { saved.value = false }, 3000)
    emit('changed')
    return true
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Erro ao guardar.'
    return false
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.scs { display: flex; flex-direction: column; gap: 16px; }
.scs-switch { display: flex; align-items: center; gap: 16px; padding: 20px 22px; border-radius: 16px; border: 1px solid var(--c-border); background: var(--c-surface); }
.scs-switch.on { border-color: rgba(34, 197, 94, .45); background: linear-gradient(135deg, rgba(34, 197, 94, .08), rgba(8, 145, 178, .08)); }
.scs-switch-icon { width: 46px; height: 46px; border-radius: 14px; display: grid; place-items: center; color: #fff; background: linear-gradient(135deg, #64748B, #94A3B8); flex-shrink: 0; }
.scs-switch.on .scs-switch-icon { background: linear-gradient(135deg, #16A34A, #0891B2); }
.scs-switch-text { flex: 1; min-width: 0; }
.scs-switch-text strong { display: block; font-size: 16px; }
.scs-switch-text span { display: block; font-size: 13px; color: var(--c-muted); margin-top: 2px; }
.scs-switch-btn { display: inline-flex; align-items: center; gap: 10px; padding: 9px 16px; border-radius: 12px; border: 1px solid var(--c-border); background: var(--c-surface); font-weight: 800; font-size: 13.5px; color: var(--c-text); cursor: pointer; white-space: nowrap; }
.scs-switch-btn .hd-toggle-track { position: relative; display: inline-block; width: 40px; height: 22px; border-radius: 11px; }
.scs-switch-btn.on { color: #15803D; border-color: rgba(34, 197, 94, .45); }
.scs-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 16px; padding: 22px 24px; }
.scs-card.dim { opacity: .75; }
.scs-title { font-weight: 700; font-size: 14.5px; }
.scs-desc { font-size: 12.5px; color: var(--c-muted); margin: 3px 0 14px; }
.scs-actions { display: flex; justify-content: flex-end; align-items: center; gap: 12px; }
.scs-error { color: #DC2626; font-size: 13px; margin: -6px 0 0; }
@media (max-width: 600px) { .scs-switch { flex-wrap: wrap; } .scs-switch-btn { width: 100%; justify-content: center; } }

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
