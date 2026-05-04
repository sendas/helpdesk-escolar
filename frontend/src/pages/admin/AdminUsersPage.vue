<template>
  <div class="hd-page">
    <div class="hd-row" style="margin-bottom:20px">
      <h1 style="font-size:22px">Utilizadores e permissões</h1>
      <div class="hd-spacer"></div>
      <div class="hd-row" style="gap:6px;font-size:12px;color:var(--c-muted);background:var(--c-surface);border:1px solid var(--c-border);border-radius:6px;padding:4px 10px">
        <span class="material-icons" style="font-size:14px;color:#3D52D5">sync</span>
        Sincronizado com Entra ID ·
        <span style="color:#3D52D5;font-weight:500;cursor:pointer" @click="syncEntra">
          {{ syncing ? 'A sincronizar...' : 'Sincronizar agora' }}
        </span>
      </div>
    </div>
    <div v-if="syncMessage" style="font-size:13px;color:var(--c-muted);margin:-12px 0 16px">
      {{ syncMessage }}
    </div>

    <!-- Tabs -->
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

    <!-- Users tab -->
    <div v-if="tab === 'users'" class="hd-card">
      <div style="padding:12px 16px;border-bottom:1px solid var(--c-border);display:flex;gap:10px;align-items:center">
        <input class="hd-input" style="max-width:240px;padding:6px 10px;font-size:13px" placeholder="Filtrar por nome..." v-model="search" />
        <select class="hd-select" style="width:auto" v-model="filterRole">
          <option value="">Todos os papéis</option>
          <option value="teacher">Docente</option>
          <option value="technician">Técnico</option>
          <option value="admin">Administrador</option>
        </select>
        <div class="hd-spacer"></div>
        <span style="font-size:13px;color:var(--c-muted)">{{ filteredUsers.length }} utilizador{{ filteredUsers.length !== 1 ? 'es' : '' }}</span>
      </div>

      <div v-if="loading" style="padding:48px;text-align:center;color:var(--c-muted)">A carregar...</div>
      <table v-else class="hd-table">
        <thead>
          <tr>
            <th>UTILIZADOR</th>
            <th>EMAIL</th>
            <th>AUTENTICAÇÃO</th>
            <th>PAPEL</th>
            <th>DEPARTAMENTO</th>
            <th>ATIVO</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in filteredUsers" :key="u.id">
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
              <span :style="authBadgeStyle(u.auth_provider)">{{ authLabel(u.auth_provider) }}</span>
            </td>
            <td>
              <select
                class="hd-select"
                style="font-size:12px;padding:3px 6px;width:auto"
                :value="u.role"
                @change="changeRole(u, ($event.target as HTMLSelectElement).value)"
              >
                <option value="teacher">Docente</option>
                <option value="technician">Técnico</option>
                <option value="admin">Administrador</option>
              </select>
            </td>
            <td style="font-size:13px;color:var(--c-muted)">{{ u.department || '—' }}</td>
            <td>
              <div class="hd-toggle-wrap" @click="toggleActive(u)" :title="u.is_active ? 'Desativar' : 'Ativar'">
                <div class="hd-toggle" :class="{ active: u.is_active }"></div>
              </div>
            </td>
            <td>
              <button class="hd-icon-btn" title="Mais opções">
                <span class="material-icons" style="font-size:16px">more_vert</span>
              </button>
            </td>
          </tr>
          <tr v-if="!filteredUsers.length">
            <td colspan="7" style="text-align:center;color:var(--c-muted);padding:40px">Sem utilizadores.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Permissions tab -->
    <div v-if="tab === 'permissions'" class="hd-card" style="padding:28px">
      <div style="font-weight:600;font-size:15px;margin-bottom:20px">Mapeamento de papéis</div>
      <div style="display:flex;flex-direction:column;gap:16px;max-width:640px">
        <div v-for="role in roleDefinitions" :key="role.name" style="border:1px solid var(--c-border);border-radius:10px;padding:16px">
          <div class="hd-row" style="margin-bottom:8px">
            <span class="material-icons" :style="{ color: role.color, fontSize: '18px' }">{{ role.icon }}</span>
            <div style="font-weight:600;font-size:14px;margin-left:8px">{{ role.label }}</div>
            <div class="hd-spacer"></div>
            <span style="font-size:12px;color:var(--c-muted);background:var(--c-bg);border:1px solid var(--c-border);border-radius:12px;padding:2px 10px">
              {{ users.filter(u => u.role === role.name).length }} utilizadores
            </span>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px">
            <div v-for="perm in role.permissions" :key="perm" class="hd-row" style="gap:6px;font-size:13px;color:var(--c-muted)">
              <span class="material-icons" style="font-size:14px;color:#22C55E">check_circle</span>
              {{ perm }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Departments tab -->
    <div v-if="tab === 'departments'" class="hd-card" style="padding:28px">
      <div style="font-weight:600;font-size:15px;margin-bottom:4px">Departamentos</div>
      <div style="font-size:13px;color:var(--c-muted);margin-bottom:20px">Departamentos importados do Microsoft Entra ID.</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px">
        <div
          v-for="dept in departments"
          :key="dept"
          style="border:1px solid var(--c-border);border-radius:10px;padding:14px"
        >
          <div class="hd-row" style="gap:6px;margin-bottom:4px">
            <span class="material-icons" style="font-size:16px;color:var(--c-primary)">apartment</span>
            <div style="font-weight:500;font-size:13px">{{ dept }}</div>
          </div>
          <div style="font-size:12px;color:var(--c-muted)">
            {{ users.filter(u => u.department === dept).length }} membros
          </div>
        </div>
        <div v-if="!departments.length" style="color:var(--c-muted);font-size:13px;grid-column:1/-1">
          Nenhum departamento encontrado.
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getUsers, importAzureUsers, updateUser } from '../../api/users'
import AvatarCircle from '../../components/AvatarCircle.vue'

