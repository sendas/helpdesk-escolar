<template>
  <div class="hd-page">
    <div class="hd-row" style="margin-bottom:24px">
      <h1 style="font-size:22px">Sugestões</h1>
      <div class="hd-spacer"></div>
      <span style="font-size:13px;color:var(--c-muted);align-self:center">{{ suggestions.length }} sugestão{{ suggestions.length !== 1 ? 'ões' : '' }}</span>
    </div>

    <div v-if="loading" style="padding:48px;text-align:center;color:var(--c-muted)">A carregar...</div>

    <div v-else-if="!suggestions.length" class="hd-card" style="padding:48px;text-align:center;color:var(--c-muted)">
      <span class="material-icons" style="font-size:40px;display:block;margin-bottom:12px;opacity:.4">lightbulb</span>
      Ainda não foram enviadas sugestões.
    </div>

    <div v-else style="display:flex;flex-direction:column;gap:14px;max-width:760px">
      <div v-for="s in suggestions" :key="s.id" class="hd-card suggestion-card">
        <div class="suggestion-header">
          <div class="suggestion-avatar">{{ initials(s.author_name) }}</div>
          <div>
            <div style="font-weight:600;font-size:13px">{{ s.author_name }}</div>
            <div style="font-size:11px;color:var(--c-muted)">{{ formatDate(s.created_at) }}</div>
          </div>
          <div class="hd-spacer"></div>
          <span style="font-size:11px;color:var(--c-muted);font-weight:500">#{{ s.id }}</span>
        </div>
        <div class="suggestion-body">{{ s.text }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../../boot/axios'

interface Suggestion { id: number; text: string; created_at: string; author_name: string }

const suggestions = ref<Suggestion[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get<Suggestion[]>('/api/v1/suggestions')
    suggestions.value = data
  } finally {
    loading.value = false
  }
})

function initials(name: string) {
  return name.split(' ').filter(Boolean).slice(0, 2).map(n => n[0].toUpperCase()).join('')
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleString('pt-PT', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.suggestion-card {
  padding: 18px 20px;
}
.suggestion-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.suggestion-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3D52D5, #6B7FE3);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.suggestion-body {
  font-size: 14px;
  line-height: 1.65;
  color: var(--c-text);
  white-space: pre-wrap;
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 14px 16px;
}
</style>
