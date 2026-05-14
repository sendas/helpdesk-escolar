<template>
  <div class="hd-page suggestions-page">
    <h1 style="font-size:22px;margin-bottom:6px">Sugestões</h1>
    <p class="hd-hint" style="margin-bottom:28px">Partilhe ideias para melhorar o Helpdesk Escolar</p>

    <div class="hd-card" style="padding:28px;max-width:640px;margin-bottom:24px">
      <label class="hd-label" style="display:block;margin-bottom:8px">A sua sugestão</label>
      <textarea
        v-model="text"
        class="hd-input"
        style="width:100%;min-height:120px;resize:vertical;font-family:inherit"
        placeholder="Descreva a sua ideia ou sugestão de melhoria..."
        :disabled="loading"
        maxlength="2000"
      />
      <div style="display:flex;align-items:center;justify-content:space-between;margin-top:6px">
        <span style="font-size:11px;color:var(--c-muted)">{{ text.length }}/2000</span>
        <button
          class="hd-btn hd-btn-primary"
          :disabled="loading || !text.trim()"
          @click="submit"
        >
          <span class="material-icons" style="font-size:16px">send</span>
          {{ loading ? 'A enviar...' : 'Enviar sugestão' }}
        </button>
      </div>
      <div v-if="error" style="margin-top:12px;color:#EF4444;font-size:13px">{{ error }}</div>
    </div>

    <div v-if="sent" class="hd-card" style="padding:24px;max-width:640px;background:var(--c-bg-alt,rgba(61,82,213,.06));border:1px solid var(--c-primary-light,#c7d0f8)">
      <div style="display:flex;align-items:center;gap:10px">
        <span class="material-icons" style="color:#22C55E;font-size:22px">check_circle</span>
        <div>
          <div style="font-weight:600;font-size:14px">Sugestão enviada</div>
          <div style="font-size:13px;color:var(--c-muted);margin-top:2px">Obrigado pelo seu contributo! A sua sugestão foi registada e será analisada.</div>
        </div>
      </div>
    </div>

    <div style="max-width:640px;margin-top:16px;padding:16px 20px;border-left:3px solid var(--c-border);border-radius:0 8px 8px 0;background:var(--c-surface)">
      <div style="font-size:13px;color:var(--c-muted);line-height:1.6">
        As sugestões são anónimas para outros utilizadores mas o administrador do sistema pode ver quem as enviou.
        Utilize este espaço para propor novas funcionalidades, melhorias de usabilidade ou reportar problemas que não sejam urgentes.
        Para pedidos de suporte técnico, utilize antes o botão <strong>Novo ticket</strong>.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../boot/axios'

const text = ref('')
const loading = ref(false)
const error = ref('')
const sent = ref(false)

async function submit() {
  if (!text.value.trim()) return
  loading.value = true
  error.value = ''
  sent.value = false
  try {
    await api.post('/api/v1/suggestions', { text: text.value.trim() })
    sent.value = true
    text.value = ''
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Erro ao enviar a sugestão. Tente novamente.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.suggestions-page {
  padding-bottom: 40px;
}
</style>
