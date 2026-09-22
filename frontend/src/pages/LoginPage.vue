<template>
  <div class="hd-login-wrap">
    <!-- Left panel -->
    <div class="hd-login-left">
      <!-- Logo -->
      <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:auto">
        <img v-if="settings.logo_url" :src="settings.logo_url" alt="" style="width:64px;height:48px;object-fit:contain;border-radius:8px" />
        <div v-else class="hd-sidebar-logo-icon" style="width:56px;height:48px;border-radius:10px"></div>
        <div>
          <div style="font-weight:600;font-size:14px;line-height:1.3">{{ settings.org_name }}</div>
          <div style="font-size:12px;color:var(--c-muted);margin-top:2px">Sistema de Helpdesk</div>
        </div>
      </div>

      <!-- Main content -->
      <div style="margin:auto 0;padding:26px 0 18px">
        <h1 style="font-size:30px;font-weight:500;line-height:1.1;margin-bottom:10px">Centro de Apoio Digital<br>do Agrupamento</h1>
        <p style="color:var(--c-muted);font-size:13px;margin-bottom:18px;line-height:1.45">
          Entre com a sua conta institucional para<br>abrir e gerir pedidos de apoio.
        </p>
        <div style="border:1px solid var(--c-border);border-radius:10px;padding:10px 12px;margin-bottom:14px;background:var(--c-surface);font-size:12px;color:var(--c-muted);line-height:1.4">
          <strong style="display:block;color:var(--c-text);margin-bottom:4px">Instruções de acesso</strong>
          A autenticação deve ser feita com as mesmas credenciais de acesso ao mail institucional.
          O ecrã de entrada abre sempre em modo claro; se preferir, pode ativar modo escuro abaixo.
        </div>

        <div class="login-theme-choice">
          <span>Modo escuro</span>
          <div class="login-theme-toggle" role="group" aria-label="Escolher modo escuro no login">
            <button type="button" :class="{ selected: !loginDark }" @click="setLoginDark(false)">Não</button>
            <button type="button" :class="{ selected: loginDark }" @click="setLoginDark(true)">Sim</button>
          </div>
        </div>

        <div v-if="error" style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px 14px;font-size:13px;color:#DC2626;margin-bottom:16px">
          {{ error }}
        </div>

        <!-- Microsoft Login button -->
        <button class="hd-btn hd-btn-dark hd-btn-lg" style="width:100%;justify-content:center;gap:10px" :disabled="loading" @click="onMicrosoftLogin">
          <span class="material-icons" style="font-size:18px">account_circle</span>
          Entrar com email ou conta da escola
        </button>
        <p style="text-align:center;font-size:12px;color:var(--c-muted);margin-top:10px">
          Autenticação via Microsoft Entra ID
        </p>

        <button
          v-if="!showLocalLogin"
          class="hd-link-btn"
          type="button"
          @click="showLocalLogin = true"
        >
          Entrar com conta local
        </button>
        <template v-if="showLocalLogin">
          <!-- Local Login form -->
          <div style="display:flex;align-items:center;gap:12px;margin:18px 0 14px">
            <div style="height:1px;background:var(--c-border);flex:1"></div>
            <span style="font-size:12px;color:var(--c-muted)">conta local</span>
            <div style="height:1px;background:var(--c-border);flex:1"></div>
          </div>
          <div style="display:flex;flex-direction:column;gap:10px">
            <input
              class="hd-input"
              v-model="username"
              autocomplete="username"
              placeholder="Email ou utilizador"
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
            {{ loading ? 'A autenticar...' : 'Entrar com conta local' }}
          </button>
          <p style="text-align:center;font-size:12px;color:var(--c-muted);margin-top:10px">
            Autenticação com conta criada pelo administrador
          </p>
        </template>

        <button class="hd-btn hd-btn-sm no-access-btn" type="button" style="width:100%;justify-content:center;gap:8px;margin-top:14px" @click="openContactForm">
          <span class="material-icons" style="font-size:15px">help_outline</span>
          Não tenho acesso ao mail institucional
        </button>
      </div>

      <!-- Footer -->
      <p style="font-size:11.5px;color:var(--c-muted);margin-top:auto">
        {{ versionLabelText }} · © 2026 Agrupamento de Escolas Eça de Queirós
      </p>
    </div>

    <!-- Right panel -->
    <div class="hd-login-right">
      <div style="margin-bottom:24px">
        <div style="font-size:22px;font-weight:600;color:var(--c-text);line-height:1.2;margin-bottom:4px">Agrupamento de Escolas<br>Eça de Queirós</div>
        <a href="https://www.queiroz.pt" target="_blank" rel="noopener" style="font-size:13px;color:var(--c-primary);text-decoration:none;opacity:.85">www.queiroz.pt</a>
      </div>
      <h2 style="font-size:22px;line-height:1.3;color:var(--c-text);margin-bottom:10px">
        Um sistema simples para que o tempo dos docentes seja gasto com os alunos — não com pedidos perdidos.
      </h2>
      <p style="color:var(--c-muted);font-size:13px;margin-bottom:24px">— Direção Pedagógica</p>
      <ul style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:12px">
        <li v-for="f in features" :key="f.title" style="display:flex;align-items:flex-start;gap:12px">
          <div :style="{ width:'22px', height:'22px', background: f.color, borderRadius:'6px', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, marginTop:'1px' }">
            <span class="material-icons" style="font-size:13px;color:#fff">{{ f.icon }}</span>
          </div>
          <div>
            <div style="font-weight:600;font-size:13.5px">{{ f.title }}</div>
            <div style="font-size:12px;color:var(--c-muted);margin-top:2px">{{ f.sub }}</div>
          </div>
        </li>
      </ul>
    </div>

    <!-- Login notice modal -->
    <div v-if="showNotice" class="modal-backdrop" @click.self="showNotice = false">
      <div class="modal-card hd-card">
        <div class="modal-head">
          <div style="font-weight:700;font-size:16px;display:flex;align-items:center;gap:8px">
            <span class="material-icons" style="font-size:20px;color:var(--c-primary)">info</span>
            Aviso
          </div>
          <button class="hd-icon-btn" @click="showNotice = false" title="Fechar">
            <span class="material-icons">close</span>
          </button>
        </div>
        <p style="font-size:13.5px;line-height:1.6;color:var(--c-text);white-space:pre-line">{{ loginNoticeText }}</p>
        <div class="modal-actions">
          <button class="hd-btn hd-btn-primary" @click="showNotice = false">Entendi</button>
        </div>
      </div>
    </div>

    <!-- No institutional access contact form modal -->
    <div v-if="showContactForm" class="modal-backdrop" @click.self="closeContactForm">
      <div class="modal-card hd-card">
        <div class="modal-head">
          <div style="font-weight:700;font-size:16px;display:flex;align-items:center;gap:8px">
            <span class="material-icons" style="font-size:20px;color:var(--c-primary)">mail</span>
            Não tenho acesso ao mail institucional
          </div>
          <button class="hd-icon-btn" @click="closeContactForm" title="Fechar">
            <span class="material-icons">close</span>
          </button>
        </div>

        <template v-if="contactSent">
          <p style="font-size:13.5px;line-height:1.6;color:var(--c-text)">
            <span class="material-icons" style="font-size:18px;color:#22C55E;vertical-align:-3px;margin-right:4px">check_circle</span>
            Mensagem enviada. Vamos entrar em contacto assim que possível.
          </p>
          <div class="modal-actions">
            <button class="hd-btn hd-btn-primary" @click="closeContactForm">Fechar</button>
          </div>
        </template>
        <template v-else>
          <p style="font-size:12.5px;color:var(--c-muted);margin:0 0 14px;line-height:1.5">
            Preencha os seus dados para entrarmos em contacto por outra via.
          </p>
          <div v-if="contactError" style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:10px 14px;font-size:13px;color:#DC2626;margin-bottom:14px">
            {{ contactError }}
          </div>
          <div style="display:flex;flex-direction:column;gap:10px">
            <input class="hd-input" v-model="contactForm.name" placeholder="Nome do docente" />
            <input class="hd-input" v-model="contactForm.recruitment_group" placeholder="Grupo de recrutamento (ex: 550)" />
            <input class="hd-input" v-model="contactForm.school" placeholder="Escola onde leciona" />
            <textarea class="hd-textarea" v-model="contactForm.message" rows="4" placeholder="Mensagem"></textarea>
          </div>
          <div class="modal-actions">
            <button class="hd-btn hd-btn-outline" @click="closeContactForm">Cancelar</button>
            <button class="hd-btn hd-btn-primary" :disabled="contactSending || !contactForm.name.trim() || !contactForm.message.trim()" @click="submitContactForm">
              <span class="material-icons" style="font-size:16px">{{ contactSending ? 'hourglass_empty' : 'send' }}</span>
              {{ contactSending ? 'A enviar...' : 'Enviar' }}
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { getPublicSettings } from '../api/settings'
import { sendNoAccessContact } from '../api/auth'
import { applyFavicon } from '../utils/branding'
import { versionLabel } from '../utils/version'

