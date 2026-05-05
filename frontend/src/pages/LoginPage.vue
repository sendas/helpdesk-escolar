<template>
  <div class="hd-login-wrap">
    <!-- Left panel -->
    <div class="hd-login-left">
      <!-- Logo -->
      <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:auto">
        <img v-if="settings.logo_url" :src="settings.logo_url" alt="" style="width:42px;height:42px;object-fit:contain;border-radius:8px" />
        <div v-else class="hd-sidebar-logo-icon" style="width:42px;height:42px;border-radius:10px"></div>
        <div>
          <div style="font-weight:600;font-size:14px;line-height:1.3">{{ settings.org_name }}</div>
          <div style="font-size:12px;color:var(--c-muted);margin-top:2px">Sistema de Helpdesk</div>
        </div>
      </div>

      <!-- Main content -->
      <div style="margin:auto 0;padding:48px 0 32px">
        <h1 style="font-size:36px;font-weight:500;line-height:1.15;margin-bottom:12px">Bem-vindo<br>de volta.</h1>
        <p style="color:var(--c-muted);font-size:14px;margin-bottom:32px;line-height:1.5">
          Entre com a sua conta institucional para<br>abrir e gerir pedidos de apoio.
        </p>

        <div v-if="error" style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px 14px;font-size:13px;color:#DC2626;margin-bottom:16px">
          {{ error }}
        </div>

        <!-- Microsoft Login button -->
        <button class="hd-btn hd-btn-dark hd-btn-lg" style="width:100%;justify-content:center;gap:10px" :disabled="loading" @click="onMicrosoftLogin">
          <span class="material-icons" style="font-size:18px">account_circle</span>
          Entrar com Microsoft
        </button>
        <p style="text-align:center;font-size:12px;color:var(--c-muted);margin-top:10px">
          Autenticação via Microsoft Entra ID
        </p>

        <template v-if="ldapEnabled">
          <!-- AD Login form -->
          <div style="display:flex;align-items:center;gap:12px;margin:24px 0 16px">
            <div style="height:1px;background:var(--c-border);flex:1"></div>
            <span style="font-size:12px;color:var(--c-muted)">ou Active Directory local</span>
            <div style="height:1px;background:var(--c-border);flex:1"></div>
          </div>
          <div style="display:flex;flex-direction:column;gap:10px">
            <input
              class="hd-input"
              v-model="username"
              autocomplete="username"
              placeholder="Utilizador do domínio"
              @keyup.enter="onAdLogin"
            />
            <input
              class="hd-input"
              v-model="password"
              type="password"
              autocomplete="current-password"
              placeholder="Palavra-passe"
              @keyup.enter="onAdLogin"
            />
          </div>
          <button class="hd-btn hd-btn-dark hd-btn-lg" style="width:100%;justify-content:center;gap:10px;margin-top:12px" :disabled="loading || !username || !password" @click="onAdLogin">
            <span class="material-icons" style="font-size:18px">shield</span>
            {{ loading ? 'A autenticar...' : 'Entrar com a conta da escola' }}
          </button>
          <p style="text-align:center;font-size:12px;color:var(--c-muted);margin-top:10px">
            Autenticação via Active Directory/LDAP
          </p>
        </template>

        <!-- Demo mode -->
        <div style="margin-top:32px;padding:16px;border:1px solid var(--c-border);border-radius:12px">
          <div style="display:flex;gap:0;border:1px solid var(--c-border);border-radius:8px;overflow:hidden;margin-bottom:10px">
            <button
              v-for="p in demoProfiles"
              :key="p.role"
              :style="{ background: demoRole === p.role ? 'var(--c-text)' : 'transparent', color: demoRole === p.role ? 'var(--c-surface)' : 'var(--c-muted)', flex: 1, border: 'none', padding: '7px 0', font: '600 12.5px Inter, sans-serif', cursor: 'pointer', transition: 'all .15s' }"
              @click="demoRole = p.role"
            >{{ p.label }}</button>
          </div>
          <p style="font-size:12px;color:var(--c-muted);text-align:center;margin:0 0 10px">
            Modo de demonstração — selecione o perfil para experimentar
          </p>
          <button class="hd-btn hd-btn-outline" style="width:100%;justify-content:center" @click="onDemoLogin">
            Entrar em modo demo
          </button>
        </div>
      </div>

      <!-- Footer -->
      <p style="font-size:11.5px;color:var(--c-muted);margin-top:auto">
        © 2026 Agrupamento de Escolas Eça de Queirós · Apoio: helpdesk@escola.pt
      </p>
    </div>

    <!-- Right panel -->
    <div class="hd-login-right">
      <div style="background:var(--c-surface);border:1px solid var(--c-border);border-radius:16px;padding:20px 24px;width:72px;margin-bottom:40px;box-shadow:var(--shadow-sm)">
        <div style="height:10px;background:var(--c-border);border-radius:4px;margin-bottom:8px"></div>
        <div style="height:10px;background:var(--c-border);border-radius:4px;width:60%"></div>
      </div>
      <h2 style="font-size:30px;line-height:1.25;color:var(--c-text);margin-bottom:16px">
        Um sistema simples para que o tempo dos docentes seja gasto com os alunos — não com pedidos perdidos.
      </h2>
      <p style="color:var(--c-muted);font-size:13px;margin-bottom:40px">— Direção Pedagógica</p>
      <ul style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:16px">
        <li v-for="f in features" :key="f.title" style="display:flex;align-items:flex-start;gap:12px">
          <div style="width:22px;height:22px;background:var(--c-primary);border-radius:6px;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:1px">
            <span class="material-icons" style="font-size:13px;color:#fff">check</span>
          </div>
          <div>
            <div style="font-weight:600;font-size:13.5px">{{ f.title }}</div>
            <div style="font-size:12px;color:var(--c-muted);margin-top:2px">{{ f.sub }}</div>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { getPublicSettings } from '../api/settings'

const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const username = ref('')
const password = ref('')
const demoRole = ref('teacher')
const ldapEnabled = import.meta.env.VITE_LDAP_ENABLED === 'true'
const settings = ref({ org_name: 'Agrupamento de Escolas Eça de Queirós', logo_url: '' })

const demoProfiles = [
  { role: 'teacher', label: 'Docente' },
  { role: 'technician', label: 'Técnico' },
  { role: 'admin', label: 'Administrador' },
]

const features = [
  { title: 'Aberto → Atribuído → Em Curso → Resolvido', sub: 'Estados claros e auditáveis' },
  { title: 'Integração com Microsoft Entra ID', sub: 'Login institucional com a conta Microsoft' },
  { title: 'Notificações e SLAs configuráveis', sub: 'Cada categoria com o seu prazo' },
]

onMounted(async () => {
  localStorage.setItem('dark', '0')
  document.documentElement.classList.remove('dark')
  try { settings.value = await getPublicSettings() }
  catch { /* ignore */ }
})

function onMicrosoftLogin() {
  error.value = ''
  auth.loginAzure()
}

async function onAdLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.loginLdap(username.value.trim(), password.value)
  } catch (e: any) {
    error.value = e?.code === 'ECONNABORTED'
      ? 'Tempo de autenticação esgotado. Verifique a ligação ao Active Directory.'
      : e?.response?.data?.detail || 'Erro de autenticação'
  } finally {
    loading.value = false
  }
}

async function onDemoLogin() {
  loading.value = true
  error.value = ''
  try {
    await auth.loginDemo(demoRole.value)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || 'Erro de autenticação'
  } finally {
    loading.value = false
  }
}
</script>
