import { api } from '../boot/axios'

export interface PublicSettings {
  org_name: string
  logo_url: string
  favicon_url: string
  support_provider_name: string
  support_provider_email: string
  azure_allowed_onprem_ous?: string[]
  knowledge_enabled: boolean
  category_warnings_enabled: boolean
  suggestion_emails?: string[]
}

export interface AzureSyncSettings {
  allowed_onprem_ous: string[]
}

export async function getPublicSettings() {
  const { data } = await api.get<PublicSettings>('/api/v1/settings/public')
  return data
}

export async function updateSettings(payload: { org_name: string; support_provider_name?: string; support_provider_email?: string; logo?: File | null }) {
  const form = new FormData()
  form.append('org_name', payload.org_name)
  form.append('support_provider_name', payload.support_provider_name || 'Empresa de apoio informático')
  form.append('support_provider_email', payload.support_provider_email || '')
  if (payload.logo) form.append('logo', payload.logo)
  const { data } = await api.put<PublicSettings>('/api/v1/settings', form)
  return data
}

export async function getAzureSyncSettings() {
  const { data } = await api.get<AzureSyncSettings>('/api/v1/settings/azure-sync')
  return data
}

export async function updateAzureSyncSettings(payload: AzureSyncSettings) {
  const { data } = await api.put<AzureSyncSettings>('/api/v1/settings/azure-sync', payload)
  return data
}

export async function updateFeatureSettings(payload: { knowledge_enabled: boolean; category_warnings_enabled?: boolean }) {
  const { data } = await api.put<{ knowledge_enabled: boolean; category_warnings_enabled: boolean }>('/api/v1/settings/features', payload)
  return data
}
