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
      { path: 'tickets/:id', component: () => import('../pages/TicketDetailPage.vue') },
      { path: 'knowledge', component: () => import('../pages/KnowledgePage.vue') },
      { path: 'version', component: () => import('../pages/VersionPage.vue') },
      { path: 'about', component: () => import('../pages/AboutPage.vue') },
      { path: 'suggestions', component: () => import('../pages/SuggestionsPage.vue') },
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

  return router
})