const auth = useAuthStore()
const loading = ref(false)
const error = ref('')
const username = ref('')
const password = ref('')
const showLocalLogin = ref(false)
const loginDark = ref(false)
const settings = ref({ org_name: 'Agrupamento de Escolas Eça de Queirós', logo_url: '', favicon_url: '' })
const versionLabelText = versionLabel()
const showNotice = ref(false)
const loginNoticeText = ref('')

const showContactForm = ref(false)
const contactSending = ref(false)
const contactSent = ref(false)
const contactError = ref('')
const contactForm = ref({ name: '', recruitment_group: '', school: '', message: '' })

const features = [
  { title: 'Aberto → Atribuído → Em Curso → Resolvido', sub: 'Estados claros e auditáveis', color: '#0D9488', icon: 'task_alt' },
  { title: 'Integração com Microsoft Entra ID', sub: 'Login institucional com a conta Microsoft', color: '#0078D4', icon: 'shield' },
  { title: 'Notificações e tempos de resposta configuráveis', sub: 'Cada categoria com o seu prazo', color: '#D97706', icon: 'notifications_active' },
]

onMounted(async () => {
  setLoginDark(false)
  try {
    const s = await getPublicSettings()
    settings.value = s
    applyFavicon(settings.value.favicon_url || settings.value.logo_url)
    if (s.login_notice_enabled && s.login_notice_text) {
      loginNoticeText.value = s.login_notice_text
      showNotice.value = true
    }
  }
  catch { /* ignore */ }
})

