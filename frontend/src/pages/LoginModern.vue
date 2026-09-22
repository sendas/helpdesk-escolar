<template>
  <div class="lg-wrap hd-login-wrap">
    <div class="lg-bg-blob lg-bg-blob-1"></div>
    <div class="lg-bg-blob lg-bg-blob-2"></div>

    <!-- Left: form -->
    <main class="lg-left">
      <div class="lg-brand">
        <img v-if="settings.logo_url" :src="settings.logo_url" alt="" class="lg-logo" />
        <div v-else class="lg-logo lg-logo-fallback"><span class="material-icons">support_agent</span></div>
        <div>
          <div class="lg-org">{{ settings.org_name }}</div>
          <div class="lg-org-sub">Sistema de Helpdesk</div>
        </div>
      </div>

      <div class="lg-form">
        <div class="lg-badge"><span class="material-icons">waving_hand</span> Bem-vindo</div>
        <h1 class="lg-title">Centro de Apoio <span class="lg-title-accent">Digital</span> do Agrupamento</h1>
        <p class="lg-sub">Entre com a sua conta institucional para abrir e acompanhar pedidos de apoio.</p>

        <div class="lg-info">
          <span class="material-icons">info</span>
          <div>
            <strong>Instruções de acesso</strong>
            Use as mesmas credenciais do mail institucional.
          </div>
        </div>

        <div v-if="error" class="lg-error">{{ error }}</div>

        <button class="lg-btn-main" :disabled="loading" @click="onMicrosoftLogin">
          <span class="lg-ms-logo" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
          Entrar com email ou conta da escola
        </button>
        <p class="lg-hint">Autenticação segura via Microsoft Entra ID</p>

        <button v-if="!showLocalLogin" class="lg-link" type="button" @click="showLocalLogin = true">
          Entrar com conta local
        </button>
        <template v-if="showLocalLogin">
          <div class="lg-divider"><span>conta local</span></div>
          <div class="lg-fields">
            <input class="hd-input" v-model="username" autocomplete="username" placeholder="Email ou utilizador" @keyup.enter="onAdLogin" />
            <input class="hd-input" v-model="password" type="password" autocomplete="current-password" placeholder="Palavra-passe" @keyup.enter="onAdLogin" />
          </div>
          <button class="lg-btn-local" :disabled="loading || !username || !password" @click="onAdLogin">
            <span class="material-icons">shield</span>
            {{ loading ? 'A autenticar...' : 'Entrar com conta local' }}
          </button>
          <p class="lg-hint">Autenticação com conta criada pelo administrador</p>
        </template>

        <button class="lg-btn-help" type="button" @click="openContactForm">
          <span class="material-icons">help_outline</span>
          Não tenho acesso ao mail institucional
        </button>

        <div class="lg-theme">
          <span class="material-icons">dark_mode</span>
          <span class="lg-theme-label">Modo escuro</span>
          <div class="lg-theme-toggle" role="group" aria-label="Escolher modo escuro no login">
            <button type="button" :class="{ selected: !loginDark }" @click="setLoginDark(false)">Não</button>
            <button type="button" :class="{ selected: loginDark }" @click="setLoginDark(true)">Sim</button>
          </div>
        </div>
      </div>

      <p class="lg-footer">{{ versionLabelText }} · © 2026 Agrupamento de Escolas Eça de Queirós</p>
    </main>

    <!-- Right: showcase -->
    <aside class="lg-right">
      <div class="lg-right-blob lg-right-blob-1"></div>
      <div class="lg-right-blob lg-right-blob-2"></div>

      <div class="lg-right-inner">
        <div class="lg-right-org">Agrupamento de Escolas<br>Eça de Queirós</div>
        <a href="https://www.queiroz.pt" target="_blank" rel="noopener" class="lg-right-site">
          www.queiroz.pt <span class="material-icons">open_in_new</span>
        </a>

        <h2 class="lg-quote">“Um sistema simples para que o tempo dos docentes seja gasto com os alunos — não com pedidos perdidos.”</h2>
        <p class="lg-quote-author">— Direção Pedagógica</p>

        <div class="lg-mock" aria-hidden="true">
          <div class="lg-mock-row">
            <span class="lg-mock-dot" style="background:#10B981"></span>
            <div class="lg-mock-text">
              <strong>Projetor da sala 14</strong>
              <small>T-112 · há 10 min</small>
            </div>
            <span class="lg-mock-pill">Resolvido</span>
          </div>
        </div>

        <ul class="lg-features">
          <li v-for="f in features" :key="f.title">
            <div class="lg-feat-icon" :style="{ background: f.color }"><span class="material-icons">{{ f.icon }}</span></div>
            <div>
              <div class="lg-feat-title">{{ f.title }}</div>
              <div class="lg-feat-sub">{{ f.sub }}</div>
            </div>
          </li>
        </ul>
      </div>
    </aside>

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
          <div v-if="contactError" class="lg-error">{{ contactError }}</div>
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
  { title: 'Aberto → Atribuído → Em Curso → Resolvido', sub: 'Estados claros e auditáveis', color: '#10B981', icon: 'task_alt' },
  { title: 'Integração com Microsoft Entra ID', sub: 'Login institucional com a conta Microsoft', color: '#3B82F6', icon: 'shield' },
  { title: 'Notificações e tempos de resposta configuráveis', sub: 'Cada categoria com o seu prazo', color: '#F59E0B', icon: 'notifications_active' },
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
/* ── Page ── */
.lg-wrap {
  position: relative;
  overflow: hidden;
  display: flex;
  min-height: 100vh;
  background: linear-gradient(160deg, #F5F8FF 0%, #EFF6FF 55%, #ECFEFF 100%);
}
.dark .lg-wrap { background: linear-gradient(160deg, #0F1117 0%, #0F172A 60%, #0D1A1C 100%); }

.lg-bg-blob { position: absolute; border-radius: 50%; filter: blur(60px); pointer-events: none; opacity: .55; }
.lg-bg-blob-1 { width: 380px; height: 380px; left: -120px; top: -120px; background: #A5B4FC; }
.lg-bg-blob-2 { width: 320px; height: 320px; left: 25%; bottom: -160px; background: #99F6E4; }
.dark .lg-bg-blob { opacity: .18; }

/* ── Left (form) ── */
.lg-left {
  position: relative;
  z-index: 1;
  width: 46%;
  min-width: 420px;
  display: flex;
  flex-direction: column;
  padding: 28px 56px;
}

.lg-brand { display: flex; align-items: center; gap: 12px; }
.lg-logo { width: 56px; height: 46px; object-fit: contain; border-radius: 10px; }
.lg-logo-fallback {
  display: grid; place-items: center;
  background: linear-gradient(120deg, #2563EB, #0891B2);
}
.lg-logo-fallback .material-icons { color: #fff; font-size: 26px; }
.lg-org { font-weight: 700; font-size: 14px; line-height: 1.3; color: var(--c-text); }
.lg-org-sub { font-size: 12px; color: var(--c-muted); margin-top: 2px; }

.lg-form {
  margin: auto 0;
  padding: 28px 0 20px;
  max-width: 440px;
  width: 100%;
}

.lg-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px; font-weight: 700;
  color: #2563EB;
  background: rgba(37, 99, 235, .1);
  margin-bottom: 14px;
}
.lg-badge .material-icons { font-size: 15px; }
.dark .lg-badge { color: #93C5FD; background: rgba(96, 165, 250, .16); }

.lg-title {
  font-size: 34px;
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: -.01em;
  margin: 0 0 10px;
  color: var(--c-text);
}
.lg-title-accent {
  background: linear-gradient(120deg, #2563EB, #0891B2);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.lg-sub { color: var(--c-muted); font-size: 14px; line-height: 1.5; margin: 0 0 18px; }

.lg-info {
  display: flex; gap: 10px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(59, 130, 246, .08);
  border: 1px solid rgba(59, 130, 246, .2);
  font-size: 12.5px; line-height: 1.45;
  color: var(--c-muted);
  margin-bottom: 18px;
}
.lg-info .material-icons { color: #3B82F6; font-size: 18px; flex-shrink: 0; }
.lg-info strong { display: block; color: var(--c-text); margin-bottom: 2px; }

.lg-error {
  background: #FEF2F2; border: 1px solid #FECACA; border-radius: 10px;
  padding: 10px 14px; font-size: 13px; color: #DC2626; margin-bottom: 14px;
}

.lg-btn-main {
  width: 100%;
  display: flex; align-items: center; justify-content: center; gap: 12px;
  padding: 14px 20px;
  border: 0; border-radius: 14px;
  font: 700 15px var(--font-sans);
  color: #fff;
  cursor: pointer;
  background: linear-gradient(120deg, #2563EB, #0891B2);
  box-shadow: 0 14px 28px rgba(37, 99, 235, .3);
  transition: transform .15s ease, box-shadow .15s ease;
}
.lg-btn-main:hover { transform: translateY(-2px); box-shadow: 0 18px 34px rgba(37, 99, 235, .38); }
.lg-btn-main:disabled { opacity: .6; cursor: not-allowed; transform: none; }

.lg-ms-logo {
  display: grid; grid-template-columns: 1fr 1fr; gap: 2px;
  width: 18px; height: 18px;
  padding: 3px; border-radius: 5px; background: #fff;
  box-sizing: content-box;
}
.lg-ms-logo i { display: block; }
.lg-ms-logo i:nth-child(1) { background: #F25022; }
.lg-ms-logo i:nth-child(2) { background: #7FBA00; }
.lg-ms-logo i:nth-child(3) { background: #00A4EF; }
.lg-ms-logo i:nth-child(4) { background: #FFB900; }

.lg-hint { text-align: center; font-size: 12px; color: var(--c-muted); margin: 10px 0 0; }

.lg-link {
  display: block; margin: 12px auto 0;
  padding: 4px 8px; border: 0; background: transparent;
  color: var(--c-primary); font: 600 12.5px var(--font-sans);
  cursor: pointer; text-decoration: underline; text-underline-offset: 3px;
}

.lg-divider {
  display: flex; align-items: center; gap: 12px;
  margin: 18px 0 14px;
  font-size: 12px; color: var(--c-muted);
}
.lg-divider::before, .lg-divider::after { content: ''; flex: 1; height: 1px; background: var(--c-border); }

.lg-fields { display: flex; flex-direction: column; gap: 10px; }

.lg-btn-local {
  width: 100%;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  margin-top: 12px; padding: 12px 18px;
  border: 0; border-radius: 12px;
  font: 700 14px var(--font-sans);
  color: var(--c-surface); background: var(--c-text);
  cursor: pointer;
}
.lg-btn-local .material-icons { font-size: 18px; }
.lg-btn-local:disabled { opacity: .5; cursor: not-allowed; }

.lg-btn-help {
  width: 100%;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  margin-top: 16px; padding: 9px 14px;
  border: 0; border-radius: 12px;
  font: 700 13px var(--font-sans);
  color: #fff;
  background: linear-gradient(120deg, #14B8A6, #06B6D4);
  box-shadow: 0 10px 20px rgba(20, 184, 166, .25);
  cursor: pointer;
  transition: transform .15s ease;
}
.lg-btn-help:hover { transform: translateY(-1px); }
.lg-btn-help .material-icons { font-size: 17px; }

.lg-theme {
  display: flex; align-items: center; gap: 8px;
  margin-top: 18px; padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid var(--c-border);
  background: color-mix(in srgb, var(--c-surface) 70%, transparent);
}
.lg-theme > .material-icons { font-size: 17px; color: var(--c-muted); }
.lg-theme-label { flex: 1; font-size: 12.5px; font-weight: 700; color: var(--c-text); }
.lg-theme-toggle {
  display: inline-flex; overflow: hidden;
  border-radius: 8px; border: 1px solid var(--c-border); background: var(--c-bg);
}
.lg-theme-toggle button {
  min-width: 52px; padding: 6px 10px;
  border: 0; background: transparent; cursor: pointer;
  font: 700 12px var(--font-sans); color: var(--c-muted);
}
.lg-theme-toggle button.selected { background: var(--c-text); color: var(--c-surface); }

.lg-footer { font-size: 11.5px; color: var(--c-muted); margin: 0; }

/* ── Right (showcase) ── */
.lg-right {
  position: relative;
  flex: 1;
  margin: 16px 16px 16px 0;
  border-radius: 28px;
  overflow: hidden;
  display: flex;
  align-items: center;
  padding: 48px 56px;
  color: #fff;
  background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 50%, #0891B2 100%);
  box-shadow: 0 24px 60px rgba(37, 99, 235, .25);
}
.lg-right-blob { position: absolute; border-radius: 50%; pointer-events: none; }
.lg-right-blob-1 { width: 340px; height: 340px; right: -110px; top: -110px; background: rgba(255, 255, 255, .12); }
.lg-right-blob-2 { width: 260px; height: 260px; left: -80px; bottom: -120px; background: rgba(20, 184, 166, .4); }

.lg-right-inner { position: relative; max-width: 520px; }
.lg-right-org { font-size: 24px; font-weight: 800; line-height: 1.2; margin-bottom: 6px; }
.lg-right-site {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 13px; font-weight: 600; color: rgba(255, 255, 255, .85); text-decoration: none;
}
.lg-right-site .material-icons { font-size: 14px; }
.lg-right-site:hover { color: #fff; }

.lg-quote { font-size: 22px; font-weight: 600; line-height: 1.35; margin: 30px 0 8px; color: #fff; }
.lg-quote-author { font-size: 13px; opacity: .8; margin: 0 0 26px; }

.lg-mock {
  display: inline-block;
  padding: 10px;
  border-radius: 16px;
  background: rgba(255, 255, 255, .14);
  border: 1px solid rgba(255, 255, 255, .25);
  backdrop-filter: blur(6px);
  margin-bottom: 26px;
}
.lg-mock-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px;
  border-radius: 12px;
  background: #fff;
  color: #1E293B;
  box-shadow: 0 10px 24px rgba(15, 23, 42, .2);
}
.lg-mock-dot { width: 10px; height: 10px; border-radius: 50%; box-shadow: 0 0 0 4px rgba(16, 185, 129, .2); }
.lg-mock-text strong { display: block; font-size: 13px; }
.lg-mock-text small { font-size: 11px; color: #64748B; }
.lg-mock-pill {
  margin-left: 18px;
  font-size: 11px; font-weight: 700;
  padding: 3px 10px; border-radius: 999px;
  color: #059669; background: rgba(16, 185, 129, .14);
}

.lg-features { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
.lg-features li {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, .12);
  border: 1px solid rgba(255, 255, 255, .18);
}
.lg-feat-icon {
  width: 34px; height: 34px; border-radius: 10px; flex-shrink: 0;
  display: grid; place-items: center;
  box-shadow: 0 6px 14px rgba(15, 23, 42, .2);
}
.lg-feat-icon .material-icons { font-size: 18px; color: #fff; }
.lg-feat-title { font-size: 13.5px; font-weight: 700; }
.lg-feat-sub { font-size: 12px; opacity: .8; margin-top: 1px; }

/* ── Modals ── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0, 0, 0, 0.50);
  display: grid; place-items: center; padding: 20px;
}
.modal-card { width: min(480px, 100%); max-height: calc(100vh - 40px); overflow-y: auto; border-radius: 16px; padding: 24px; }
.modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.modal-actions {
  display: flex; justify-content: flex-end; gap: 10px;
  padding-top: 16px; margin-top: 16px; border-top: 1px solid var(--c-border);
}

/* ── Responsive ── */
@media (max-width: 1100px) {
  .lg-left { padding: 28px 36px; }
  .lg-right { padding: 40px 36px; }
}

@media (max-width: 860px) {
  .lg-right { display: none; }
  .lg-left { width: 100%; min-width: 0; padding: max(env(safe-area-inset-top, 0px), 24px) 22px 24px; }
  .lg-form { max-width: none; }
  .lg-title { font-size: 28px; }
}
</style>
