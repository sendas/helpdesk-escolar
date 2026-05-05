import { api } from '../boot/axios'

export interface PublicSettings {
  org_name: string
  logo_url: string
  favicon_url: string
  support_provider_name: string
  support_provider_email: string
}

export async function getPublicSettings() {
  const { data } = await api.get<PublicSettings>('/api/v1/settings/public')
  return data
}

export async function updateSettings(payload: { org_name: string; support_provider_name?: string; support_provider_email?: string; logo?: File | null }) {
  const form = new FormData()
  form.append('org_name', payload.org_name)
  form.append('support_provider_name', payload.support_provider_name || 'Fornecedor externo')
  form.append('support_provider_email', payload.support_provider_email || '')
  if (payload.logo) form.append('logo', payload.logo)
  const { data } = await api.put<PublicSettings>('/api/v1/settings', form)
  return data
}
