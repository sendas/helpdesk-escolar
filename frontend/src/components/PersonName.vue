<template>
  <span class="person-name" :title="name || ''">{{ short }}<span v-if="withTag && tag" class="pn-tag" :title="tagTitle">{{ tag }}</span></span>
</template>

<script setup lang="ts">
// A person is shown by the short form of their name ("Pedro Pereira", "M. Carmo Fortunato" — see utils/names.ts)
// and a small tag: the recruitment group for teachers ("550 INF", "910 EE"), or, for people without one, their
// function when it is not plain "docente" ("Técnico", "Administrador", "Direção"…). Full name in the tooltip.
import { computed } from 'vue'
import { groupTag, shortName } from '../utils/names'

const props = withDefaults(defineProps<{
  name?: string | null
  withTag?: boolean
  // The user record, when the caller has it: gives the function for people without a recruitment group
  user?: { role?: string; role_label?: string; effective_role_key?: string; is_technician?: boolean } | null
}>(), { name: '', withTag: true, user: null })

const PLAIN_ROLES = new Set(['teacher', 'student', ''])
const short = computed(() => shortName(props.name))
const group = computed(() => groupTag(props.name))
const roleTag = computed(() => {
  const u = props.user
  if (!u?.role_label) return ''
  const key = u.effective_role_key ?? u.role ?? ''
  return PLAIN_ROLES.has(key) && !u.is_technician ? '' : u.role_label
})
const tag = computed(() => group.value || roleTag.value)
const tagTitle = computed(() => group.value
  ? (props.name ?? '').match(/\d{3}\s*-\s*(.+)$/)?.[1]?.trim() || 'Grupo de recrutamento'
  : 'Função no helpdesk')
</script>

<style scoped>
.person-name { display: inline-block; max-width: 100%; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; }
.pn-tag {
  display: inline-block; margin-left: 6px; font-size: 10.5px; font-weight: 700; color: var(--c-muted);
  border: 1px solid var(--c-border); border-radius: 6px; padding: 0 6px; line-height: 17px; vertical-align: 1px;
}
</style>
