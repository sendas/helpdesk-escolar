import { api } from '../boot/axios'

export interface Role { key: string; label: string; icon: string; color: string; permissions: string[]; builtin: boolean; locked: boolean; sort: number; user_count: number }
export interface Permission { key: string; label: string; hint: string }

export async function getRoles() {
  const { data } = await api.get<Role[]>('/api/v1/roles')
  return data
}

export async function getPermissionCatalog() {
  const { data } = await api.get<Permission[]>('/api/v1/roles/permissions')
  return data
}

export async function createRole(payload: { label: string; icon?: string; color?: string; permissions: string[] }) {
  const { data } = await api.post<Role>('/api/v1/roles', payload)
  return data
}

export async function updateRole(key: string, payload: { label?: string; icon?: string; color?: string; permissions?: string[] }) {
  const { data } = await api.patch<Role>(`/api/v1/roles/${key}`, payload)
  return data
}

export async function deleteRole(key: string) {
  await api.delete(`/api/v1/roles/${key}`)
}
