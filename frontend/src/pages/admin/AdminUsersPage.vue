<template>
  <div class="hd-page admin-users-page">
    <div class="admin-users-head">
      <div>
        <h1 style="font-size:22px;margin-bottom:6px">Utilizadores e permissões</h1>
        <div class="sync-note">
          <span class="material-icons">sync</span>
          Sincronização Entra ID
          <button class="sync-link" @click="syncEntra" :disabled="syncing">
            {{ syncing ? 'A sincronizar...' : 'Sincronizar agora' }}
          </button>
        </div>
      </div>
      <div class="admin-users-summary">
        <div><strong>{{ users.length }}</strong><span>utilizadores</span></div>
        <div><strong>{{ lockedCount }}</strong><span>papéis bloqueados</span></div>
      </div>
    </div>

    <div v-if="syncReport" class="sync-report">
      <div><strong>{{ syncReport.created }}</strong><span>criados</span></div>
      <div><strong>{{ syncReport.updated }}</strong><span>atualizados</span></div>
      <div><strong>{{ syncReport.role_changes }}</strong><span>papéis alterados</span></div>
      <div><strong>{{ syncReport.manual_locked }}</strong><span>mantidos manualmente</span></div>
      <div><strong>{{ syncReport.skipped }}</strong><span>ignorados</span></div>
      <div class="sync-report-muted">
        convidados {{ syncReport.skipped_guests }} · inativos {{ syncReport.skipped_disabled }} · fora das OUs {{ syncReport.skipped_outside_ou }} · sem email {{ syncReport.skipped_without_email }}
      </div>
    </div>
    <div v-if="syncMessage" class="sync-message">{{ syncMessage }}</div>

    <div class="hd-tabs" style="margin-bottom:20px">
      <button class="hd-tab" :class="{ active: tab === 'users' }" @click="tab = 'users'">
        <span class="material-icons" style="font-size:15px">people</span> Utilizadores
      </button>
      <button class="hd-tab" :class="{ active: tab === 'permissions' }" @click="tab = 'permissions'">
        <span class="material-icons" style="font-size:15px">shield</span> Permissões
      </button>
      <button class="hd-tab" :class="{ active: tab === 'departments' }" @click="tab = 'departments'">
        <span class="material-icons" style="font-size:15px">apartment</span> Departamentos
      </button>
    </div>

    <div v-if="tab === 'users'" class="hd-card users-card">
      <div class="users-toolbar">
        <input class="hd-input" placeholder="Pesquisar por nome, email ou utilizador..." v-model="search" />
        <select class="hd-select" v-model="filterRole">
          <option value="">Todos os papéis</option>
          <option v-for="role in roleOptions" :key="role.value" :value="role.value">{{ role.label }}</option>
        </select>
        <select class="hd-select" v-model="filterSource">
          <option value="">Todas as origens</option>
          <option value="manual">Manual</option>
          <option value="entra">Entra ID</option>
        </select>
        <select class="hd-select" v-model="filterActive">
          <option value="">Ativos e inativos</option>
          <option value="active">Só ativos</option>
          <option value="inactive">Só inativos</option>
        </select>
        <select class="hd-select" v-model="filterDepartment">
          <option value="">Todos os departamentos</option>
          <option v-for="dept in departments" :key="dept" :value="dept">{{ dept }}</option>
        </select>
      </div>

      <div v-if="selectedIds.length" class="bulk-bar">
        <span>{{ selectedIds.length }} selecionado{{ selectedIds.length !== 1 ? 's' : '' }}</span>
        <select class="hd-select" v-model="bulkRole">
          <option value="">Alterar papel...</option>
          <option v-for="role in roleOptions" :key="role.value" :value="role.value">{{ role.label }}</option>
        </select>
        <button class="hd-btn hd-btn-outline" @click="applyBulkRole" :disabled="!bulkRole">Aplicar papel</button>
        <button class="hd-btn hd-btn-outline" @click="applyBulkActive(true)">Ativar</button>
        <button class="hd-btn hd-btn-outline" @click="applyBulkActive(false)">Desativar</button>
        <button class="hd-btn hd-btn-outline" @click="applyBulkLock(true)">Bloquear papel</button>
        <button class="hd-btn hd-btn-outline" @click="applyBulkLock(false)">Libertar papel</button>
      </div>

      <div class="users-count">{{ filteredUsers.length }} utilizador{{ filteredUsers.length !== 1 ? 'es' : '' }}</div>

      <div v-if="loading" style="padding:48px;text-align:center;color:var(--c-muted)">A carregar...</div>
      <template v-else>
        <table class="hd-table users-table">
          <thead>
            <tr>
              <th><input type="checkbox" :checked="allVisibleSelected" @change="toggleAllVisible" /></th>
              <th>UTILIZADOR</th>
              <th>EMAIL</th>
              <th>PAPEL</th>
              <th>ORIGEM</th>
              <th>DEPARTAMENTO / OU</th>
              <th>ATIVO</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="u in filteredUsers" :key="u.id">
              <td><input type="checkbox" :checked="selectedIds.includes(u.id)" @change="toggleSelected(u.id)" /></td>
              <td>
                <div class="hd-row" style="gap:8px">
                  <AvatarCircle :name="u.display_name" size="28" />
                  <div>
                    <div style="font-weight:500;font-size:13px">{{ u.display_name }}</div>
                    <div style="font-size:11px;color:var(--c-muted)">@{{ u.username }}</div>
                  </div>
                </div>
              </td>
              <td style="font-size:13px;color:var(--c-muted)">{{ u.email }}</td>
              <td>
                <select class="hd-select compact" :value="u.role" @change="changeRole(u, ($event.target as HTMLSelectElement).value)">
                  <option v-for="role in roleOptions" :key="role.value" :value="role.value">{{ role.label }}</option>
                </select>
              </td>
              <td>
                <button class="role-source" :class="{ locked: u.role_locked }" @click="toggleRoleLock(u)">
                  <span class="material-icons">{{ u.role_locked ? 'lock' : 'sync' }}</span>
                  {{ u.role_locked ? 'Manual' : 'Entra ID' }}
                </button>
              </td>
              <td>
                <div style="font-size:13px">{{ u.department || '—' }}</div>
                <div style="font-size:11px;color:var(--c-muted);max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                  {{ u.onprem_path || 'Sem OU local' }}
                </div>
              </td>
              <td>
                <div class="hd-toggle-wrap" @click="toggleActive(u)" :title="u.is_active ? 'Desativar' : 'Ativar'">
                  <div class="hd-toggle" :class="{ active: u.is_active }"></div>
                </div>
              </td>
            </tr>
            <tr v-if="!filteredUsers.length">
              <td colspan="7" style="text-align:center;color:var(--c-muted);padding:40px">Sem utilizadores.</td>
            </tr>
          </tbody>
        </table>

        <div class="users-mobile-list">
          <article v-for="u in filteredUsers" :key="u.id" class="user-card">
            <div class="user-card-top">
              <input type="checkbox" :checked="selectedIds.includes(u.id)" @change="toggleSelected(u.id)" />
              <AvatarCircle :name="u.display_name" size="34" />
              <div>
                <div class="user-card-name">{{ u.display_name }}</div>
                <div class="user-card-email">{{ u.email }}</div>
              </div>
            </div>
            <div class="user-card-grid">
              <label>
                <span>Papel</span>
                <select class="hd-select compact" :value="u.role" @change="changeRole(u, ($event.target as HTMLSelectElement).value)">
                  <option v-for="role in roleOptions" :key="role.value" :value="role.value">{{ role.label }}</option>
                </select>
              </label>
              <label>
                <span>Origem</span>
                <button class="role-source" :class="{ locked: u.role_locked }" @click="toggleRoleLock(u)">
                  <span class="material-icons">{{ u.role_locked ? 'lock' : 'sync' }}</span>
                  {{ u.role_locked ? 'Manual' : 'Entra ID' }}
                </button>
              </label>
              <label>
                <span>Estado</span>
                <button class="role-source" :class="{ locked: u.is_active }" @click="toggleActive(u)">
                  <span class="material-icons">{{ u.is_active ? 'check_circle' : 'block' }}</span>
                  {{ u.is_active ? 'Ativo' : 'Inativo' }}
                </button>
              </label>
            </div>
            <div class="user-card-meta">{{ u.department || 'Sem departamento' }}</div>
            <div class="user-card-ou">{{ u.onprem_path || 'Sem OU local' }}</div>
          </article>
        </div>
      </template>
    </div>

    <div v-if="tab === 'permissions'" class="hd-card" style="padding:28px">
      <div style="font-weight:600;font-size:15px;margin-bottom:20px">Mapeamento de papéis</div>
      <div class="role-grid">
        <div v-for="role in roleDefinitions" :key="role.name" class="role-card">
          <div class="hd-row" style="margin-bottom:8px">
            <span class="material-icons" :style="{ color: role.color, fontSize: '18px' }">{{ role.icon }}</span>
            <div style="font-weight:600;font-size:14px;margin-left:8px">{{ role.label }}</div>
            <div class="hd-spacer"></div>
            <span class="role-count">{{ users.filter(u => u.role === role.name).length }} utilizadores</span>
          </div>
          <div v-for="perm in role.permissions" :key="perm" class="role-perm">
            <span class="material-icons">check_circle</span>{{ perm }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="tab === 'departments'" class="hd-card" style="padding:28px">
      <div style="font-weight:600;font-size:15px;margin-bottom:4px">Departamentos e OUs</div>
      <div style="font-size:13px;color:var(--c-muted);margin-bottom:20px">Dados importados do Microsoft Entra ID.</div>
      <div class="department-grid">
        <div v-for="dept in departments" :key="dept" class="department-card">
          <div class="hd-row" style="gap:6px;margin-bottom:4px">
            <span class="material-icons" style="font-size:16px;color:var(--c-primary)">apartment</span>
            <div style="font-weight:500;font-size:13px">{{ dept }}</div>
          </div>
          <div style="font-size:12px;color:var(--c-muted)">{{ users.filter(u => u.department === dept).length }} membros</div>
        </div>
        <div v-if="!departments.length" style="color:var(--c-muted);font-size:13px;grid-column:1/-1">Nenhum departamento encontrado.</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { bulkUpdateUsers, getUsers, importAzureUsers, updateUser } from '../../api/users'
import AvatarCircle from '../../components/AvatarCircle.vue'

const users = ref<any[]>([])
const selectedIds = ref<number[]>([])
const loading = ref(false)
const syncing = ref(false)
const syncMessage = ref('')
const syncReport = ref<any>(null)
const tab = ref<'users' | 'permissions' | 'departments'>('users')
const search = ref('')
const filterRole = ref('')
const filterSource = ref('')
const filterActive = ref('')
const filterDepartment = ref('')
const bulkRole = ref('')

const roleOptions = [
  { value: 'teacher', label: 'Docente' },
  { value: 'non_teaching', label: 'Não docente' },
  { value: 'secretary', label: 'Secretaria' },
  { value: 'technician', label: 'Técnico' },
  { value: 'admin', label: 'Administrador' },
]

const filteredUsers = computed(() => users.value.filter(u => {
  const haystack = `${u.display_name} ${u.email} ${u.username}`.toLowerCase()
  const matchText = !search.value || haystack.includes(search.value.toLowerCase())
  const matchRole = !filterRole.value || u.role === filterRole.value
  const matchSource = !filterSource.value || (filterSource.value === 'manual' ? u.role_locked : !u.role_locked)
  const matchActive = !filterActive.value || (filterActive.value === 'active' ? u.is_active : !u.is_active)
  const matchDepartment = !filterDepartment.value || u.department === filterDepartment.value
  return matchText && matchRole && matchSource && matchActive && matchDepartment
}))

const departments = computed(() => {
  const set = new Set(users.value.map(u => u.department).filter(Boolean))
  return Array.from(set).sort() as string[]
})

const lockedCount = computed(() => users.value.filter(u => u.role_locked).length)
const allVisibleSelected = computed(() => filteredUsers.value.length > 0 && filteredUsers.value.every(u => selectedIds.value.includes(u.id)))

const roleDefinitions = [
  { name: 'teacher', label: 'Docente', icon: 'school', color: '#3D52D5', permissions: ['Criar e gerir os próprios tickets', 'Adicionar comentários', 'Ver estado dos pedidos'] },
  { name: 'non_teaching', label: 'Não docente', icon: 'badge', color: '#64748B', permissions: ['Criar e gerir os próprios tickets', 'Adicionar comentários', 'Ver estado dos pedidos'] },
  { name: 'secretary', label: 'Secretaria', icon: 'business_center', color: '#0D9488', permissions: ['Criar e gerir os próprios tickets', 'Adicionar comentários', 'Ver estado dos pedidos'] },
  { name: 'technician', label: 'Técnico', icon: 'build', color: '#F59E0B', permissions: ['Ver e gerir todos os tickets', 'Atribuir e atualizar estados', 'Adicionar notas internas'] },
  { name: 'admin', label: 'Administrador', icon: 'admin_panel_settings', color: '#EF4444', permissions: ['Gerir utilizadores e papéis', 'Configurar categorias e SLAs', 'Exportar dados e fazer backup', 'Configurar integrações'] },
]

onMounted(loadUsers)

async function loadUsers() {
  loading.value = true
  try { users.value = await getUsers() }
  finally { loading.value = false }
}

async function changeRole(user: any, role: string) {
  try {
    const updated = await updateUser(user.id, { role })
    replaceUser(updated)
  } catch { /* ignore */ }
}

async function toggleRoleLock(user: any) {
  try {
    const updated = await updateUser(user.id, { role_locked: !user.role_locked })
    replaceUser(updated)
  } catch { /* ignore */ }
}

async function toggleActive(user: any) {
  try {
    const updated = await updateUser(user.id, { is_active: !user.is_active })
    replaceUser(updated)
  } catch { /* ignore */ }
}

async function syncEntra() {
  if (syncing.value) return
  syncing.value = true
  syncMessage.value = ''
  syncReport.value = null
  try {
    syncReport.value = await importAzureUsers()
    await loadUsers()
    syncMessage.value = 'Sincronização concluída.'
  } catch (e: any) {
    syncMessage.value = e?.response?.data?.detail || 'Não foi possível importar utilizadores do Entra ID.'
  } finally {
    syncing.value = false
  }
}

function toggleSelected(id: number) {
  selectedIds.value = selectedIds.value.includes(id) ? selectedIds.value.filter(i => i !== id) : [...selectedIds.value, id]
}

function toggleAllVisible() {
  if (allVisibleSelected.value) {
    selectedIds.value = selectedIds.value.filter(id => !filteredUsers.value.some(u => u.id === id))
  } else {
    selectedIds.value = Array.from(new Set([...selectedIds.value, ...filteredUsers.value.map(u => u.id)]))
  }
}

async function applyBulkRole() {
  if (!bulkRole.value) return
  await applyBulk({ role: bulkRole.value })
  bulkRole.value = ''
}

async function applyBulkActive(is_active: boolean) {
  await applyBulk({ is_active })
}

async function applyBulkLock(role_locked: boolean) {
  await applyBulk({ role_locked })
}

async function applyBulk(payload: any) {
  if (!selectedIds.value.length) return
  try {
    const updated = await bulkUpdateUsers({ ids: selectedIds.value, ...payload })
    updated.forEach(replaceUser)
  } catch { /* ignore */ }
}

function replaceUser(updated: any) {
  const idx = users.value.findIndex(u => u.id === updated.id)
  if (idx !== -1) users.value[idx] = { ...users.value[idx], ...updated }
}
</script>

<style scoped>
.admin-users-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.sync-note, .sync-message {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--c-muted);
}
.sync-note .material-icons { font-size: 15px; color: #3D52D5; }
.sync-link {
  border: 0;
  background: transparent;
  color: #3D52D5;
  font-weight: 600;
  cursor: pointer;
}
.admin-users-summary, .sync-report {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.admin-users-summary > div, .sync-report > div {
  border: 1px solid var(--c-border);
  border-radius: 8px;
  background: var(--c-surface);
  padding: 8px 12px;
}
.admin-users-summary strong, .sync-report strong {
  display: block;
  font-size: 18px;
}
.admin-users-summary span, .sync-report span, .sync-report-muted {
  color: var(--c-muted);
  font-size: 12px;
}
.sync-report {
  margin-bottom: 14px;
}
.sync-report-muted {
  display: flex !important;
  align-items: center;
}
.users-toolbar, .bulk-bar {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--c-border);
  flex-wrap: wrap;
  align-items: center;
}
.users-toolbar .hd-input { max-width: 300px; }
.users-toolbar .hd-select, .bulk-bar .hd-select { width: auto; }
.bulk-bar {
  background: var(--c-bg);
}
.users-count {
  padding: 10px 16px;
  color: var(--c-muted);
  font-size: 13px;
}
.compact {
  font-size: 12px;
  padding: 4px 7px;
  width: auto;
}
.role-source {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--c-border);
  border-radius: 999px;
  background: var(--c-bg);
  color: var(--c-muted);
  padding: 4px 9px;
  font-size: 12px;
  cursor: pointer;
}
.role-source.locked {
  color: #3D52D5;
  background: rgba(61, 82, 213, 0.1);
  border-color: rgba(61, 82, 213, 0.25);
}
.role-source .material-icons { font-size: 14px; }
.role-grid, .department-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}
.role-card, .department-card {
  border: 1px solid var(--c-border);
  border-radius: 10px;
  padding: 16px;
}
.role-count {
  font-size: 12px;
  color: var(--c-muted);
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 12px;
  padding: 2px 10px;
}
.role-perm {
  display: flex;
  gap: 6px;
  font-size: 13px;
  color: var(--c-muted);
  margin-top: 5px;
}
.role-perm .material-icons {
  font-size: 14px;
  color: #22C55E;
}
.users-mobile-list { display: none; }

