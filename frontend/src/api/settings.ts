import { api } from '../boot/axios'

export interface PublicSettings {
  org_name: string
  logo_url: string
  favicon_url: string
}

export async function getPublicSettings() {
  const { data } = await api.get<PublicSettings>('/api/v1/settings/public')
  return data
}

export async function updateSettings(payload: { org_name: string; logo?: File | null }) {
  const form = new FormData()
  form.append('org_name', payload.org_name)
  if (payload.logo) form.append('logo', payload.logo)
  const { data } = await api.put<PublicSettings>('/api/v1/settings', form)
  return data
}
