<template>
  <div class="cat-filter" ref="root">
    <button type="button" class="cat-filter-btn" :class="{ active: hiddenCount > 0 }" @click="open = !open">
      <span class="material-icons">tune</span>
      Categorias
      <span v-if="hiddenCount" class="cat-filter-badge">{{ hiddenCount }} oculta{{ hiddenCount !== 1 ? 's' : '' }}</span>
    </button>
    <div v-if="open" class="cat-filter-panel">
      <div class="cat-filter-title">Categorias que quero ver</div>
      <label v-for="c in categories" :key="c.id" class="cat-filter-opt">
        <input type="checkbox" :checked="!draft.includes(c.id)" @change="toggle(c.id)" />
        <span class="cat-filter-dot" :style="{ background: c.color }"></span>
        {{ c.name }}
      </label>
      <p v-if="error" class="cat-filter-error">{{ error }}</p>
      <div class="cat-filter-actions">
        <button type="button" class="hd-btn hd-btn-outline hd-btn-sm" @click="draft = []">Mostrar todas</button>
        <button type="button" class="hd-btn hd-btn-primary hd-btn-sm" :disabled="saving" @click="save">
          {{ saving ? 'A guardar...' : 'Guardar' }}
        </button>
      </div>
      <p class="cat-filter-hint">Aplica-se ao Painel inicial e a "Os meus tickets".</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import { updateMyPreferences } from '../api/users'

defineProps<{ categories: { id: number; name: string; color: string }[] }>()
const emit = defineEmits<{ (e: 'changed', hidden: number[]): void }>()

const auth = useAuthStore()
const open = ref(false)
const saving = ref(false)
const error = ref('')
const root = ref<HTMLElement | null>(null)
const draft = ref<number[]>([])

const hiddenCount = computed(() => auth.user?.hidden_category_ids?.length ?? 0)

watch(open, (v) => { if (v) { draft.value = [...(auth.user?.hidden_category_ids ?? [])]; error.value = '' } })

function toggle(id: number) {
  draft.value = draft.value.includes(id) ? draft.value.filter(x => x !== id) : [...draft.value, id]
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const u = await updateMyPreferences(draft.value)
    if (auth.user) auth.user.hidden_category_ids = u.hidden_category_ids ?? []
    emit('changed', auth.user?.hidden_category_ids ?? [])
    open.value = false
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Não foi possível guardar.'
  } finally {
    saving.value = false
  }
}

function onDocClick(e: MouseEvent) {
  if (open.value && root.value && !root.value.contains(e.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.cat-filter { position: relative; display: inline-block; }
.cat-filter-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 12px;
  border: 1px solid var(--c-border); border-radius: 10px;
  background: var(--c-surface); color: var(--c-text);
  font: 600 13px var(--font-sans); cursor: pointer;
}
.cat-filter-btn .material-icons { font-size: 16px; color: var(--c-muted); }
.cat-filter-btn.active { border-color: var(--c-primary); color: var(--c-primary); }
.cat-filter-btn.active .material-icons { color: var(--c-primary); }
.cat-filter-badge {
  font-size: 11px; font-weight: 700;
  padding: 1px 7px; border-radius: 999px;
  background: var(--c-primary-soft); color: var(--c-primary);
}
.cat-filter-panel {
  position: absolute; right: 0; top: calc(100% + 6px); z-index: 60;
  width: 270px; padding: 14px;
  border: 1px solid var(--c-border); border-radius: 12px;
  background: var(--c-surface);
  box-shadow: 0 16px 36px rgba(15, 23, 42, .16);
}
.cat-filter-title { font-size: 12px; font-weight: 700; color: var(--c-muted); margin-bottom: 8px; }
.cat-filter-opt { display: flex; align-items: center; gap: 8px; padding: 5px 0; font-size: 13px; cursor: pointer; color: var(--c-text); }
.cat-filter-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.cat-filter-actions { display: flex; justify-content: space-between; gap: 8px; margin-top: 12px; }
.cat-filter-hint { font-size: 11px; color: var(--c-muted); margin: 10px 0 0; }
.cat-filter-error { font-size: 12px; color: #EF4444; margin: 8px 0 0; }
</style>
