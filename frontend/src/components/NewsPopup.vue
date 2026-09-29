<template>
  <div class="news-backdrop" role="dialog" aria-modal="true" :aria-label="title" @click.self="emit('close')" @keydown.esc="emit('close')">
    <div class="news-card" tabindex="-1" ref="card">
      <div class="news-head">
        <div class="news-spark"><span class="material-icons">auto_awesome</span></div>
        <div class="news-title">{{ title }}</div>
        <div class="news-sub">O que há de novo para si</div>
      </div>
      <div class="news-list">
        <div v-for="(it, i) in items" :key="i" class="news-item">
          <div class="news-icon"><span class="material-icons">{{ it.icon || 'new_releases' }}</span></div>
          <div>
            <div class="news-item-title">{{ it.title }}</div>
            <div v-if="it.text" class="news-item-text">{{ it.text }}</div>
          </div>
        </div>
      </div>
      <div class="news-foot">
        <button type="button" class="hd-btn hd-btn-primary" @click="emit('close')">Entendi</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// "Novidades" popup (Configurações → Novidades), shown once to each person
import { onMounted, ref } from 'vue'

defineProps<{ title: string; items: { icon: string; title: string; text: string }[] }>()
const emit = defineEmits<{ (e: 'close'): void }>()
const card = ref<HTMLElement | null>(null)
onMounted(() => card.value?.focus())
</script>

<style scoped>
.news-backdrop { position: fixed; inset: 0; z-index: 2000; background: rgba(15, 23, 42, .5); display: flex; align-items: center; justify-content: center; padding: 16px; }
.news-card { width: min(520px, 100%); max-height: calc(100vh - 32px); overflow-y: auto; background: var(--c-surface); border-radius: 20px; box-shadow: 0 24px 60px rgba(15, 23, 42, .35); outline: none; }
.news-head { text-align: center; padding: 26px 24px 18px; background: linear-gradient(135deg, color-mix(in srgb, var(--c-primary) 16%, var(--c-surface)), var(--c-surface)); border-radius: 20px 20px 0 0; }
.news-spark { width: 52px; height: 52px; margin: 0 auto 10px; border-radius: 16px; display: flex; align-items: center; justify-content: center; background: var(--c-primary); color: #fff; box-shadow: 0 8px 20px color-mix(in srgb, var(--c-primary) 40%, transparent); }
.news-spark .material-icons { font-size: 28px; }
.news-title { font-size: 20px; font-weight: 800; color: var(--c-text); }
.news-sub { font-size: 13px; color: var(--c-muted); margin-top: 2px; }
.news-list { padding: 8px 24px; display: flex; flex-direction: column; gap: 14px; }
.news-item { display: flex; gap: 14px; align-items: flex-start; }
.news-icon { width: 38px; height: 38px; flex-shrink: 0; border-radius: 12px; display: flex; align-items: center; justify-content: center; background: var(--c-primary-soft); color: var(--c-primary); }
.news-icon .material-icons { font-size: 21px; }
.news-item-title { font-weight: 700; font-size: 14.5px; color: var(--c-text); }
.news-item-text { font-size: 13px; color: var(--c-muted); margin-top: 2px; line-height: 1.45; }
.news-foot { display: flex; justify-content: flex-end; padding: 16px 24px 22px; }
</style>
