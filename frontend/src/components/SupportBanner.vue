<template>
  <div v-if="visible" class="sb" :class="[status!.open_now ? 'open' : 'closed', { compact }]">
    <div class="sb-icon">
      <span class="material-icons">support_agent</span>
      <i v-if="status!.open_now" class="sb-dot"></i>
    </div>
    <div class="sb-text">
      <template v-if="compact">
        <strong>{{ status!.open_now ? 'Prefere resolver já?' : 'Apoio ao vivo' }}</strong>
        <span>{{ status!.open_now ? `Fale com um técnico em tempo real (${when}).` : `Fechado de momento — ${when}.` }}</span>
      </template>
      <template v-else>
        <strong>{{ status!.open_now ? 'Apoio ao vivo disponível agora' : 'Apoio ao vivo' }}</strong>
        <span v-if="status!.open_now">Fale com a equipa TIC em tempo real, {{ when }}. Para problemas rápidos é mais simples do que abrir um ticket.</span>
        <span v-else>O chat com a equipa TIC {{ when }}. Pode deixar já a mensagem: criamos um ticket e respondemos por lá.</span>
      </template>
    </div>
    <button class="sb-btn" @click="openSupportChat()">
      <span class="material-icons">forum</span>
      {{ status!.open_now ? 'Falar agora' : 'Deixar mensagem' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { loadSupportStatus, openSupportChat, supportStatus, supportWhen } from '../utils/supportChat'

const props = defineProps<{ compact?: boolean; onlyWhenOpen?: boolean }>()
const auth = useAuthStore()
const status = supportStatus
const when = computed(() => supportWhen(status.value))
// Shown to the people who use the bubble (not to those who answer it)
const visible = computed(() => !!status.value?.enabled && !auth.can('chat.support') && !auth.isDemo
  && (!props.onlyWhenOpen || status.value.open_now))

onMounted(() => { loadSupportStatus() })
</script>

<style scoped>
.sb { display: flex; align-items: center; gap: 14px; padding: 14px 16px; border-radius: 16px; margin-bottom: 18px; border: 1px solid; }
.sb.open { background: linear-gradient(135deg, rgba(37, 99, 235, .08), rgba(8, 145, 178, .10)); border-color: rgba(8, 145, 178, .35); }
.sb.closed { background: var(--c-surface); border-color: var(--c-border); }
.sb-icon { position: relative; width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center; color: #fff; flex-shrink: 0; background: linear-gradient(135deg, #2563EB, #0891B2); }
.sb.closed .sb-icon { background: linear-gradient(135deg, #64748B, #94A3B8); }
.sb-icon .material-icons { font-size: 24px; }
.sb-dot { position: absolute; top: -3px; right: -3px; width: 12px; height: 12px; border-radius: 50%; background: #22C55E; border: 2px solid var(--c-surface); animation: sb-pulse 2s infinite; }
@keyframes sb-pulse { 0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, .5); } 70% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); } 100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); } }
.sb-text { flex: 1; min-width: 0; }
.sb-text strong { display: block; font-size: 14.5px; }
.sb-text span { display: block; font-size: 13px; color: var(--c-muted); margin-top: 2px; line-height: 1.4; }
.sb-btn { display: inline-flex; align-items: center; gap: 6px; border: 0; border-radius: 12px; padding: 10px 16px; font-weight: 700; font-size: 13.5px; cursor: pointer; color: #fff; background: var(--c-primary); white-space: nowrap; }
.sb.closed .sb-btn { background: var(--c-surface); color: var(--c-primary); border: 1px solid var(--c-border); }
.sb-btn .material-icons { font-size: 18px; }
.sb.compact { padding: 10px 12px; border-radius: 12px; }
.sb.compact .sb-icon { width: 36px; height: 36px; border-radius: 11px; }
.sb.compact .sb-icon .material-icons { font-size: 20px; }
@media (max-width: 600px) { .sb { flex-wrap: wrap; } .sb-btn { width: 100%; justify-content: center; } }
</style>
