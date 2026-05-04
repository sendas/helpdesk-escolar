<template>
  <div class="hd-page">
    <h1 style="font-size:22px;margin-bottom:24px">Configurações</h1>

    <!-- Tabs -->
    <div class="hd-tabs" style="margin-bottom:24px">
      <button class="hd-tab" :class="{ active: tab === 'general' }" @click="tab = 'general'">
        <span class="material-icons" style="font-size:15px">tune</span> Geral
      </button>
      <button class="hd-tab" :class="{ active: tab === 'ldap' }" @click="tab = 'ldap'">
        <span class="material-icons" style="font-size:15px">dns</span> Active Directory
      </button>
      <button class="hd-tab" :class="{ active: tab === 'email' }" @click="tab = 'email'">
        <span class="material-icons" style="font-size:15px">email</span> Notificações
      </button>
      <button class="hd-tab" :class="{ active: tab === 'categories' }" @click="tab = 'categories'">
        <span class="material-icons" style="font-size:15px">category</span> Categorias e SLAs
      </button>
      <button class="hd-tab" :class="{ active: tab === 'schools' }" @click="tab = 'schools'">
        <span class="material-icons" style="font-size:15px">account_balance</span> Escolas
      </button>
    </div>

    <!-- General -->
    <div v-if="tab === 'general'" class="hd-card" style="padding:28px;max-width:640px">
      <div style="font-weight:600;font-size:15px;margin-bottom:20px">Configurações gerais</div>
      <div class="hd-field" style="margin-bottom:18px">
        <label class="hd-label">Nome do Agrupamento</label>
        <input class="hd-input" v-model="general.org_name" placeholder="Agrupamento de Escolas Eça de Queirós" />
      </div>
      <div class="hd-field" style="margin-bottom:18px">
        <label class="hd-label">Logotipo do Agrupamento</label>
        <input type="file" accept=".png,.jpg,.jpeg,.svg,.webp,image/png,image/jpeg,image/svg+xml,image/webp" @change="onLogoPicked" />
        <div v-if="general.logo_url" style="margin-top:10px">
          <img :src="general.logo_url" alt="Logotipo" style="max-width:180px;max-height:80px;object-fit:contain" />
        </div>
        <p class="hd-hint">PNG, JPG, SVG ou WEBP até 2 MB.</p>
      </div>
      <div class="hd-field" style="margin-bottom:18px">
        <label class="hd-label">URL base da aplicação</label>
        <input class="hd-input" v-model="general.app_url" placeholder="http://helpdesk.escola.local" />
      </div>
      <div class="hd-field" style="margin-bottom:18px">
        <label class="hd-label">Fuso horário</label>
        <select class="hd-select" v-model="general.timezone" style="max-width:300px">
          <option value="Europe/Lisbon">Europe/Lisbon</option>
          <option value="UTC">UTC</option>
        </select>
      </div>
      <div class="hd-field" style="margin-bottom:24px">
        <label class="hd-label">Duração da sessão (minutos)</label>
        <input class="hd-input" type="number" v-model="general.jwt_expire" style="max-width:140px" />
        <p class="hd-hint">Tempo até o token JWT expirar e o utilizador ter de iniciar sessão novamente.</p>
      </div>
      <button class="hd-btn hd-btn-primary" @click="saveGeneral">
        <span class="material-icons" style="font-size:16px">save</span> Guardar
      </button>
      <span v-if="saved" style="margin-left:12px;font-size:13px;color:#22C55E">Guardado!</span>
    </div>

    <!-- Schools -->
    <div v-if="tab === 'schools'" class="hd-card" style="padding:28px;max-width:760px">
      <div class="hd-row" style="margin-bottom:20px">
        <div style="font-weight:600;font-size:15px">Escolas</div>
        <div class="hd-spacer"></div>
        <button class="hd-btn hd-btn-primary" style="font-size:12px;padding:6px 14px" @click="showNewSchool = true">
          <span class="material-icons" style="font-size:14px">add</span> Nova escola
        </button>
      </div>
      <div v-if="loadingSchools" style="color:var(--c-muted)">A carregar...</div>
      <table v-else class="hd-table">
        <thead><tr><th>NOME</th><th>NOME CURTO</th><th>MORADA</th><th></th></tr></thead>
        <tbody>
          <tr v-for="school in schools" :key="school.id">
            <td style="font-weight:500">{{ school.name }}</td>
            <td style="font-size:12px;color:var(--c-muted)">{{ school.short_name }}</td>
            <td style="font-size:12px;color:var(--c-muted)">{{ school.address || '—' }}</td>
            <td>
              <button class="hd-icon-btn" @click="deleteSchool(school.id)" title="Eliminar">
                <span class="material-icons" style="font-size:15px;color:#EF4444">delete</span>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="showNewSchool" style="margin-top:20px;border:1px solid var(--c-border);border-radius:10px;padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:16px">Nova escola</div>
        <div class="hd-grid-2" style="margin-bottom:12px">
          <div class="hd-field">
            <label class="hd-label">Nome</label>
            <input class="hd-input" v-model="newSchool.name" placeholder="Escola Eça de Queirós" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Nome curto</label>
            <input class="hd-input" v-model="newSchool.short_name" placeholder="Eça" />
          </div>
        </div>
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Morada</label>
          <input class="hd-input" v-model="newSchool.address" placeholder="Morada da escola" />
        </div>
        <div class="hd-row" style="gap:8px;justify-content:flex-end">
          <button class="hd-btn hd-btn-outline" @click="showNewSchool = false">Cancelar</button>
          <button class="hd-btn hd-btn-primary" @click="createSchool" :disabled="!newSchool.name || !newSchool.short_name">
            Criar escola
          </button>
        </div>
      </div>
    </div>

    <!-- LDAP -->
    <div v-if="tab === 'ldap'" class="hd-card" style="padding:28px;max-width:640px">
      <div class="hd-row" style="margin-bottom:20px">
        <div style="font-weight:600;font-size:15px">Configuração LDAP / Active Directory</div>
        <div class="hd-spacer"></div>
        <label class="hd-row" style="gap:8px;cursor:pointer;font-size:13px">
          <div class="hd-toggle-wrap" @click="ldap.enabled = !ldap.enabled">
            <div class="hd-toggle" :class="{ active: ldap.enabled }"></div>
          </div>
          {{ ldap.enabled ? 'Ativo' : 'Inativo' }}
        </label>
      </div>

      <div :style="{ opacity: ldap.enabled ? 1 : 0.5, pointerEvents: ldap.enabled ? 'auto' : 'none' }">
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Servidor LDAP</label>
          <input class="hd-input" v-model="ldap.server" placeholder="ldaps://dc.escola.local" />
        </div>
        <div class="hd-grid-2" style="margin-bottom:16px">
          <div class="hd-field">
            <label class="hd-label">Porta</label>
            <input class="hd-input" type="number" v-model="ldap.port" placeholder="636" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Protocolo</label>
            <select class="hd-select" v-model="ldap.tls">
              <option value="ldaps">LDAPS (recomendado)</option>
              <option value="ldap">LDAP + STARTTLS</option>
              <option value="plain">LDAP simples</option>
            </select>
          </div>
        </div>
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Bind DN (conta de serviço)</label>
          <input class="hd-input" v-model="ldap.bind_dn" placeholder="cn=svc_tickets,ou=ServiceAccounts,dc=escola,dc=local" />
        </div>
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Palavra-passe</label>
          <input class="hd-input" type="password" v-model="ldap.bind_password" placeholder="••••••••" />
        </div>
        <div class="hd-field" style="margin-bottom:16px">
          <label class="hd-label">Base DN</label>
          <input class="hd-input" v-model="ldap.base_dn" placeholder="ou=Staff,dc=escola,dc=local" />
        </div>
        <div class="hd-field" style="margin-bottom:24px">
          <label class="hd-label">Grupo de administradores (DN)</label>
          <input class="hd-input" v-model="ldap.admin_group" placeholder="CN=TI-Suporte,ou=Groups,dc=escola,dc=local" />
          <p class="hd-hint">Membros deste grupo recebem automaticamente o papel de Administrador.</p>
        </div>
        <div class="hd-row" style="gap:10px">
          <button class="hd-btn hd-btn-outline" @click="testLdap" :disabled="testing">
            <span class="material-icons" style="font-size:16px">cable</span>
            {{ testing ? 'A testar...' : 'Testar ligação' }}
          </button>
          <span v-if="ldapTestResult" :style="{ color: ldapTestOk ? '#22C55E' : '#EF4444', fontSize: '13px' }">
            {{ ldapTestResult }}
          </span>
          <div class="hd-spacer"></div>
          <button class="hd-btn hd-btn-primary" @click="saved = true">
            <span class="material-icons" style="font-size:16px">save</span> Guardar
          </button>
        </div>
      </div>
    </div>

    <!-- Email / notifications -->
    <div v-if="tab === 'email'" class="hd-card" style="padding:28px;max-width:640px">
      <div style="font-weight:600;font-size:15px;margin-bottom:20px">Configuração de email</div>
      <div class="hd-grid-2" style="margin-bottom:16px">
        <div class="hd-field">
          <label class="hd-label">Servidor SMTP</label>
          <input class="hd-input" v-model="email.server" placeholder="smtp.escola.local" />
        </div>
        <div class="hd-field">
          <label class="hd-label">Porta</label>
          <input class="hd-input" type="number" v-model="email.port" placeholder="587" />
        </div>
      </div>
      <div class="hd-field" style="margin-bottom:16px">
        <label class="hd-label">Endereço remetente</label>
        <input class="hd-input" v-model="email.from" placeholder="tickets@escola.local" />
      </div>
      <div class="hd-field" style="margin-bottom:16px">
        <label class="hd-label">Utilizador SMTP</label>
        <input class="hd-input" v-model="email.username" />
      </div>
      <div class="hd-field" style="margin-bottom:24px">
        <label class="hd-label">Palavra-passe SMTP</label>
        <input class="hd-input" type="password" v-model="email.password" placeholder="••••••••" />
      </div>

      <div style="border-top:1px solid var(--c-border);padding-top:20px;margin-bottom:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:12px">Notificações automáticas</div>
        <div style="display:flex;flex-direction:column;gap:12px">
          <div v-for="n in notifications" :key="n.key" class="hd-row" style="justify-content:space-between">
            <div>
              <div style="font-size:13px;font-weight:500">{{ n.label }}</div>
              <div style="font-size:12px;color:var(--c-muted)">{{ n.desc }}</div>
            </div>
            <div class="hd-toggle-wrap" @click="n.enabled = !n.enabled">
              <div class="hd-toggle" :class="{ active: n.enabled }"></div>
            </div>
          </div>
        </div>
      </div>
      <button class="hd-btn hd-btn-primary" @click="saved = true">
        <span class="material-icons" style="font-size:16px">save</span> Guardar
      </button>
      <span v-if="saved" style="margin-left:12px;font-size:13px;color:#22C55E">Guardado!</span>
    </div>

    <!-- Categories -->
    <div v-if="tab === 'categories'" class="hd-card" style="padding:28px;max-width:980px">
      <div class="hd-row" style="margin-bottom:20px">
        <div style="font-weight:600;font-size:15px">Categorias e SLAs</div>
        <div class="hd-spacer"></div>
        <button class="hd-btn hd-btn-primary" style="font-size:12px;padding:6px 14px" @click="showNewCat = true">
          <span class="material-icons" style="font-size:14px">add</span> Nova categoria
        </button>
      </div>
      <div v-if="loadingCats" style="color:var(--c-muted)">A carregar...</div>
      <table v-else class="hd-table">
        <thead><tr><th>ÍCONE</th><th>NOME</th><th>DESCRIÇÃO</th><th>EMAIL</th><th>SLA</th><th></th></tr></thead>
        <tbody>
          <tr v-for="cat in categories" :key="cat.id">
            <td>
              <div style="width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center"
                :style="{ background: cat.color + '22' }">
                <span class="material-icons" :style="{ color: cat.color, fontSize: '16px' }">{{ cat.icon }}</span>
              </div>
            </td>
            <td style="font-weight:500">{{ cat.name }}</td>
            <td style="font-size:12px;color:var(--c-muted)">{{ cat.description }}</td>
            <td style="min-width:220px">
              <input
                class="hd-input"
                style="padding:5px 8px;font-size:12px"
                v-model="cat.email_to"
                placeholder="email@escola.pt"
                @change="saveCategoryEmail(cat)"
              />
            </td>
            <td style="font-weight:600">{{ cat.sla_hours }}h</td>
            <td>
              <button class="hd-icon-btn" @click="deleteCategory(cat.id)" title="Eliminar">
                <span class="material-icons" style="font-size:15px;color:#EF4444">delete</span>
              </button>
            </td>
          </tr>
          <tr v-if="!categories.length">
            <td colspan="6" style="text-align:center;color:var(--c-muted);padding:32px">Sem categorias.</td>
          </tr>
        </tbody>
      </table>

      <!-- New category form -->
      <div v-if="showNewCat" style="margin-top:20px;border:1px solid var(--c-border);border-radius:10px;padding:20px">
        <div style="font-weight:600;font-size:14px;margin-bottom:16px">Nova categoria</div>
        <div class="hd-grid-2" style="margin-bottom:12px">
          <div class="hd-field">
            <label class="hd-label">Nome</label>
            <input class="hd-input" v-model="newCat.name" placeholder="Ex: Equipamento TI" />
          </div>
          <div class="hd-field">
            <label class="hd-label">SLA (horas)</label>
            <input class="hd-input" type="number" v-model="newCat.sla_hours" placeholder="24" />
          </div>
        </div>
        <div class="hd-field" style="margin-bottom:12px">
          <label class="hd-label">Descrição</label>
          <input class="hd-input" v-model="newCat.description" placeholder="Breve descrição da categoria" />
        </div>
        <div class="hd-field" style="margin-bottom:12px">
          <label class="hd-label">Email de notificação</label>
          <input class="hd-input" v-model="newCat.email_to" placeholder="ex: inovar@escola.pt" />
        </div>
        <div class="hd-grid-2" style="margin-bottom:16px">
          <div class="hd-field">
            <label class="hd-label">Ícone Material Icons</label>
            <input class="hd-input" v-model="newCat.icon" placeholder="computer" />
          </div>
          <div class="hd-field">
            <label class="hd-label">Cor (hex)</label>
            <div class="hd-row" style="gap:8px">
              <input class="hd-input" v-model="newCat.color" placeholder="#3D52D5" style="flex:1" />
              <input type="color" v-model="newCat.color" style="width:40px;height:36px;border:none;background:none;cursor:pointer" />
            </div>
          </div>
        </div>
        <div class="hd-row" style="gap:8px;justify-content:flex-end">
          <button class="hd-btn hd-btn-outline" @click="showNewCat = false">Cancelar</button>
          <button class="hd-btn hd-btn-primary" @click="createCat" :disabled="!newCat.name">
            Criar categoria
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { createCategory, createSchool as apiCreateSchool, deleteCategory as apiDeleteCategory, deleteSchool as apiDeleteSchool, getCategories, getSchools, updateCategory as apiUpdateCategory } from '../../api/tickets'
import { getPublicSettings, updateSettings } from '../../api/settings'

