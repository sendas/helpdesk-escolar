import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { loginLdap as apiLoginLdap, getAzureLoginUrl, loginDemo as apiLoginDemo } from '../api/auth'
import { getMe } from '../api/users'

interface User {
  id: number
  username: string
  email: string
  display_name: string
  department?: string
  role: 'teacher' | 'non_teaching' | 'secretary' | 'technician' | 'admin'
  is_technician?: boolean
  auth_provider: string
  hidden_category_ids?: number[]
  role_key?: string | null
  effective_role_key?: string
  role_label?: string
  permissions?: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('token'))
  const user = ref<User | null>(null)
  const isDark = ref(localStorage.getItem('dark') === '1')

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const permissions = computed(() => new Set(user.value?.permissions ?? []))
  // Permission check (see backend app/services/permissions.py); administrators can do everything
  function can(perm: string) {
    return isAdmin.value || permissions.value.has(perm)
  }
  const isStaff = computed(() => can('tickets.manage') || user.value?.role === 'technician' || !!user.value?.is_technician)
  // Can open the "Administração" area (manage or only supervise)
  const hasAdminArea = computed(() => ['tickets.view_all', 'tickets.manage', 'stats.view', 'users.manage', 'settings.manage'].some(can))
  const isDemo = computed(() => user.value?.auth_provider === 'demo')

  function applyDark() {
    document.documentElement.classList.toggle('dark', isDark.value)
  }

  function setDark(enabled: boolean) {
    isDark.value = enabled
    localStorage.setItem('dark', isDark.value ? '1' : '0')
    applyDark()
  }

  function toggleDark() {
    setDark(!isDark.value)
  }

  async function loginLdap(username: string, password: string) {
    const data = await apiLoginLdap(username, password)
    _setToken(data.access_token)
    await fetchMe()
    _redirect()
  }

  async function loginDemo(role: string) {
    const data = await apiLoginDemo(role)
    _setToken(data.access_token)
    await fetchMe()
    _redirect()
  }

  function loginAzure() {
    window.location.href = getAzureLoginUrl()
  }

  async function handleAzureCallback(rawToken: string) {
    _setToken(rawToken)
    await fetchMe()
    _redirect()
  }

  function _setToken(t: string) {
    token.value = t
    localStorage.setItem('token', t)
  }

  function _redirect() {
    window.location.href = '/dashboard'
  }

  async function fetchMe() {
    try {
      user.value = (await getMe()) as User
    } catch {
      logout()
    }
  }

  async function init() {
    if (token.value && !user.value) {
      await fetchMe()
    }
    applyDark()
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
    setDark(false)
    applyDark()
    window.location.href = '/login'
  }

  return { token, user, isDark, isAuthenticated, isAdmin, isStaff, isDemo, can, hasAdminArea, loginLdap, loginDemo, loginAzure, handleAzureCallback, fetchMe, init, setDark, toggleDark, logout }
})
