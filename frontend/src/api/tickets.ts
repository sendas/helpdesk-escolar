import { api } from '../boot/axios'

export interface School { id: number; name: string; short_name: string; address?: string }
export interface Category { id: number; name: string; description?: string; color: string; icon: string; sla_hours: number }
export interface UserBrief { id: number; username: string; email: string; display_name: string; department?: string; role: string }

export interface TicketListItem {
  id: number; title: string; status: string; priority: string
  created_at: string; updated_at: string
  creator: UserBrief; assignee?: UserBrief; category: Category; school?: School
}
export interface Comment { id: number; body: string; is_internal: boolean; created_at: string; author: UserBrief }
export interface Attachment { id: number; original_name: string; content_type: string; size: number; created_at: string }
export interface TicketDetail extends TicketListItem { description: string; comments: Comment[]; attachments: Attachment[] }
export interface PaginatedTickets { items: TicketListItem[]; total: number; page: number; size: number }

export async function getTickets(params: { page?: number; size?: number; status?: string; category_id?: number; school_id?: number; priority?: string; admin?: boolean }) {
  const prefix = params.admin ? '/api/v1/admin' : '/api/v1'
  const p = { ...params }
  delete (p as any).admin
  const { data } = await api.get<PaginatedTickets>(`${prefix}/tickets`, { params: p })
  return data
}

export async function getTicket(id: number) {
  const { data } = await api.get<TicketDetail>(`/api/v1/tickets/${id}`)
  return data
}

export async function createTicket(payload: { title: string; description: string; category_id: number; school_id: number; priority: string }) {
  const { data } = await api.post<TicketDetail>('/api/v1/tickets', payload)
  return data
}

export async function uploadTicketAttachment(ticketId: number, file: File) {
  const payload = new FormData()
  payload.append('file', file)
  const { data } = await api.post<Attachment>(`/api/v1/tickets/${ticketId}/attachments`, payload)
  return data
}

export async function updateTicket(id: number, payload: Partial<{ status: string; assignee_id: number | null; priority: string }>) {
  const { data } = await api.patch<TicketDetail>(`/api/v1/tickets/${id}`, payload)
  return data
}

export async function adminUpdateTicket(id: number, payload: Partial<{ status: string; assignee_id: number | null; priority: string }>) {
  const { data } = await api.patch<TicketDetail>(`/api/v1/admin/tickets/${id}`, payload)
  return data
}

export async function addComment(ticketId: number, body: string, is_internal = false) {
  const { data } = await api.post<Comment>(`/api/v1/tickets/${ticketId}/comments`, { body, is_internal })
  return data
}

export async function getCategories() {
  const { data } = await api.get<Category[]>('/api/v1/categories')
  return data
}

export async function createCategory(payload: { name: string; description?: string; color: string; icon: string; sla_hours: number }) {
  const { data } = await api.post<Category>('/api/v1/categories', payload)
  return data
}

export async function deleteCategory(id: number) { await api.delete(`/api/v1/categories/${id}`) }

export async function getSchools() {
  const { data } = await api.get<School[]>('/api/v1/schools')
  return data
}

export async function createSchool(payload: { name: string; short_name: string; address?: string }) {
  const { data } = await api.post<School>('/api/v1/schools', payload)
  return data
}

export async function deleteSchool(id: number) { await api.delete(`/api/v1/schools/${id}`) }

export async function getAdminStats() {
  const { data } = await api.get('/api/v1/admin/stats')
  return data
}

export async function downloadBackup() {
  const resp = await api.get('/api/v1/admin/backup', { responseType: 'blob' })
  const url = URL.createObjectURL(resp.data)
  const a = document.createElement('a')
  a.href = url
  a.download = `helpdesk-backup-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
}
