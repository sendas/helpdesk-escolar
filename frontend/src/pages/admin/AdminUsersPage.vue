<template>
  <div class="hd-page admin-users-page">
    <div class="admin-users-head">
      <div>
        <h1 style="font-size:22px;margin-bottom:6px">Utilizadores e permissões</h1>
        <div class="sync-note">
          <span class="material-icons">sync</span>
          Sincronização Entra ID
          <button type="button" class="sync-link" @click="openSyncDialog" :disabled="syncing">
            {{ syncing ? 'A sincronizar...' : 'Escolher OUs e sincronizar' }}
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
        convidados {{ syncReport.skipped_guests }} · inativos {{ syncReport.skipped_disabled }} · alunos {{ syncReport.skipped_students || 0 }} · fora das regras {{ syncReport.skipped_outside_ou }} · sem email {{ syncReport.skipped_without_email }}
      </div>
    </div>
    <div v-if="syncMessage" class="sync-message">{{ syncMessage }}</div>

    <div v-if="showSyncDialog" class="sync-modal-backdrop" @click.self="showSyncDialog = false">
      <section class="sync-modal hd-card">
        <div class="sync-modal-head">
          <div>
            <h2>Sincronizar Entra ID</h2>
            <p>Sincronize todos os utilizadores ativos do Entra ID. Os alunos são sempre ignorados automaticamente.</p>
          </div>
          <div class="sync-modal-actions sync-modal-actions-top">
            <button class="hd-btn hd-btn-outline" @click="showSyncDialog = false">Cancelar</button>
            <button class="hd-btn hd-btn-primary" @click="runSyncWithOus" :disabled="syncing || (!syncAllOus && !selectedSyncOus.length)">
              <span class="material-icons" style="font-size:16px">sync</span>
              {{ syncing ? 'A sincronizar...' : 'Guardar e sincronizar' }}
            </button>
            <button class="hd-icon-btn" @click="showSyncDialog = false" title="Fechar">
              <span class="material-icons">close</span>
            </button>
          </div>
        </div>

        <label class="sync-all-option">
          <input type="checkbox" v-model="syncAllOus" />
          <span>
            <strong>Sincronizar todos os utilizadores não alunos</strong>
            <small>Importa todos os utilizadores ativos do Entra ID e ignora alunos automaticamente.</small>
          </span>
        </label>

        <div v-if="!syncAllOus" class="sync-ou-panel">
          <div class="sync-ou-list">
            <label v-for="ou in knownOus" :key="ou" class="sync-ou-item">
              <input type="checkbox" :value="ou" v-model="selectedSyncOus" />
              <span>{{ ou }}</span>
            </label>
            <div v-if="!knownOus.length" class="empty-note">Ainda não há OUs importadas. Pode escrever uma manualmente abaixo.</div>
          </div>
          <div class="sync-ou-add">
            <input class="hd-input" v-model="newSyncOu" placeholder="Ex: queiroz.local/aeeq/_docentes" @keyup.enter="addSyncOu" />
            <button class="hd-btn hd-btn-outline" @click="addSyncOu" :disabled="!newSyncOu.trim()">Adicionar OU</button>
          </div>
          <div v-if="selectedSyncOus.length" class="sync-ou-chips">
            <button v-for="ou in selectedSyncOus" :key="ou" class="watcher-chip" @click="removeSyncOu(ou)">
              {{ ou }}
              <span class="material-icons">close</span>
            </button>
          </div>
        </div>

        <div class="sync-modal-actions">
          <button class="hd-btn hd-btn-outline" @click="showSyncDialog = false">Cancelar</button>
          <button class="hd-btn hd-btn-primary" @click="runSyncWithOus" :disabled="syncing || (!syncAllOus && !selectedSyncOus.length)">
            <span class="material-icons" style="font-size:16px">sync</span>
            {{ syncing ? 'A sincronizar...' : 'Guardar e sincronizar' }}
          </button>
        </div>
      </section>
    </div>

    <div v-if="showCreateUserDialog" class="sync-modal-backdrop" @click.self="closeCreateUserDialog">
      <section class="sync-modal hd-card">
        <div class="sync-modal-head">
          <div>
            <h2>Adicionar utilizador manual</h2>
            <p>Crie um utilizador fora do Entra ID, com autenticação local por email e palavra-passe.</p>
          </div>
          <button class="hd-icon-btn" @click="closeCreateUserDialog" title="Fechar">
            <span class="material-icons">close</span>
          </button>
        </div>

        <div class="manual-user-form">
          <label>
            Nome
            <input class="hd-input" v-model="manualUserForm.display_name" placeholder="Ex: Controlink Suporte" />
          </label>
          <label>
            Email de login
            <input class="hd-input" v-model="manualUserForm.email" type="email" placeholder="suporte@empresa.pt" />
          </label>
          <label>
            Papel
            <select class="hd-select" v-model="manualUserForm.role">
              <option v-for="role in roleOptions" :key="role.value" :value="role.value">{{ role.label }}</option>
            </select>
          </label>
          <label>
            Departamento / OU
            <input class="hd-input" v-model="manualUserForm.department" placeholder="Empresa de apoio, TIC..." />
          </label>
          <label class="full">
            Palavra-passe inicial
            <input class="hd-input" v-model="manualUserForm.password" type="password" autocomplete="new-password" placeholder="Mínimo 8 caracteres" />
          </label>
          <label class="manual-active-option full">
            <input type="checkbox" v-model="manualUserForm.is_active" />
            <span>Utilizador ativo</span>
          </label>
          <label class="manual-active-option full">
            <input type="checkbox" v-model="manualUserForm.is_technician" />
            <span>Pode receber e assumir tickets como técnico</span>
          </label>
        </div>

        <div v-if="manualUserError" class="form-error">{{ manualUserError }}</div>

        <div class="sync-modal-actions">
          <button class="hd-btn hd-btn-outline" @click="closeCreateUserDialog">Cancelar</button>
          <button class="hd-btn hd-btn-primary" @click="addManualUser" :disabled="creatingManualUser">
            <span class="material-icons" style="font-size:16px">person_add</span>
            {{ creatingManualUser ? 'A criar...' : 'Criar utilizador' }}
          </button>
        </div>
      </section>
    </div>

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
      <button class="hd-tab" :class="{ active: tab === 'groups' }" @click="tab = 'groups'">
        <span class="material-icons" style="font-size:15px">groups</span> Grupos
      </button>
    </div>

    <div v-if="tab === 'users'" class="hd-card users-card">
      <div class="users-toolbar">
        <button class="hd-btn hd-btn-primary" @click="showCreateUserDialog = true">
          <span class="material-icons" style="font-size:16px">person_add</span>
          Adicionar utilizador
        </button>
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
        <button class="hd-btn hd-btn-outline" @click="applyBulkTechnician(true)">Marcar técnico</button>
        <button class="hd-btn hd-btn-outline" @click="applyBulkTechnician(false)">Retirar técnico</button>
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
              <th>TÉCNICO</th>
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
                <button class="role-source" :class="{ locked: u.is_technician }" @click="toggleTechnician(u)">
                  <span class="material-icons">{{ u.is_technician ? 'engineering' : 'person' }}</span>
                  {{ u.is_technician ? 'Recebe tickets' : 'Não recebe' }}
                </button>
              </td>
              <td>
                <button class="role-source" :class="{ locked: u.role_locked }" @click="toggleRoleLock(u)">
                  <span class="material-icons">{{ u.role_locked ? 'lock' : 'sync' }}</span>
                  {{ u.role_locked ? 'Manual' : 'Entra ID' }}
                </button>
              </td>
              <td>
                <input
                  class="department-input"
                  :value="u.department || ''"
                  placeholder="Departamento / OU"
                  @change="changeDepartment(u, ($event.target as HTMLInputElement).value)"
                />
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
              <td colspan="8" style="text-align:center;color:var(--c-muted);padding:40px">Sem utilizadores.</td>
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
                <span>Técnico</span>
                <button class="role-source" :class="{ locked: u.is_technician }" @click="toggleTechnician(u)">
                  <span class="material-icons">{{ u.is_technician ? 'engineering' : 'person' }}</span>
                  {{ u.is_technician ? 'Recebe tickets' : 'Não recebe' }}
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
            <input
              class="department-input mobile"
              :value="u.department || ''"
              placeholder="Departamento / OU"
              @change="changeDepartment(u, ($event.target as HTMLInputElement).value)"
            />
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

    <div v-if="tab === 'groups'" class="hd-card groups-card">
      <div class="groups-head">
        <div>
          <div style="font-weight:600;font-size:15px;margin-bottom:4px">Grupos internos</div>
          <div style="font-size:13px;color:var(--c-muted)">Cria equipas e atribui os utilizadores que devem pertencer a cada grupo.</div>
        </div>
        <div class="group-create">
          <input class="hd-input" v-model="groupForm.name" placeholder="Nome do grupo" />
          <input class="hd-input" v-model="groupForm.description" placeholder="Descrição opcional" />
          <button class="hd-btn hd-btn-primary" @click="addGroup" :disabled="!groupForm.name.trim()">
            <span class="material-icons" style="font-size:16px">add</span> Criar grupo
          </button>
        </div>
      </div>

      <div class="groups-layout">
        <aside class="groups-list">
          <button
            v-for="group in groups"
            :key="group.id"
            class="group-list-item"
            :class="{ active: selectedGroupId === group.id }"
            @click="selectGroup(group.id)"
          >
            <span class="material-icons">groups</span>
            <span>
              <strong>{{ group.name }}</strong>
              <small>{{ group.members.length }} membro{{ group.members.length !== 1 ? 's' : '' }}</small>
            </span>
          </button>
          <div v-if="!groups.length" class="empty-note">Ainda não existem grupos.</div>
        </aside>

        <section v-if="selectedGroup" class="group-detail">
          <div class="group-detail-top">
            <div>
              <h2>{{ selectedGroup.name }}</h2>
              <p>{{ selectedGroup.description || 'Sem descrição' }}</p>
            </div>
            <button class="hd-btn hd-btn-outline" @click="removeGroup(selectedGroup.id)">
              <span class="material-icons" style="font-size:16px">delete</span> Apagar
            </button>
          </div>

          <div class="group-member-toolbar">
            <input class="hd-input" v-model="groupUserSearch" placeholder="Pesquisar por nome, email ou utilizador..." />
            <button class="hd-btn hd-btn-primary" @click="saveGroupMembers">
              <span class="material-icons" style="font-size:16px">save</span> Guardar membros
            </button>
          </div>

          <div class="group-members-grid">
            <label v-for="u in groupCandidateUsers" :key="u.id" class="group-member-card">
              <input type="checkbox" :value="u.id" v-model="groupMemberIds" />
              <AvatarCircle :name="u.display_name" size="30" />
              <span>
                <strong>{{ u.display_name }}</strong>
                <small>{{ u.email }}</small>
              </span>
            </label>
          </div>
        </section>
        <section v-else class="group-detail empty-note">
          Seleciona ou cria um grupo para gerir os membros.
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { bulkUpdateUsers, createGroup, createUser, deleteGroup, getGroups, getUsers, importAzureUsers, updateGroupMembers, updateUser } from '../../api/users'
import { getAzureSyncSettings, updateAzureSyncSettings } from '../../api/settings'
import AvatarCircle from '../../components/AvatarCircle.vue'