const users = ref<any[]>([])
const loading = ref(false)
const syncing = ref(false)
const syncMessage = ref('')
const tab = ref<'users' | 'permissions' | 'departments'>('users')
const search = ref('')
const filterRole = ref('')

const filteredUsers = computed(() => users.value.filter(u => {
  const matchName = !search.value || u.display_name.toLowerCase().includes(search.value.toLowerCase())
  const matchRole = !filterRole.value || u.role === filterRole.value
  return matchName && matchRole
}))

const departments = computed(() => {
  const set = new Set(users.value.map(u => u.department).filter(Boolean))
  return Array.from(set).sort() as string[]
})

const roleDefinitions = [
  {
    name: 'teacher', label: 'Docente', icon: 'school', color: '#3D52D5',
    permissions: ['Criar e gerir os próprios tickets', 'Adicionar comentários', 'Ver estado dos pedidos'],
  },
  {
    name: 'technician', label: 'Técnico', icon: 'build', color: '#F59E0B',
    permissions: ['Todas as permissões de Docente', 'Ver e gerir todos os tickets', 'Atribuir e atualizar estados', 'Adicionar notas internas'],
  },
  {
    name: 'admin', label: 'Administrador', icon: 'admin_panel_settings', color: '#EF4444',
    permissions: ['Todas as permissões de Técnico', 'Gerir utilizadores e papéis', 'Configurar categorias e SLAs', 'Exportar dados e fazer backup', 'Configurar integrações AD e email'],
  },
]

onMounted(async () => {
  loading.value = true
  try { users.value = await getUsers() }
  finally { loading.value = false }
})

async function changeRole(user: any, role: string) {
  try {
    const updated = await updateUser(user.id, { role })
    const idx = users.value.findIndex(u => u.id === user.id)
    if (idx !== -1) users.value[idx] = { ...users.value[idx], ...updated }
  } catch { /* ignore */ }
}

async function toggleActive(user: any) {
  try {
    const updated = await updateUser(user.id, { is_active: !user.is_active })
    const idx = users.value.findIndex(u => u.id === user.id)
    if (idx !== -1) users.value[idx] = { ...users.value[idx], ...updated }
  } catch { /* ignore */ }
}

async function syncEntra() {
  if (syncing.value) return
  syncing.value = true
  syncMessage.value = ''
  try {
    const result = await importAzureUsers()
    users.value = await getUsers()
    syncMessage.value = `Importação concluída: ${result.created} criado(s), ${result.updated} atualizado(s), ${result.skipped} ignorado(s).`
  } catch (e: any) {
    syncMessage.value = e?.response?.data?.detail || 'Não foi possível importar utilizadores do Entra ID.'
  } finally {
    syncing.value = false
  }
}

function authLabel(p: string) {
  return ({ ldap: 'LDAP', azure: 'Azure AD', demo: 'Demo' } as Record<string, string>)[p] ?? p
}

function authBadgeStyle(p: string) {
  const colors: Record<string, string> = { ldap: '#3D52D5', azure: '#0078D4', demo: '#6B7280' }
  const c = colors[p] ?? '#6B7280'
  return `display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;background:${c}22;color:${c}`
}
</script>
