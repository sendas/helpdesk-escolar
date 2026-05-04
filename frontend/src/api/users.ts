import { api } from '../boot/axios'
import type { UserBrief } from './tickets'

export interface UserFull extends UserBrief {
  auth_provider: string
  is_active: boolean
  role_source: string
  role_locked: boolean
  onprem_path?: string
  created_at: string
  last_login?: string
}

export async function getMe() {
  const { data } = await api.get<UserFull>('/api/v1/users/me')
  return data
}

export async function getUsers() {
  const { data } = await api.get<UserFull[]>('/api/v1/users')
  return data
}

export async function updateUser(id: number, payload: { role?: string; is_active?: boolean; department?: string; role_locked?: boolean }) {
  const { data } = await api.patch<UserFull>(`/api/v1/users/${id}`, payload)
  return data
}

export async function importAzureUsers() {
  const { data } = await api.post<{
    created: number; updated: number; skipped: number; total: number; role_changes: number; manual_locked: number
    skipped_guests: number; skipped_disabled: number; skipped_outside_ou: number; skipped_without_email: number
  }>('/api/v1/users/import-azure')
  return data
}

export async function bulkUpdateUsers(payload: { ids: number[]; role?: string; is_active?: boolean; role_locked?: boolean }) {
  const { data } = await api.patch<UserFull[]>('/api/v1/users/bulk', payload)
  return data
}