const users = ref<any[]>([])
const groups = ref<any[]>([])
const selectedIds = ref<number[]>([])
const loading = ref(false)
const syncing = ref(false)
const syncMessage = ref('')
const syncReport = ref<any>(null)
const tab = ref<'users' | 'permissions' | 'departments' | 'groups'>('users')
const search = ref('')
const filterRole = ref('')
const filterSource = ref('')
const filterActive = ref('')
const filterDepartment = ref('')
const bulkRole = ref('')
const groupForm = ref({ name: '', description: '' })
const selectedGroupId = ref<number | null>(null)
const groupMemberIds = ref<number[]>([])
const groupUserSearch = ref('')
const showSyncDialog = ref(false)
const showCreateUserDialog = ref(false)
const creatingManualUser = ref(false)
const manualUserError = ref('')
const manualUserForm = ref({
  display_name: '',
  email: '',
  password: '',
  role: 'teacher',
  department: '',
  is_active: true,
  is_technician: false,
})
const syncAllOus = ref(true)
const selectedSyncOus = ref<string[]>([])
const newSyncOu = ref('')
const azureSyncSettingsLoaded = ref(false)

const suggestedOus = [
  'queiroz.local/aeeq/_direcao',
  'queiroz.local/aeeq/_docentes',
  'queiroz.local/aeeq/_nao docentes',
  'queiroz.local/aeeq/_secretaria',
  'queiroz.local/aeeq/_suporte',
  'queiroz.local/aeeq/secretaria-eseq',
]

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

