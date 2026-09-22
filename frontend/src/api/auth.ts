import { api } from '../boot/axios'

export async function loginLdap(username: string, password: string) {
  const { data } = await api.post('/api/v1/auth/ldap-login', { username, password })
  return data as { access_token: string; token_type: string }
}

export function getAzureLoginUrl() {
  const apiUrl = (import.meta as any).env?.VITE_API_URL || ''
  return `${apiUrl}/api/v1/auth/azure-login`
}

export async function sendNoAccessContact(payload: { name: string; recruitment_group: string; school: string; message: string }) {
  const { data } = await api.post('/api/v1/auth/no-access-contact', payload)
  return data as { sent: boolean }
}
