<template>
  <div class="app-shell">
    <header class="mobile-topbar">
      <div class="mobile-brand">
        <img v-if="settings.logo_url" class="mobile-logo-img" :src="settings.logo_url" alt="" />
        <div v-else class="mobile-logo-dot"></div>
        <div>
          <div class="mobile-title">{{ settings.org_name }}</div>
          <div class="mobile-subtitle">{{ pageTitle }}</div>
        </div>
      </div>
      <button class="hd-icon-btn" type="button" @click="mobileMenuOpen = !mobileMenuOpen" title="Menu">
        <span class="material-icons">{{ mobileMenuOpen ? 'close' : 'menu' }}</span>
      </button>
    </header>

    <!-- Sidebar -->
    <aside class="hd-sidebar app-sidebar" :class="{ open: mobileMenuOpen }">
      <div class="hd-sidebar-logo">
        <img v-if="settings.logo_url" class="hd-sidebar-logo-img" :src="settings.logo_url" alt="" />
        <div v-else class="hd-sidebar-logo-icon"></div>
        <div class="hd-sidebar-logo-text">
          <div class="hd-sidebar-logo-name">{{ settings.org_name }}</div>
          <div class="hd-sidebar-logo-sub">Helpdesk {{ roleLabel }}</div>
        </div>
      </div>

      <nav class="hd-nav">
        <div class="hd-nav-section">Principal</div>
        <router-link class="hd-nav-item" :class="{ active: $route.path === '/dashboard' }" to="/dashboard" @click="mobileMenuOpen = false">
          <span class="material-icons">home</span> Painel inicial
        </router-link>
        <router-link class="hd-nav-item" :class="{ active: $route.path.startsWith('/tickets') && !$route.path.startsWith('/admin') }" to="/tickets" @click="mobileMenuOpen = false">
          <span class="material-icons">inbox</span> Os meus tickets
          <span v-if="openCount" class="hd-nav-badge">{{ openCount }}</span>
        </router-link>
        <router-link class="hd-nav-item" :class="{ active: $route.path === '/tickets/new' }" to="/tickets/new" @click="mobileMenuOpen = false">
          <span class="material-icons" style="font-size:16px">add_circle</span> Novo ticket
        </router-link>
        <router-link class="hd-nav-item" :class="{ active: $route.path === '/knowledge' }" to="/knowledge" @click="mobileMenuOpen = false">
          <span class="material-icons" style="font-size:16px">menu_book</span> Base de conhecimento
        </router-link>
        <router-link class="hd-nav-item" :class="{ active: $route.path === '/version' }" to="/version" @click="mobileMenuOpen = false">
          <span class="material-icons" style="font-size:16px">new_releases</span> Versão / Atualizações
        </router-link>

        <template v-if="auth.isStaff">
          <div class="hd-nav-section" style="margin-top:8px">Administração</div>
          <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/tickets' }" to="/admin/tickets" @click="mobileMenuOpen = false">
            <span class="material-icons">manage_search</span> Gestão de tickets
            <span v-if="adminOpenCount" class="hd-nav-badge">{{ adminOpenCount }}</span>
          </router-link>
          <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/users' }" to="/admin/users" @click="mobileMenuOpen = false">
            <span class="material-icons">group</span> Utilizadores
          </router-link>
          <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/stats' }" to="/admin/stats" @click="mobileMenuOpen = false">
            <span class="material-icons">bar_chart</span> Estatísticas
          </router-link>
          <template v-if="auth.isAdmin">
            <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/settings' }" to="/admin/settings" @click="mobileMenuOpen = false">
              <span class="material-icons">settings</span> Configurações
            </router-link>
            <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/backup' }" to="/admin/backup" @click="mobileMenuOpen = false">
              <span class="material-icons">database</span> Backup &amp; Restauro
            </router-link>
          </template>
        </template>
      </nav>

      <div class="hd-sidebar-user" @click="auth.logout()">
        <AvatarCircle :name="auth.user?.display_name || '?'" size="32" />
        <div>
          <div class="hd-sidebar-user-name">{{ auth.user?.display_name }}</div>
          <div class="hd-sidebar-user-role">{{ roleLabel }}</div>
        </div>
        <span class="material-icons" style="font-size:16px;color:var(--c-muted);margin-left:auto">logout</span>
      </div>
      <router-link class="app-version-link" to="/version" @click="mobileMenuOpen = false">
        {{ versionLabelText }}
      </router-link>
    </aside>

    <!-- Main -->
    <div class="app-main">
      <!-- Header -->
      <header class="hd-header">
        <div class="hd-header-title">{{ pageTitle }}</div>
        <div class="hd-search">
          <span class="material-icons" style="font-size:16px">search</span>
          <input placeholder="Pesquisar tickets, utilizadores..." v-model="search" @keydown.enter="doSearch" />
        </div>
        <div class="hd-header-actions">
          <button class="hd-icon-btn" @click="auth.toggleDark()" :title="auth.isDark ? 'Modo claro' : 'Modo escuro'">
            <span class="material-icons">{{ auth.isDark ? 'light_mode' : 'dark_mode' }}</span>
          </button>
          <div class="notif-wrap" @click.stop>
            <button class="hd-icon-btn" @click="showNotifications = !showNotifications" title="Notificações" type="button">
              <span class="material-icons">notifications</span>
              <span v-if="notificationCount" class="hd-notif-dot"></span>
            </button>
            <div v-if="showNotifications" class="notif-panel">
              <div class="notif-title">Notificações</div>
              <router-link class="notif-item" to="/tickets" @click="showNotifications = false">
                <span class="material-icons">inbox</span>
                <div>
                  <strong>{{ openCount }}</strong> ticket{{ openCount !== 1 ? 's' : '' }} aberto{{ openCount !== 1 ? 's' : '' }} nos meus pedidos
                </div>
              </router-link>
              <router-link v-if="auth.isStaff" class="notif-item" to="/admin/tickets" @click="showNotifications = false">
                <span class="material-icons">manage_search</span>
                <div>
                  <strong>{{ adminOpenCount }}</strong> ticket{{ adminOpenCount !== 1 ? 's' : '' }} aberto{{ adminOpenCount !== 1 ? 's' : '' }} na gestão
                </div>
              </router-link>
              <div v-if="!notificationCount" class="notif-empty">Sem notificações novas.</div>
            </div>
          </div>
          <AvatarCircle :name="auth.user?.display_name || '?'" size="36" style="cursor:pointer" />
        </div>
      </header>

      <!-- Demo banner -->
      <div v-if="auth.isDemo" class="demo-banner">
        <span class="material-icons" style="font-size:16px;flex-shrink:0">info</span>
        <span>
          Está em <strong>modo de demonstração</strong> — os pedidos submetidos não serão processados.
          Para utilizar o sistema entre com a sua <strong>conta da escola</strong>
          (as mesmas credenciais do correio institucional).
        </span>
        <router-link to="/login" class="demo-banner-btn" @click="auth.logout()">Entrar</router-link>
      </div>

      <!-- Page content -->
      <main style="flex:1;overflow:auto">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getTickets } from '../api/tickets'