const knownOus = computed(() => {
  const set = new Set<string>()
  suggestedOus.forEach(ou => set.add(ou))
  users.value.forEach(u => {
    if (u.onprem_path) set.add(u.onprem_path)
  })
  selectedSyncOus.value.forEach(ou => set.add(ou))
  return Array.from(set).sort((a, b) => a.localeCompare(b))
})

const lockedCount = computed(() => users.value.filter(u => u.role_locked).length)
const allVisibleSelected = computed(() => filteredUsers.value.length > 0 && filteredUsers.value.every(u => selectedIds.value.includes(u.id)))
const selectedGroup = computed(() => groups.value.find(g => g.id === selectedGroupId.value) || null)
const groupCandidateUsers = computed(() => {
  const q = groupUserSearch.value.trim().toLowerCase()
  return users.value
    .filter(u => u.is_active)
    .filter(u => groupMemberIds.value.includes(u.id) || (q && `${u.display_name} ${u.email} ${u.username} ${u.department || ''}`.toLowerCase().includes(q)))
})

const roleDefinitions = [
  { name: 'teacher', label: 'Docente', icon: 'school', color: '#3D52D5', permissions: ['Criar e gerir os próprios tickets', 'Adicionar comentários', 'Ver estado dos pedidos'] },
  { name: 'non_teaching', label: 'Não docente', icon: 'badge', color: '#64748B', permissions: ['Criar e gerir os próprios tickets', 'Adicionar comentários', 'Ver estado dos pedidos'] },
  { name: 'secretary', label: 'Secretaria', icon: 'business_center', color: '#0D9488', permissions: ['Criar e gerir os próprios tickets', 'Adicionar comentários', 'Ver estado dos pedidos'] },
  { name: 'technician', label: 'Técnico', icon: 'build', color: '#F59E0B', permissions: ['Ver e gerir todos os tickets', 'Atribuir e atualizar estados', 'Adicionar notas internas'] },
  { name: 'admin', label: 'Administrador', icon: 'admin_panel_settings', color: '#EF4444', permissions: ['Gerir utilizadores e papéis', 'Configurar categorias e tempos de resposta', 'Exportar dados e fazer backup', 'Configurar integrações'] },
]

