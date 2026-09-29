<template>
  <div class="rbar" :class="{ empty: !reactions.length, right: alignRight }" @click.stop>
    <button
      v-for="r in reactions"
      :key="r.emoji"
      type="button"
      class="rchip"
      :class="{ mine: r.mine }"
      :title="r.names.join(', ') + (r.mine ? ' (clique para retirar)' : '')"
      @click="toggle(r.emoji)"
    >
      <span class="remoji">{{ r.emoji }}</span>{{ r.count }}
    </button>
    <span class="radd-wrap">
      <button type="button" class="radd" title="Reagir" @click="open = !open">
        <span class="material-icons">add_reaction</span><span v-if="!reactions.length">Reagir</span>
      </button>
      <span v-if="open" class="rpicker" :class="{ right: alignRight }">
        <button v-for="e in REACTION_EMOJIS" :key="e" type="button" class="rpick" :class="{ mine: reactions.some(r => r.emoji === e && r.mine) }" @click="toggle(e); open = false">{{ e }}</button>
      </span>
    </span>
  </div>
</template>

<script setup lang="ts">
// Emoji reactions under a ticket reply or a chat message
import { notifyError } from '../utils/feedback'
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { REACTION_EMOJIS, toggleReaction, type ReactionSummary, type ReactionTarget } from '../api/reactions'

const props = defineProps<{ targetType: ReactionTarget; targetId: number; reactions: ReactionSummary[]; alignRight?: boolean }>()
const emit = defineEmits<{ (e: 'update', reactions: ReactionSummary[]): void }>()
const open = ref(false)

async function toggle(emoji: string) {
  try {
    emit('update', await toggleReaction(props.targetType, props.targetId, emoji))
  } catch (e) {
    notifyError(e, 'Não foi possível guardar a reação.')
  }
}

function closeOnOutside() { open.value = false }
onMounted(() => document.addEventListener('click', closeOnOutside))
onBeforeUnmount(() => document.removeEventListener('click', closeOnOutside))
</script>

<style scoped>
.rbar { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; margin-top: 6px; }
.rbar.right { justify-content: flex-end; }
.rchip { display: inline-flex; align-items: center; gap: 4px; height: 26px; padding: 0 8px; border-radius: 999px; border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-text); font-size: 12px; font-weight: 700; cursor: pointer; }
.rchip:hover { border-color: var(--c-primary); }
.rchip.mine { border-color: var(--c-primary); background: var(--c-primary-soft); color: var(--c-primary); }
.remoji { font-size: 14px; line-height: 1; }
.radd-wrap { position: relative; display: inline-flex; }
.radd { display: inline-flex; align-items: center; gap: 4px; height: 26px; padding: 0 8px 0 6px; border-radius: 999px; border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-muted); cursor: pointer; font-size: 12px; font-weight: 600; }
.radd .material-icons { font-size: 16px; }
.radd:hover { border-color: var(--c-primary); color: var(--c-primary); }
.rpicker { position: absolute; bottom: calc(100% + 6px); left: 0; z-index: 50; display: flex; gap: 2px; padding: 5px; border-radius: 14px; background: var(--c-surface); border: 1px solid var(--c-border); box-shadow: 0 10px 30px rgba(15, 23, 42, .18); }
.rpicker.right { left: auto; right: 0; }
.rpick { width: 34px; height: 34px; border: 0; border-radius: 10px; background: transparent; font-size: 19px; cursor: pointer; transition: transform .1s; }
.rpick:hover { background: var(--c-bg); transform: scale(1.15); }
.rpick.mine { background: var(--c-primary-soft); }
</style>
