<template>
  <div class="hd-page notif-page">
    <p class="np-intro">
      Escolha o que quer receber <strong>por email</strong> e <strong>como notificação</strong> no telemóvel ou no computador.
      Nunca recebe avisos das suas próprias ações.
    </p>

    <div v-if="loading" class="np-empty">A carregar…</div>
    <div v-else-if="error" class="np-empty np-error">{{ error }}</div>
    <section v-else class="hd-card np-card">
      <div class="np-head">
        <span></span>
        <span class="np-col"><span class="material-icons">mail</span> Email</span>
        <span class="np-col"><span class="material-icons">notifications</span> Notificação</span>
      </div>
      <div v-for="k in kinds" :key="k.key" class="np-row">
        <div class="np-text">
          <div class="np-label">{{ k.label }}</div>
          <div class="np-desc">{{ k.description }}</div>
        </div>
        <div v-for="ch in ['email', 'push']" :key="ch" class="np-col">
          <div
            v-if="k.channels.includes(ch)"
            class="hd-toggle-wrap"
            role="switch"
            tabindex="0"
            :aria-checked="!!prefs[k.key]?.[ch]"
            :aria-label="`${k.label} — ${ch === 'email' ? 'email' : 'notificação'}`"
            @click="toggle(k.key, ch)"
            @keydown.enter.prevent="toggle(k.key, ch)"
            @keydown.space.prevent="toggle(k.key, ch)"
          >
            <div class="hd-toggle-track" :class="{ on: prefs[k.key]?.[ch] }"><div class="hd-toggle-thumb"></div></div>
          </div>
          <span v-else class="np-na">—</span>
        </div>
      </div>
      <div class="np-foot">
        <span v-if="saved" class="np-saved"><span class="material-icons">check_circle</span> Guardado</span>
        <button type="button" class="hd-btn hd-btn-outline" :disabled="saving" @click="resetDefaults">Repor as opções recomendadas</button>
      </div>
    </section>
    <p class="np-note">
      As notificações no telemóvel/computador precisam de estar ativadas no sino <span class="material-icons" style="font-size:15px;vertical-align:-3px">notifications</span> no topo da página.
      Num ticket que fez, também pode desligar os emails só desse ticket ("Atualizações por email").
    </p>
  </div>
</template>

<script setup lang="ts">
// "As minhas notificações": what each person is told by email and by push (backend services/notification_prefs.py)
import { onMounted, ref } from 'vue'
import { api } from '../boot/axios'
import { errorMessage, notifyError } from '../utils/feedback'

type Prefs = Record<string, Record<string, boolean>>
const kinds = ref<{ key: string; label: string; description: string; channels: string[] }[]>([])
const prefs = ref<Prefs>({})
const defaults = ref<Prefs>({})
const loading = ref(true)
const saving = ref(false)
const saved = ref(false)
const error = ref('')
let savedTimer: ReturnType<typeof setTimeout> | null = null

function apply(data: any) {
  kinds.value = data.kinds
  prefs.value = data.prefs
  defaults.value = data.defaults
}

onMounted(async () => {
  try {
    apply((await api.get('/api/v1/users/me/notifications')).data)
  } catch (e) {
    error.value = errorMessage(e, 'Não foi possível carregar as suas preferências.')
  } finally {
    loading.value = false
  }
})

async function save(next: Prefs) {
  const previous = prefs.value
  prefs.value = next
  saving.value = true
  try {
    apply((await api.put('/api/v1/users/me/notifications', { prefs: next })).data)
    saved.value = true
    if (savedTimer) clearTimeout(savedTimer)
    savedTimer = setTimeout(() => { saved.value = false }, 2000)
  } catch (e) {
    prefs.value = previous
    notifyError(e, 'Não foi possível guardar.')
  } finally {
    saving.value = false
  }
}

function toggle(kind: string, channel: string) {
  const next: Prefs = JSON.parse(JSON.stringify(prefs.value))
  next[kind] = { ...(next[kind] ?? {}), [channel]: !next[kind]?.[channel] }
  save(next)
}

function resetDefaults() {
  save(JSON.parse(JSON.stringify(defaults.value)))
}
</script>

<style scoped>
.notif-page { max-width: 860px; }
.np-intro { color: var(--c-muted); margin: 0 0 18px; font-size: 14px; }
.np-card { padding: 6px 20px 14px; }
.np-head, .np-row { display: grid; grid-template-columns: minmax(0, 1fr) 110px 110px; align-items: center; gap: 12px; }
.np-head { padding: 12px 0; border-bottom: 1px solid var(--c-border); font-size: 12px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; color: var(--c-muted); }
.np-head .material-icons { font-size: 16px; vertical-align: -3px; }
.np-row { padding: 14px 0; border-bottom: 1px solid var(--c-border); }
.np-col { display: flex; justify-content: center; align-items: center; gap: 4px; }
.np-label { font-weight: 700; font-size: 14px; color: var(--c-text); }
.np-desc { font-size: 12.5px; color: var(--c-muted); margin-top: 2px; }
.np-na { color: var(--c-muted); }
.np-foot { display: flex; justify-content: flex-end; align-items: center; gap: 12px; padding-top: 14px; }
.np-saved { color: #16A34A; font-size: 13px; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; }
.np-saved .material-icons { font-size: 17px; }
.np-note { color: var(--c-muted); font-size: 12.5px; margin-top: 14px; }
.np-empty { padding: 40px; text-align: center; color: var(--c-muted); }
.np-error { color: #DC2626; }
@media (max-width: 600px) {
  .np-head, .np-row { grid-template-columns: minmax(0, 1fr) 64px 64px; }
  .np-head .np-col { font-size: 0; }
  .np-head .material-icons { font-size: 18px; }
}
</style>