onMounted(async () => {
  await Promise.all([loadUsers(), loadGroups(), loadAzureSyncSettings()])
})

async function loadUsers() {
  loading.value = true
  try { users.value = await getUsers() }
  finally { loading.value = false }
}

async function loadGroups() {
  groups.value = await getGroups()
  if (!selectedGroupId.value && groups.value.length) selectGroup(groups.value[0].id)
}

async function loadAzureSyncSettings() {
  try {
    const settings = await getAzureSyncSettings()
    selectedSyncOus.value = settings.allowed_onprem_ous || []
    syncAllOus.value = selectedSyncOus.value.length === 0
    azureSyncSettingsLoaded.value = true
  } catch {
    azureSyncSettingsLoaded.value = false
  }
}

async function openSyncDialog() {
  if (!azureSyncSettingsLoaded.value) await loadAzureSyncSettings()
  showSyncDialog.value = true
}

function resetManualUserForm() {
  manualUserForm.value = {
    display_name: '',
    email: '',
    password: '',
    role: 'teacher',
    department: '',
    is_active: true,
    is_technician: false,
  }
  manualUserError.value = ''
}

function closeCreateUserDialog() {
  if (creatingManualUser.value) return
  showCreateUserDialog.value = false
  resetManualUserForm()
}

async function addManualUser() {
  manualUserError.value = ''
  const displayName = manualUserForm.value.display_name.trim()
  const email = manualUserForm.value.email.trim().toLowerCase()
  const password = manualUserForm.value.password.trim()
  if (!displayName || !email || !password) {
    manualUserError.value = 'Preencha nome, email e palavra-passe.'
    return
  }
  if (password.length < 8) {
    manualUserError.value = 'A palavra-passe deve ter pelo menos 8 caracteres.'
    return
  }
  creatingManualUser.value = true
  try {
    const created = await createUser({
      display_name: displayName,
      email,
      password,
      role: manualUserForm.value.role,
      is_technician: manualUserForm.value.is_technician || manualUserForm.value.role === 'technician',
      department: manualUserForm.value.department.trim(),
      is_active: manualUserForm.value.is_active,
    })
    users.value = [...users.value, created].sort((a, b) => a.display_name.localeCompare(b.display_name))
    creatingManualUser.value = false
    closeCreateUserDialog()
  } catch (e: any) {
    manualUserError.value = e?.response?.data?.detail || 'Não foi possível criar o utilizador.'
  } finally {
    creatingManualUser.value = false
  }
}