function setLoginDark(enabled: boolean) {
  loginDark.value = enabled
  localStorage.setItem('dark', enabled ? '1' : '0')
  document.documentElement.classList.toggle('dark', enabled)
}

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
      ? 'Tempo de autenticação esgotado. Tente novamente.'
      : e?.response?.data?.detail || 'Erro de autenticação'
  } finally {
    loading.value = false
  }
}

function openContactForm() {
  contactSent.value = false
  contactError.value = ''
  contactForm.value = { name: '', recruitment_group: '', school: '', message: '' }
  showContactForm.value = true
}

function closeContactForm() {
  showContactForm.value = false
}

async function submitContactForm() {
  if (contactSending.value) return
  contactSending.value = true
  contactError.value = ''
  try {
    await sendNoAccessContact({
      name: contactForm.value.name.trim(),
      recruitment_group: contactForm.value.recruitment_group.trim(),
      school: contactForm.value.school.trim(),
      message: contactForm.value.message.trim(),
    })
    contactSent.value = true
  } catch (e: any) {
    contactError.value = e?.response?.data?.detail || 'Não foi possível enviar a mensagem. Tente novamente.'
  } finally {
    contactSending.value = false
  }
}
</script>

<style scoped>
.no-access-btn {
  background: var(--c-accent);
  color: #fff;
}
.no-access-btn .material-icons { color: #fff; }

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.50);
  display: grid;
  place-items: center;
  padding: 20px;
}

.modal-card {
  width: min(480px, 100%);
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  border-radius: 14px;
  padding: 24px;
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 16px;
  border-top: 1px solid var(--c-border);
}

.login-theme-choice {
  align-items: center;
  border: 1px solid var(--c-border);
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
  padding: 8px 10px;
}

.login-theme-choice > span {
  color: var(--c-text);
  font-size: 12.5px;
  font-weight: 700;
}

.login-theme-toggle {
  background: var(--c-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  display: inline-flex;
  overflow: hidden;
}

.login-theme-toggle button {
  background: transparent;
  border: 0;
  color: var(--c-muted);
  cursor: pointer;
  font: 700 12px var(--font-sans);
  min-width: 54px;
  padding: 7px 10px;
}

.login-theme-toggle button.selected {
  background: var(--c-text);
  color: var(--c-surface);
}

@media (max-width: 640px) {
  .login-theme-choice {
    align-items: stretch;
    flex-direction: column;
    gap: 8px;
  }

  .login-theme-toggle {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}
</style>
