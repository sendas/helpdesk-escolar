<template>
  <span class="person-name" :title="name || ''">{{ short }}<span v-if="withTag && tag" class="pn-tag" :title="tagTitle">{{ tag }}</span></span>
</template>

<script setup lang="ts">
// A person is shown by the short form of their name ("Pedro Pereira", "M. Carmo Fortunato" — see utils/names.ts)
// and, for teachers, their recruitment group ("550 INF", "910 EE"); the full directory name is in the tooltip.
import { computed } from 'vue'
import { groupTag, shortName } from '../utils/names'

const props = withDefaults(defineProps<{ name?: string | null; withTag?: boolean }>(), { name: '', withTag: true })
const short = computed(() => shortName(props.name))
const tag = computed(() => groupTag(props.name))
const tagTitle = computed(() => (props.name ?? '').match(/\d{3}\s*-\s*(.+)$/)?.[1]?.trim() || 'Grupo de recrutamento')
</script>

<style scoped>
.person-name { display: inline-block; max-width: 100%; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; }
.pn-tag {
  display: inline-block; margin-left: 6px; font-size: 10.5px; font-weight: 700; color: var(--c-muted);
  border: 1px solid var(--c-border); border-radius: 6px; padding: 0 6px; line-height: 17px; vertical-align: 1px;
}
</style>
