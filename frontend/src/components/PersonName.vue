<template>
  <span ref="el" class="person-name" :class="{ compact }" :title="name || ''">
    <template v-if="!compact">{{ name }}</template>
    <template v-else>{{ short }}<span v-if="withTag && tag" class="pn-tag">{{ tag }}</span></template>
  </span>
</template>

<script setup lang="ts">
// Shows the full directory name ("Maria Leonor Marinho Nunes Serra Docente-510 - Física e Química") when it fits
// in the available space, and the short form ("Maria Serra" + "510 FQ") only when it does not.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { groupTag, shortName } from '../utils/names'

const props = withDefaults(defineProps<{ name?: string | null; withTag?: boolean }>(), { name: '', withTag: true })
const el = ref<HTMLElement | null>(null)
const compact = ref(false)
const short = computed(() => shortName(props.name))
const tag = computed(() => groupTag(props.name))
let observer: ResizeObserver | null = null
let frame = 0
let lastWidth = -1

async function measure() {
  const node = el.value
  if (!node) return
  // Nothing to shorten
  if (short.value === (props.name ?? '').trim()) { compact.value = false; return }
  compact.value = false
  await nextTick()
  compact.value = node.scrollWidth > node.clientWidth + 1
}

function schedule() {
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(() => {
    const width = el.value?.parentElement?.clientWidth ?? 0
    if (width === lastWidth) return
    lastWidth = width
    measure()
  })
}

onMounted(() => {
  measure()
  const parent = el.value?.parentElement
  if (parent && 'ResizeObserver' in window) {
    observer = new ResizeObserver(schedule)
    observer.observe(parent)
  }
})
onBeforeUnmount(() => { observer?.disconnect(); cancelAnimationFrame(frame) })
watch(() => props.name, () => { lastWidth = -1; measure() })
</script>

<style scoped>
.person-name { display: inline-block; max-width: 100%; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; }
.pn-tag {
  display: inline-block; margin-left: 6px; font-size: 10.5px; font-weight: 700; color: var(--c-muted);
  border: 1px solid var(--c-border); border-radius: 6px; padding: 0 6px; line-height: 17px; vertical-align: 1px;
}
</style>