import { getPublicSettings } from '../api/settings'
import { applyFavicon } from '../utils/branding'
import { versionLabel } from '../utils/version'
import AvatarCircle from '../components/AvatarCircle.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const search = ref('')
const openCount = ref(0)
const adminOpenCount = ref(0)
const showNotifications = ref(false)
const mobileMenuOpen = ref(false)
const settings = ref({ org_name: 'Agrupamento de Escolas Eça de Queirós', logo_url: '', favicon_url: '' })
const versionLabelText = versionLabel()

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    teacher: 'Docente',
    non_teaching: 'Não docente',
    secretary: 'Secretaria',
    technician: 'Técnico',
    admin: 'Administrador',
  }
  return map[auth.user?.role ?? ''] ?? ''
})

const notificationCount = computed(() => openCount.value + (auth.isStaff ? adminOpenCount.value : 0))

const titleMap: Record<string, string> = {
  '/dashboard': 'Painel inicial',
  '/tickets': 'Os meus tickets',
  '/tickets/new': 'Novo pedido',
  '/knowledge': 'Base de conhecimento',
  '/version': 'Versão / Atualizações',
  '/admin/tickets': 'Gestão de tickets',
  '/admin/users': 'Utilizadores e permissões',
  '/admin/stats': 'Estatísticas',
  '/admin/settings': 'Configurações',
  '/admin/backup': 'Backup & Restauro',
}

const pageTitle = computed(() => {
  const p = route.path
  if (p.match(/^\/tickets\/\d+$/)) return 'Tickets'
  return titleMap[p] ?? 'Helpdesk'
})

function doSearch() {
  if (search.value.trim()) router.push({ path: '/tickets', query: { q: search.value } })
}

function closeNotifications() {
  showNotifications.value = false
}

onMounted(async () => {
  document.addEventListener('click', closeNotifications)
  try {
    settings.value = await getPublicSettings()
    applyFavicon(settings.value.favicon_url || settings.value.logo_url)
    const d = await getTickets({ page: 1, size: 1, status: 'open' })
    openCount.value = d.total
    if (auth.isStaff) {
      const d2 = await getTickets({ page: 1, size: 1, admin: true, status: 'open' })
      adminOpenCount.value = d2.total
    }
  } catch { /* ignore */ }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeNotifications)
})
</script>

