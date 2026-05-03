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
      {
        path: 'admin',
        meta: { requiresStaff: true },
        children: [
          { path: '', component: () => import('../pages/admin/AdminDashboard.vue') },
          { path: 'tickets', component: () => import('../pages/admin/AdminTicketsPage.vue') },
          { path: 'users', component: () => import('../pages/admin/AdminUsersPage.vue') },
          { path: 'categories', component: () => import('../pages/admin/AdminCategoriesPage.vue') },
          { path: 'stats', component: () => import('../pages/admin/AdminStatsPage.vue') },
          { path: 'settings', meta: { requiresAdmin: true }, component: () => import('../pages/admin/AdminSettingsPage.vue') },
          { path: 'backup', meta: { requiresAdmin: true }, component: () => import('../pages/admin/AdminBackupPage.vue') },
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
    if (to.meta?.requiresAdmin && !auth.isAdmin) {
      return '/dashboard'
    }
    if (to.meta?.requiresStaff && !auth.isStaff) {
      return '/dashboard'
    }
  })

  return router
})