const tab = ref<'general' | 'ldap' | 'email' | 'categories' | 'schools'>('general')
const saved = ref(false)
const testing = ref(false)
const ldapTestResult = ref('')
const ldapTestOk = ref(false)
const showNewCat = ref(false)
const showNewSchool = ref(false)
const loadingCats = ref(false)
const loadingSchools = ref(false)
const categories = ref<any[]>([])
const schools = ref<any[]>([])
const logoFile = ref<File | null>(null)

const general = ref({ org_name: '', logo_url: '', app_url: '', timezone: 'Europe/Lisbon', jwt_expire: 480 })
const ldap = ref({ enabled: true, server: '', port: 636, tls: 'ldaps', bind_dn: '', bind_password: '', base_dn: '', admin_group: '' })
const email = ref({ server: '', port: 587, from: '', username: '', password: '' })

const notifications = ref([
  { key: 'ticket_created', label: 'Ticket criado', desc: 'Notifica o solicitante quando o ticket é aberto', enabled: true },
  { key: 'ticket_assigned', label: 'Ticket atribuído', desc: 'Notifica o técnico quando lhe é atribuído um ticket', enabled: true },
  { key: 'ticket_updated', label: 'Ticket atualizado', desc: 'Notifica quando o estado muda', enabled: true },
  { key: 'ticket_resolved', label: 'Ticket resolvido', desc: 'Notifica o solicitante quando o ticket é resolvido', enabled: true },
])