<style scoped>
.demo-banner {
  align-items: center;
  background: #FEF3C7;
  border-bottom: 1px solid #FCD34D;
  color: #92400E;
  display: flex;
  font-size: 13px;
  gap: 10px;
  line-height: 1.4;
  padding: 10px 20px;
}

.dark .demo-banner {
  background: #451A03;
  border-color: #78350F;
  color: #FDE68A;
}

.demo-banner-btn {
  border: 1px solid currentColor;
  border-radius: 6px;
  color: inherit;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  margin-left: auto;
  padding: 4px 12px;
  text-decoration: none;
  white-space: nowrap;
}

.demo-banner-btn:hover {
  opacity: .75;
}

.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--c-bg);
}
.app-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  z-index: 20;
}
.app-main {
  margin-left: 260px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-version-link {
  border-top: 1px solid var(--c-border);
  color: var(--c-muted);
  display: block;
  font-size: 11px;
  font-weight: 700;
  padding: 9px 14px;
  text-align: center;
  text-decoration: none;
}

.app-version-link:hover {
  color: var(--c-primary);
}
.mobile-topbar {
  display: none;
}
.mobile-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.mobile-logo-img, .mobile-logo-dot {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  flex: 0 0 auto;
}
.mobile-logo-img {
  object-fit: contain;
}
.mobile-logo-dot {
  background: var(--c-primary);
}
.mobile-title {
  font-weight: 700;
  font-size: 13px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: calc(100vw - 112px);
}

.mobile-subtitle {
  color: var(--c-muted);
  font-size: 12px;
}
.notif-wrap {
  position: relative;
}
.notif-panel {
  position: absolute;
  top: 44px;
  right: 0;
  width: min(340px, calc(100vw - 24px));
  border: 1px solid var(--c-border);
  border-radius: 8px;
  background: var(--c-surface);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
  z-index: 50;
  overflow: hidden;
}
.notif-title {
  padding: 14px 16px;
  font-weight: 700;
  border-bottom: 1px solid var(--c-border);
}
.notif-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px;
  padding: 13px 16px;
  color: var(--c-text);
  text-decoration: none;
  border-bottom: 1px solid var(--c-border);
  font-size: 13px;
}
.notif-item:hover {
  background: var(--c-bg);
}
.notif-item .material-icons {
  color: var(--c-primary);
  font-size: 18px;
}
.notif-empty {
  padding: 18px 16px;
  color: var(--c-muted);
  font-size: 13px;
}

@media (max-width: 820px) {
  .app-shell {
    display: block;
    padding-top: 58px;
  }
  .mobile-topbar {
    position: fixed;
    inset: 0 0 auto 0;
    height: 58px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 14px;
    background: var(--c-surface);
    border-bottom: 1px solid var(--c-border);
    z-index: 80;
  }
  .app-sidebar {
    position: fixed;
    top: 58px;
    left: 0;
    right: 0;
    height: auto;
    width: 100%;
    transform: translateY(-120%);
    opacity: 0;
    pointer-events: none;
    transition: transform .18s ease, opacity .18s ease;
    box-shadow: 0 18px 40px rgba(15, 23, 42, .18);
  }
  .app-sidebar.open {
    transform: translateY(0);
    opacity: 1;
    pointer-events: auto;
  }
  .app-main {
    margin-left: 0;
  }
  :deep(.hd-sidebar) {
    width: 100%;
    min-height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--c-border);
  }
  :deep(.hd-sidebar-logo) {
    display: none;
  }
  :deep(.hd-nav) {
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
    padding: 12px;
    max-height: calc(100vh - 58px);
    overflow-y: auto;
  }
  :deep(.hd-nav-section) {
    display: block;
    grid-column: 1 / -1;
    padding: 10px 4px 2px;
  }
  :deep(.hd-nav-item) {
    min-height: 48px;
    padding: 10px 12px;
    white-space: normal;
    border: 1px solid var(--c-border);
    background: var(--c-surface);
  }
  :deep(.hd-sidebar-user) {
    display: flex;
    padding: 12px 14px;
  }
  :deep(.hd-header) {
    position: sticky;
    top: 58px;
    z-index: 15;
    gap: 8px;
    padding: 10px 12px;
    height: auto;
    flex-wrap: nowrap;
  }
  :deep(.hd-header-title) {
    display: none;
  }
  :deep(.hd-search) {
    flex: 1;
    min-width: 0;
    max-width: none;
  }
  :deep(.hd-search input) {
    min-width: 0;
    font-size: 13px;
  }
  :deep(.hd-header-actions) {
    gap: 6px;
    flex-shrink: 0;
  }
  :deep(.hd-header-actions > .hd-avatar) {
    display: none;
  }
}
</style>
