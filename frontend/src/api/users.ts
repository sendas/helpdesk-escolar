import { api } from '../boot/axios'
import type { UserBrief } from './tickets'

export interface UserFull extends UserBrief { auth_provider: string; is_active: boolean; created_at: string; last_login?: string }

export async function getMe() {
  const { data } = await api.get<UserFull>('/api/v1/users/me')
  return data
}

export async function getUsers() {
  const { data } = await api.get<UserFull[]>('/api/v1/users')
  return data
}

export async function updateUser(id: number, payload: { role?: string; is_active?: boolean; department?: string }) {
  const { data } = await api.patch<UserFull>(`/api/v1/users/${id}`, payload)
  return data
}
