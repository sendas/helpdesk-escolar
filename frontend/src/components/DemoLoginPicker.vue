<template>
  <div class="demo-picker">
    <button v-if="!open" class="demo-open-btn" type="button" @click="open = true">
      <span class="material-icons">visibility</span>
      Entrar em modo demo
    </button>
    <div v-else class="demo-box">
      <p class="demo-title">Escolha o perfil de demonstração</p>
      <div v-if="options.length > 1" class="demo-roles">
        <button
          v-for="p in options" :key="p.role"
          type="button"
          :class="{ selected: role === p.role }"
          @click="role = p.role"
        >{{ p.label }}</button>
      </div>
      <div v-if="error" class="demo-error">{{ error }}</div>
      <button class="demo-open-btn" type="button" :disabled="loading" @click="enter">
        {{ loading ? 'A entrar...' : `Entrar como ${selectedLabel}` }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'

const props = defineProps<{ profiles: string[] }>()

const LABELS: Record<string, string> = { teacher: 'Docente', technician: 'Técnico', admin: 'Administrador' }

const auth = useAuthStore()
const open = ref(false)
const loading = ref(false)
const error = ref('')
const options = computed(() => Object.keys(LABELS).filter(r => props.profiles.includes(r)).map(r => ({ role: r, label: LABELS[r] })))
const role = ref(options.value[0]?.role ?? 'teacher')
const selectedLabel = computed(() => LABELS[role.value] ?? 'demo')

watch(options, (opts) => {
  if (!opts.some(o => o.role === role.value)) role.value = opts[0]?.role ?? 'teacher'
})

async function enter() {
  loading.value = true
  error.value = ''
  try {
    await auth.loginDemo(role.value)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Não foi possível entrar em modo demo.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.demo-picker { margin-top: 12px; }

.demo-open-btn {
  width: 100%;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  padding: 9px 14px;
  border: 1px dashed var(--c-border);
  border-radius: 12px;
  background: transparent;
  color: var(--c-text);
  font: 600 13px var(--font-sans);
  cursor: pointer;
}
.demo-open-btn:hover { background: var(--c-surface-soft, rgba(0, 0, 0, .03)); }
.demo-open-btn:disabled { opacity: .6; cursor: not-allowed; }
.demo-open-btn .material-icons { font-size: 17px; color: var(--c-muted); }

.demo-box {
  padding: 14px;
  border: 1px solid var(--c-border);
  border-radius: 12px;
  background: var(--c-surface);
}
.demo-title { font-size: 12px; color: var(--c-muted); text-align: center; margin: 0 0 10px; }

.demo-roles {
  display: flex;
  overflow: hidden;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  margin-bottom: 10px;
}
.demo-roles button {
  flex: 1;
  padding: 7px 0;
  border: 0;
  background: transparent;
  color: var(--c-muted);
  font: 600 12.5px var(--font-sans);
  cursor: pointer;
}
.demo-roles button.selected { background: var(--c-text); color: var(--c-surface); }

.demo-error {
  background: #FEF2F2; border: 1px solid #FECACA; border-radius: 8px;
  padding: 8px 12px; font-size: 12.5px; color: #DC2626; margin-bottom: 10px;
}
</style>
