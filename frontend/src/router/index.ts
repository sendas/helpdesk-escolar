import { route } from 'quasar/wrappers'
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    component: () => import('../layouts/AuthLayout.vue'),
    children: [{ path: '', component: () => import('../pages/LoginPage.vue') }],
    meta: { public: true },
  },
  {
    path: '/auth/callback',
    component: () => import('../pages/AzureCallback.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('../pages/DashboardPage.vue') },
      { path: 'tickets', component: () => import('../pages/TicketListPage.vue') },
      { path: 'tickets/new', component: () => import('../pages/TicketCreatePage.vue') },
      // remount: going from one ticket to another (e.g. a link in the support chat) loads the new ticket
      { path: 'tickets/:id', meta: { remount: true }, component: () => import('../pages/TicketDetailPage.vue') },
      { path: 'knowledge', component: () => import('../pages/KnowledgePage.vue') },
      { path: 'version', component: () => import('../pages/VersionPage.vue') },
      { path: 'about', component: () => import('../pages/AboutPage.vue') },
      { path: 'suggestions', component: () => import('../pages/SuggestionsPage.vue') },
      { path: 'chat', meta: { perm: ['chat.team', 'chat.support'] }, component: () => import('../pages/ChatPage.vue') },
      {
        path: 'admin',
        meta: { requiresAdminArea: true },
        children: [
          { path: '', meta: { perm: ['tickets.view_all', 'tickets.manage'] }, component: () => import('../pages/admin/AdminDashboard.vue') },
          { path: 'tickets', meta: { perm: ['tickets.view_all', 'tickets.manage'] }, component: () => import('../pages/admin/AdminTicketsPage.vue') },
          { path: 'users', meta: { perm: ['tickets.manage', 'users.manage'] }, component: () => import('../pages/admin/AdminUsersPage.vue') },
          { path: 'categories', meta: { perm: 'settings.manage' }, component: () => import('../pages/admin/AdminCategoriesPage.vue') },
          { path: 'stats', meta: { perm: 'stats.view' }, component: () => import('../pages/admin/AdminStatsPage.vue') },
          { path: 'settings', meta: { perm: 'settings.manage' }, component: () => import('../pages/admin/AdminSettingsPage.vue') },
          { path: 'backup', meta: { perm: 'settings.manage' }, component: () => import('../pages/admin/AdminBackupPage.vue') },
          { path: 'suggestions', meta: { perm: 'settings.manage' }, component: () => import('../pages/admin/AdminSuggestionsPage.vue') },
          { path: 'mail-log', meta: { perm: 'settings.manage' }, component: () => import('../pages/admin/AdminMailLogPage.vue') },
        ],
      },
    ],
  },
  { path: '/:catchAll(.*)*', redirect: '/dashboard' },
]

export default route(function () {
  const router = createRouter({
    history: createWebHistory(),
    routes,
  })

  router.beforeEach(async (to) => {
    const { useAuthStore } = await import('../stores/auth')
    const auth = useAuthStore()
    await auth.init()

    if (!to.meta?.public && !auth.isAuthenticated) {
      return '/login'
    }
    const perm = to.meta?.perm as string | string[] | undefined
    if (perm && !(Array.isArray(perm) ? perm : [perm]).some((p) => auth.can(p) || (p === 'tickets.manage' && auth.isStaff))) {
      return '/dashboard'
    }
    if (to.meta?.requiresAdminArea && !auth.hasAdminArea) {
      return '/dashboard'
    }
  })

  // After a deploy the old page files are gone: a tab left open would fail to change page. Reload it (once).
  const isChunkError = (err: any) => /dynamically imported module|Importing a module script failed|Loading chunk|Unable to preload CSS/i.test(String(err?.message ?? err))
  const reloadOnce = (path: string) => {
    try {
      if (sessionStorage.getItem('hd-chunk-reload') === path) return
      sessionStorage.setItem('hd-chunk-reload', path)
    } catch { /* private mode: reload anyway */ }
    window.location.assign(path)
  }
  router.onError((err, to) => { if (isChunkError(err)) reloadOnce(to.fullPath) })
  window.addEventListener('vite:preloadError', (event) => {
    event.preventDefault()
    reloadOnce(window.location.pathname + window.location.search)
  })
  router.afterEach(() => { try { sessionStorage.removeItem('hd-chunk-reload') } catch { /* ignore */ } })

  return router
})
