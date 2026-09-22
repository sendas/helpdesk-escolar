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
  login_notice_enabled?: boolean
  login_notice_text?: string
  no_access_contact_email?: string
  ui_design?: 'modern' | 'classic'
  demo_mode_enabled?: boolean
  demo_profiles?: string[]
  demo_content_visible?: boolean
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

export async function updateLoginNoticeSettings(payload: { enabled: boolean; text: string }) {
  const { data } = await api.put<{ login_notice_enabled: boolean; login_notice_text: string }>('/api/v1/settings/login-notice', payload)
  return data
}

export async function updateDesignSettings(design: 'modern' | 'classic') {
  const { data } = await api.put<{ ui_design: 'modern' | 'classic' }>('/api/v1/settings/design', { design })
  return data
}

export async function updateDemoModeSettings(payload: { enabled: boolean; profiles: string[]; content_visible?: boolean }) {
  const { data } = await api.put<{ demo_mode_enabled: boolean; demo_profiles: string[]; demo_content_visible?: boolean }>('/api/v1/settings/demo-mode', payload)
  return data
}

export async function updateNoAccessContactSettings(payload: { email: string }) {
  const { data } = await api.put<{ no_access_contact_email: string }>('/api/v1/settings/no-access-contact', payload)
  return data
}
