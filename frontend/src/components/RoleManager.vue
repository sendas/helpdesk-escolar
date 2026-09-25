<template>
  <div>
    <div class="rm-head">
      <div>
        <div style="font-weight:600;font-size:15px;margin-bottom:4px">Mapeamento de papéis</div>
        <div style="font-size:13px;color:var(--c-muted)">
          Cada papel dá um conjunto de permissões. Todos podem criar e acompanhar os seus próprios pedidos.
          <template v-if="!canEdit"> Só quem tem a permissão "Gerir utilizadores e papéis" pode alterar os papéis.</template>
        </div>
      </div>
      <button v-if="canEdit" class="hd-btn hd-btn-primary" @click="startCreate">
        <span class="material-icons" style="font-size:16px">add</span> Novo papel
      </button>
    </div>

    <div v-if="error" class="rm-error">{{ error }}</div>

    <div class="role-grid">
      <div v-if="creating" class="role-card editing">
        <RoleForm v-model="draft" :catalog="catalog" @save="saveCreate" @cancel="creating = false" :saving="saving" save-label="Criar papel" />
      </div>

      <div v-for="role in roles" :key="role.key" class="role-card" :class="{ editing: editingKey === role.key }">
        <RoleForm
          v-if="editingKey === role.key"
          v-model="draft"
          :catalog="catalog"
          :locked-perms="role.key === 'technician' ? ['tickets.manage'] : []"
          :saving="saving"
          save-label="Guardar"
          @save="saveEdit(role)"
          @cancel="editingKey = ''"
        />
        <template v-else>
          <div class="rm-card-head">
            <span class="rm-icon" :style="{ background: role.color + '1f', color: role.color }">
              <span class="material-icons">{{ role.icon }}</span>
            </span>
            <div class="rm-title">
              <div>{{ role.label }}</div>
              <small>{{ role.user_count }} utilizador{{ role.user_count === 1 ? '' : 'es' }}</small>
            </div>
            <template v-if="canEdit && !role.locked">
              <button class="hd-icon-btn" title="Editar papel" @click="startEdit(role)"><span class="material-icons" style="font-size:17px">edit</span></button>
              <button v-if="!role.builtin" class="hd-icon-btn" title="Apagar papel" @click="remove(role)"><span class="material-icons" style="font-size:17px;color:#DC2626">delete</span></button>
            </template>
            <span v-else-if="role.locked" class="rm-lock" title="O administrador tem sempre todas as permissões"><span class="material-icons">lock</span></span>
          </div>
          <div class="role-perm base"><span class="material-icons">check_circle</span>Criar e acompanhar os próprios pedidos</div>
          <div v-for="perm in catalog" :key="perm.key" class="role-perm" :class="{ off: !role.permissions.includes(perm.key) }" :title="perm.hint">
            <span class="material-icons">{{ role.permissions.includes(perm.key) ? 'check_circle' : 'remove_circle_outline' }}</span>{{ perm.label }}
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineComponent, h, onMounted, ref, type PropType } from 'vue'
import { createRole, deleteRole, getPermissionCatalog, getRoles, updateRole, type Permission, type Role } from '../api/roles'

defineProps<{ canEdit: boolean }>()
const emit = defineEmits<{ (e: 'changed', roles: Role[]): void }>()

const roles = ref<Role[]>([])
const catalog = ref<Permission[]>([])
const editingKey = ref('')
const creating = ref(false)
const saving = ref(false)
const error = ref('')
const draft = ref({ label: '', icon: 'badge', color: '#64748B', permissions: [] as string[] })

const ICONS = ['badge', 'school', 'account_balance', 'computer', 'build', 'support_agent', 'groups', 'business_center', 'supervisor_account', 'visibility', 'menu_book', 'engineering']
const COLORS = ['#3D52D5', '#0891B2', '#0D9488', '#16A34A', '#F59E0B', '#EA580C', '#DC2626', '#7C3AED', '#64748B']

const RoleForm = defineComponent({
  props: {
    modelValue: { type: Object as PropType<{ label: string; icon: string; color: string; permissions: string[] }>, required: true },
    catalog: { type: Array as PropType<Permission[]>, required: true },
    lockedPerms: { type: Array as PropType<string[]>, default: () => [] },
    saving: Boolean,
    saveLabel: { type: String, default: 'Guardar' },
  },
  emits: ['update:modelValue', 'save', 'cancel'],
  setup(props, { emit: emitForm }) {
    const set = (patch: object) => emitForm('update:modelValue', { ...props.modelValue, ...patch })
    const toggle = (key: string) => {
      if (props.lockedPerms.includes(key)) return
      const perms = props.modelValue.permissions.includes(key)
        ? props.modelValue.permissions.filter((p) => p !== key)
        : [...props.modelValue.permissions, key]
      set({ permissions: perms })
    }
    return () => h('div', { class: 'rm-form' }, [
      h('input', { class: 'hd-input', placeholder: 'Nome do papel (ex.: Direção)', value: props.modelValue.label,
        onInput: (e: Event) => set({ label: (e.target as HTMLInputElement).value }) }),
      h('div', { class: 'rm-swatches' }, [
        ...ICONS.map((icon) => h('button', { type: 'button', class: ['rm-swatch', { on: props.modelValue.icon === icon }], title: icon, onClick: () => set({ icon }) },
          [h('span', { class: 'material-icons' }, icon)])),
      ]),
      h('div', { class: 'rm-swatches' }, COLORS.map((color) => h('button', { type: 'button', class: ['rm-color', { on: props.modelValue.color === color }], style: { background: color }, title: color, onClick: () => set({ color }) }))),
      h('div', { class: 'rm-perms' }, props.catalog.map((perm) => {
        const on = props.modelValue.permissions.includes(perm.key) || props.lockedPerms.includes(perm.key)
        return h('label', { class: ['rm-perm', { on, locked: props.lockedPerms.includes(perm.key) }], onClick: (e: Event) => { e.preventDefault(); toggle(perm.key) } }, [
          h('span', { class: 'hd-toggle-wrap' }, [h('span', { class: ['hd-toggle-track', { on }] }, [h('span', { class: 'hd-toggle-thumb' })])]),
          h('span', null, [h('strong', null, perm.label), h('small', null, props.lockedPerms.includes(perm.key) ? 'Sempre ativo para este papel.' : perm.hint)]),
        ])
      })),
      h('div', { class: 'rm-actions' }, [
        h('button', { type: 'button', class: 'hd-btn hd-btn-outline', onClick: () => emitForm('cancel') }, 'Cancelar'),
        h('button', { type: 'button', class: 'hd-btn hd-btn-primary', disabled: props.saving || !props.modelValue.label.trim(), onClick: () => emitForm('save') },
          props.saving ? 'A guardar...' : props.saveLabel),
      ]),
    ])
  },
})