const newCat = ref({ name: '', description: '', email_to: '', icon: 'help', color: '#3D52D5', sla_hours: 24 })
const newSchool = ref({ name: '', short_name: '', address: '' })

onMounted(async () => {
  loadingCats.value = true
  loadingSchools.value = true
  try {
    const [settings, cats, schs] = await Promise.all([getPublicSettings(), getCategories(), getSchools()])
    general.value.org_name = settings.org_name
    general.value.logo_url = settings.logo_url
    categories.value = cats
    schools.value = schs
  } finally {
    loadingCats.value = false
    loadingSchools.value = false
  }
})

function onLogoPicked(event: Event) {
  const input = event.target as HTMLInputElement
  logoFile.value = input.files?.[0] ?? null
}

async function saveGeneral() {
  try {
    const settings = await updateSettings({ org_name: general.value.org_name, logo: logoFile.value })
    general.value.org_name = settings.org_name
    general.value.logo_url = settings.logo_url
    logoFile.value = null
    saved.value = true
  } catch { /* ignore */ }
}

async function testLdap() {
  testing.value = true
  ldapTestResult.value = ''
  await new Promise(r => setTimeout(r, 1200))
  ldapTestOk.value = false
  ldapTestResult.value = 'Configure o servidor no .env e reinicie o backend para testar.'
  testing.value = false
}

