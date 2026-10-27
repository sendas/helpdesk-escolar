<template>
  <span class="person-name" :title="name || ''">{{ short }}</span>
</template>

<script setup lang="ts">
// A person is always shown by the short form of their name ("Pedro Pereira", "M. Carmo Fortunato" — see
// utils/names.ts); the full directory name ("… Docente-520 - Biologia e Geologia") is in the tooltip.
import { computed } from 'vue'
import { shortName } from '../utils/names'

// withTag is accepted for compatibility with older callers; the group ("520 BG") is no longer shown next to names
const props = withDefaults(defineProps<{ name?: string | null; withTag?: boolean }>(), { name: '', withTag: false })
const short = computed(() => shortName(props.name))
</script>

<style scoped>
.person-name { display: inline-block; max-width: 100%; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; }
</style>