async function load() {
  const [r, c] = await Promise.all([getRoles(), getPermissionCatalog()])
  roles.value = r
  catalog.value = c
  emit('changed', r)
}

function startCreate() {
  editingKey.value = ''
  error.value = ''
  draft.value = { label: '', icon: 'badge', color: '#0891B2', permissions: [] }
  creating.value = true
}

function startEdit(role: Role) {
  creating.value = false
  error.value = ''
  draft.value = { label: role.label, icon: role.icon, color: role.color, permissions: [...role.permissions] }
  editingKey.value = role.key
}

async function run(action: () => Promise<unknown>) {
  saving.value = true
  error.value = ''
  try {
    await action()
    await load()
    return true
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Não foi possível guardar o papel.'
    return false
  } finally {
    saving.value = false
  }
}

async function saveCreate() {
  if (await run(() => createRole(draft.value))) creating.value = false
}

async function saveEdit(role: Role) {
  if (await run(() => updateRole(role.key, draft.value))) editingKey.value = ''
}

async function remove(role: Role) {
  if (!confirm(`Apagar o papel "${role.label}"?`)) return
  await run(() => deleteRole(role.key))
}

onMounted(load)
defineExpose({ reload: load })
</script>

<style scoped>
.rm-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
.rm-error { color: #DC2626; font-size: 13px; margin-bottom: 12px; }
.role-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }
.role-card { border: 1px solid var(--c-border); border-radius: 12px; padding: 16px; background: var(--c-surface); }
.role-card.editing { border-color: var(--c-primary); box-shadow: 0 0 0 3px var(--c-primary-soft); grid-column: span 2; }
@media (max-width: 700px) { .role-card.editing { grid-column: auto; } }
.rm-card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.rm-icon { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; flex-shrink: 0; }
.rm-icon .material-icons { font-size: 19px; }
.rm-title { flex: 1; min-width: 0; font-weight: 700; font-size: 14px; }
.rm-title small { display: block; font-weight: 500; font-size: 12px; color: var(--c-muted); }
.rm-lock .material-icons { font-size: 17px; color: var(--c-muted); }
.role-perm { display: flex; gap: 6px; font-size: 13px; color: var(--c-text); margin-top: 6px; line-height: 1.35; }
.role-perm .material-icons { font-size: 15px; color: #22C55E; flex-shrink: 0; margin-top: 1px; }
.role-perm.off { color: var(--c-muted); opacity: .6; }
.role-perm.off .material-icons { color: var(--c-muted); }
.role-perm.base { color: var(--c-muted); }
:deep(.rm-form) { display: flex; flex-direction: column; gap: 12px; }
:deep(.rm-swatches) { display: flex; flex-wrap: wrap; gap: 6px; }
:deep(.rm-swatch) { width: 34px; height: 34px; border-radius: 9px; border: 1px solid var(--c-border); background: var(--c-surface); color: var(--c-muted); cursor: pointer; display: grid; place-items: center; }
:deep(.rm-swatch .material-icons) { font-size: 18px; }
:deep(.rm-swatch.on) { border-color: var(--c-primary); color: var(--c-primary); background: var(--c-primary-soft); }
:deep(.rm-color) { width: 24px; height: 24px; border-radius: 50%; border: 2px solid transparent; cursor: pointer; }
:deep(.rm-color.on) { outline: 2px solid var(--c-text); outline-offset: 2px; }
:deep(.rm-perms) { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 8px; }
:deep(.rm-perm) { display: flex; gap: 10px; align-items: flex-start; padding: 10px; border: 1px solid var(--c-border); border-radius: 10px; cursor: pointer; }
:deep(.rm-perm.on) { border-color: var(--c-primary); background: var(--c-primary-soft); }
:deep(.rm-perm.locked) { cursor: default; opacity: .85; }
:deep(.rm-perm strong) { display: block; font-size: 13px; }
:deep(.rm-perm small) { display: block; font-size: 12px; color: var(--c-muted); margin-top: 2px; }
:deep(.rm-perm .hd-toggle-wrap) { margin-top: 1px; }
:deep(.rm-actions) { display: flex; justify-content: flex-end; gap: 8px; }
</style>