@media (max-width: 820px) {
  .admin-users-page { padding: 16px; }
  .admin-users-head {
    flex-direction: column;
  }
  .admin-users-summary > div, .sync-report > div {
    flex: 1 1 130px;
  }
  .users-toolbar {
    display: grid;
    grid-template-columns: 1fr;
  }
  .users-toolbar .hd-input, .users-toolbar .hd-select, .bulk-bar .hd-select {
    max-width: none;
    width: 100%;
  }
  .bulk-bar {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  .bulk-bar span, .bulk-bar select {
    grid-column: 1 / -1;
  }
  .users-table { display: none; }
  .users-mobile-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
  }
  .user-card {
    border: 1px solid var(--c-border);
    border-radius: 8px;
    padding: 14px;
    background: var(--c-surface);
  }
  .user-card-top {
    display: grid;
    grid-template-columns: auto auto 1fr;
    gap: 10px;
    align-items: center;
    margin-bottom: 12px;
  }
  .user-card-name {
    font-weight: 700;
    font-size: 14px;
  }
  .user-card-email, .user-card-meta, .user-card-ou {
    color: var(--c-muted);
    font-size: 12px;
    overflow-wrap: anywhere;
  }
  .user-card-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    margin-bottom: 10px;
  }
  .user-card-grid label {
    display: grid;
    gap: 5px;
  }
  .user-card-grid label > span {
    color: var(--c-muted);
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
  }
}
</style>