function addSyncOu() {
  const ou = newSyncOu.value.trim()
  if (ou && !selectedSyncOus.value.some(item => item.toLowerCase() === ou.toLowerCase())) {
    selectedSyncOus.value = [...selectedSyncOus.value, ou]
  }
  newSyncOu.value = ''
}

function removeSyncOu(ou: string) {
  selectedSyncOus.value = selectedSyncOus.value.filter(item => item !== ou)
}

async function runSyncWithOus() {
  const allowed_onprem_ous = syncAllOus.value ? [] : selectedSyncOus.value
  await updateAzureSyncSettings({ allowed_onprem_ous })
  azureSyncSettingsLoaded.value = true
  showSyncDialog.value = false
  await syncEntra()
}

async function addGroup() {
  if (!groupForm.value.name.trim()) return
  const created = await createGroup({ name: groupForm.value.name, description: groupForm.value.description })
  groups.value = [...groups.value, created].sort((a, b) => a.name.localeCompare(b.name))
  groupForm.value = { name: '', description: '' }
  selectGroup(created.id)
}

function selectGroup(id: number) {
  selectedGroupId.value = id
  const group = groups.value.find(g => g.id === id)
  groupMemberIds.value = group ? group.members.map((m: any) => m.id) : []
}

async function saveGroupMembers() {
  if (!selectedGroupId.value) return
  const updated = await updateGroupMembers(selectedGroupId.value, groupMemberIds.value)
  const idx = groups.value.findIndex(g => g.id === updated.id)
  if (idx !== -1) groups.value[idx] = updated
}

async function removeGroup(id: number) {
  if (!window.confirm('Apagar este grupo?')) return
  await deleteGroup(id)
  groups.value = groups.value.filter(g => g.id !== id)
  selectGroup(groups.value[0]?.id ?? 0)
  if (!groups.value.length) {
    selectedGroupId.value = null
    groupMemberIds.value = []
  }
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

async function toggleTechnician(user: any) {
  try {
    const updated = await updateUser(user.id, { is_technician: !user.is_technician })
    replaceUser(updated)
  } catch { /* ignore */ }
}

async function changeDepartment(user: any, department: string) {
  const value = department.trim()
  if ((user.department || '') === value) return
  try {
    const updated = await updateUser(user.id, { department: value })
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

async function applyBulkTechnician(is_technician: boolean) {
  await applyBulk({ is_technician })
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
.sync-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.48);
}
.sync-modal {
  width: min(720px, 100%);
  padding: 22px;
  max-height: calc(100vh - 40px);
  overflow: auto;
}
.sync-modal-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  position: sticky;
  top: -22px;
  z-index: 2;
  background: var(--c-surface);
  padding: 0 0 12px;
}
.sync-modal h2 {
  margin: 0 0 4px;
  font-size: 20px;
}
.sync-modal p {
  margin: 0;
  color: var(--c-muted);
  font-size: 13px;
}
.sync-all-option {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: flex-start;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 14px;
}
.sync-all-option strong,
.sync-all-option small {
  display: block;
}
.sync-all-option small {
  color: var(--c-muted);
  font-size: 12px;
  margin-top: 3px;
}
.sync-ou-panel {
  display: grid;
  gap: 12px;
}
.sync-ou-list {
  display: grid;
  gap: 8px;
  max-height: 220px;
  overflow: auto;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 10px;
}
.sync-ou-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px;
  align-items: center;
  color: var(--c-text);
  font-size: 13px;
}
.sync-ou-add,
.sync-modal-actions,
.sync-ou-chips {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}
.sync-modal-actions {
  justify-content: flex-end;
  margin-top: 18px;
}
.sync-modal-actions-top {
  flex-wrap: nowrap;
  margin-top: 0;
  align-self: flex-start;
}
.manual-user-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.manual-user-form label {
  display: grid;
  gap: 6px;
  color: var(--c-muted);
  font-size: 12px;
  font-weight: 700;
}
.manual-user-form .full {
  grid-column: 1 / -1;
}
.manual-active-option {
  grid-template-columns: auto 1fr !important;
  align-items: center;
  color: var(--c-text) !important;
}
.form-error {
  margin-top: 12px;
  color: #DC2626;
  font-size: 13px;
}
.watcher-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border: 1px solid rgba(61, 82, 213, 0.24);
  border-radius: 999px;
  background: rgba(61, 82, 213, 0.08);
  color: #3D52D5;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
