// Pedidos sem acesso (backend app/api/v1/access_requests.py)
import { api } from '../boot/axios'

export interface AccessMessage { id: number; created_at: string; kind: 'email' | 'phone' | 'note' | 'inbound'; body: string; author?: { id: number; display_name: string } | null; sent_ok: boolean }
export interface AccessRequest {
  id: number; created_at: string; updated_at: string; status: 'new' | 'answered' | 'closed'
  profile: string; profile_label: string; name: string; email: string; phone: string
  student_number: string; year: string; class_name: string; school: string; recruitment_group: string; message: string
  handled_by?: { id: number; display_name: string } | null; messages_count: number; messages?: AccessMessage[]
}

export async function listAccessRequests(state: string, q = '') {
  const { data } = await api.get<{ items: AccessRequest[]; counts: Record<string, number> }>('/api/v1/access-requests', { params: { state, q: q || undefined } })
  return data
}
export async function getAccessRequest(id: number) {
  const { data } = await api.get<AccessRequest>(`/api/v1/access-requests/${id}`)
  return data
}
export async function replyAccessRequest(id: number, body: string, kind: 'email' | 'phone' | 'note', close = false) {
  const { data } = await api.post<AccessRequest>(`/api/v1/access-requests/${id}/reply`, { body, kind, close })
  return data
}
export async function setAccessRequestStatus(id: number, status: 'new' | 'answered' | 'closed') {
  const { data } = await api.patch<AccessRequest>(`/api/v1/access-requests/${id}`, { status })
  return data
}
export async function accessRequestsWaiting() {
  const { data } = await api.get<{ new: number }>('/api/v1/access-requests/count')
  return data.new
}
