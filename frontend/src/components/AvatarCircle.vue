<template>
  <div
    class="hd-avatar"
    :class="sizeClass"
    :style="{ background: color, width: size + 'px', height: size + 'px', fontSize: (Number(size) * 0.38) + 'px' }"
  >{{ initials }}</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ name: string; size?: string | number }>()

const palette = ['#3D52D5','#7C3AED','#0D9488','#D97706','#DC2626','#16A34A','#DB2777','#2563EB','#9333EA']

const initials = computed(() => {
  const parts = (props.name || '?').trim().split(' ')
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase()
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
})

const color = computed(() => {
  let h = 0
  for (const c of props.name || '') h = (h * 31 + c.charCodeAt(0)) % palette.length
  return palette[h]
})

const sizeClass = computed(() => props.size && Number(props.size) >= 36 ? 'hd-avatar-lg' : '')
</script>