.watcher-chip .material-icons { font-size: 13px; }
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
.department-input {
  width: min(260px, 100%);
  border: 1px solid var(--c-border);
  border-radius: 7px;
  background: var(--c-surface);
  color: var(--c-text);
  padding: 6px 8px;
  font-size: 13px;
}
.department-input.mobile {
  width: 100%;
  margin-bottom: 8px;
}
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
.groups-card {
  padding: 0;
  overflow: hidden;
}
.groups-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  padding: 20px;
  border-bottom: 1px solid var(--c-border);
}
.group-create {
  display: grid;
  grid-template-columns: minmax(160px, 220px) minmax(180px, 260px) auto;
  gap: 10px;
  align-items: center;
}
.groups-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 420px;
}
.groups-list {
  border-right: 1px solid var(--c-border);
  padding: 12px;
  background: var(--c-bg);
}
.group-list-item {
  width: 100%;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  align-items: center;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--c-text);
  padding: 12px;
  text-align: left;
  cursor: pointer;
}
.group-list-item.active {
  background: rgba(61, 82, 213, 0.1);
  border-color: rgba(61, 82, 213, 0.25);
  color: #3D52D5;
}
.group-list-item .material-icons { font-size: 18px; }
.group-list-item strong, .group-list-item small {
  display: block;
}
.group-list-item small, .empty-note {
  color: var(--c-muted);
  font-size: 12px;
}
.group-detail {
  padding: 20px;
  min-width: 0;
}
.group-detail-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}
.group-detail h2 {
  font-size: 18px;
  margin: 0 0 4px;
}
.group-detail p {
  margin: 0;
  color: var(--c-muted);
  font-size: 13px;
}
.group-member-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.group-member-toolbar .hd-input {
  max-width: 360px;
}
.group-members-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}
.group-member-card {
  display: grid;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 10px;
  background: var(--c-surface);
}
.group-member-card strong, .group-member-card small {
  display: block;
  overflow-wrap: anywhere;
}
.group-member-card strong {
  font-size: 13px;
}
.group-member-card small {
  color: var(--c-muted);
  font-size: 11px;
}

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
  .groups-head {
    flex-direction: column;
  }
  .group-create, .groups-layout {
    grid-template-columns: 1fr;
  }
  .groups-list {
    border-right: 0;
    border-bottom: 1px solid var(--c-border);
  }
  .group-member-toolbar {
    flex-direction: column;
  }
  .group-member-toolbar .hd-input {
    max-width: none;
  }
  .group-members-grid {
    grid-template-columns: 1fr;
  }
  .sync-modal {
    padding: 18px;
  }
  .sync-modal-head {
    top: -18px;
    flex-direction: column;
  }
  .sync-modal-actions,
  .sync-ou-add {
    display: grid;
    grid-template-columns: 1fr;
  }
  .sync-modal-actions-top {
    grid-template-columns: 1fr;
    width: 100%;
  }
  .manual-user-form {
    grid-template-columns: 1fr;
  }
}
</style>