async function createCat() {
  try {
    const cat = await createCategory({ ...newCat.value })
    categories.value.push(cat)
    showNewCat.value = false
    newCat.value = { name: '', description: '', email_to: '', icon: 'help', color: '#3D52D5', sla_hours: 24 }
  } catch { /* ignore */ }
}

async function saveCategoryEmail(cat: any) {
  try {
    const updated = await apiUpdateCategory(cat.id, { email_to: cat.email_to || '' })
    const idx = categories.value.findIndex(c => c.id === cat.id)
    if (idx !== -1) categories.value[idx] = { ...categories.value[idx], ...updated }
  } catch { /* ignore */ }
}

async function deleteCategory(id: number) {
  if (!confirm('Eliminar esta categoria?')) return
  try {
    await apiDeleteCategory(id)
    categories.value = categories.value.filter(c => c.id !== id)
  } catch { /* ignore */ }
}

async function createSchool() {
  try {
    const school = await apiCreateSchool({ ...newSchool.value })
    schools.value.push(school)
    showNewSchool.value = false
    newSchool.value = { name: '', short_name: '', address: '' }
  } catch { /* ignore */ }
}

async function deleteSchool(id: number) {
  if (!confirm('Eliminar esta escola?')) return
  try {
    await apiDeleteSchool(id)
    schools.value = schools.value.filter(s => s.id !== id)
  } catch { /* ignore */ }
}
</script>
