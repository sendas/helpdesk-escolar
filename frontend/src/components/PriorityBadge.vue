<template>
  <div class="hd-priority" :class="priority">
    <div class="hd-priority-bar"></div>
    {{ label }}
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ priority: string }>()
const label = computed(() => ({ low: 'Baixa', medium: 'Média', high: 'Alta', urgent: 'Urgente' }[props.priority] ?? props.priority))
</script>
