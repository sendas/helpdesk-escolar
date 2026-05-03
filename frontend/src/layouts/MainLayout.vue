<template>
  <div style="display:flex;min-height:100vh;background:var(--c-bg)">
    <!-- Sidebar -->
    <aside class="hd-sidebar" style="position:fixed;top:0;left:0;height:100vh;z-index:20">
      <div class="hd-sidebar-logo">
        <div class="hd-sidebar-logo-icon"></div>
        <div class="hd-sidebar-logo-text">
          <div class="hd-sidebar-logo-name">Agrupamento de Escolas<br>Eça de Queirós</div>
          <div class="hd-sidebar-logo-sub">Helpdesk {{ roleLabel }}</div>
        </div>
      </div>

      <nav class="hd-nav">
        <div class="hd-nav-section">Principal</div>
        <router-link class="hd-nav-item" :class="{ active: $route.path === '/dashboard' }" to="/dashboard">
          <span class="material-icons">home</span> Painel inicial
        </router-link>
        <router-link class="hd-nav-item" :class="{ active: $route.path.startsWith('/tickets') && !$route.path.startsWith('/admin') }" to="/tickets">
          <span class="material-icons">inbox</span> Os meus tickets
          <span v-if="openCount" class="hd-nav-badge">{{ openCount }}</span>
        </router-link>
        <router-link class="hd-nav-item" :class="{ active: $route.path === '/tickets/new' }" to="/tickets/new">
          <span class="material-icons" style="font-size:16px">add_circle</span> Novo ticket
        </router-link>

        <template v-if="auth.isStaff">
          <div class="hd-nav-section" style="margin-top:8px">Administração</div>
          <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/tickets' }" to="/admin/tickets">
            <span class="material-icons">manage_search</span> Gestão de tickets
            <span v-if="adminOpenCount" class="hd-nav-badge">{{ adminOpenCount }}</span>
          </router-link>
          <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/users' }" to="/admin/users">
            <span class="material-icons">group</span> Utilizadores
          </router-link>
          <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/stats' }" to="/admin/stats">
            <span class="material-icons">bar_chart</span> Estatísticas
          </router-link>
          <template v-if="auth.isAdmin">
            <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/settings' }" to="/admin/settings">
              <span class="material-icons">settings</span> Configurações
            </router-link>
            <router-link class="hd-nav-item" :class="{ active: $route.path === '/admin/backup' }" to="/admin/backup">
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
    </aside>

    <!-- Main -->
    <div style="margin-left:260px;flex:1;display:flex;flex-direction:column;min-width:0">
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
          <button class="hd-icon-btn">
            <span class="material-icons">notifications</span>
            <span class="hd-notif-dot"></span>
          </button>
          <AvatarCircle :name="auth.user?.display_name || '?'" size="36" style="cursor:pointer" />
        </div>
      </header>

      <!-- Page content -->
      <main style="flex:1;overflow:auto">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { getTickets } from '../api/tickets'
import AvatarCircle from '../components/AvatarCircle.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const search = ref('')
const openCount = ref(0)
const adminOpenCount = ref(0)

const roleLabel = computed(() => {
  const map: Record<string, string> = { teacher: 'Docente', technician: 'Técnico', admin: 'Administrador' }
  return map[auth.user?.role ?? ''] ?? ''
})

const titleMap: Record<string, string> = {
  '/dashboard': 'Painel inicial',
  '/tickets': 'Os meus tickets',
  '/tickets/new': 'Novo pedido',
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

onMounted(async () => {
  try {
    const d = await getTickets({ page: 1, size: 1, status: 'open' })
    openCount.value = d.total
    if (auth.isStaff) {
      const d2 = await getTickets({ page: 1, size: 1, admin: true, status: 'open' })
      adminOpenCount.value = d2.total
    }
  } catch { /* ignore */ }
})
</script>
