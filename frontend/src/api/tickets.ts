import { api } from '../boot/axios'

export interface School { id: number; name: string; short_name: string; address?: string }
export interface Category { id: number; name: string; description?: string; email_to?: string; color: string; icon: string; sla_hours: number }
export interface UserBrief { id: number; username: string; email: string; display_name: string; department?: string; role: string }
export interface HelpdeskGroupBrief { id: number; name: string; description?: string; members?: UserBrief[] }

export interface TicketListItem {
  id: number; title: string; status: string; priority: string
  created_at: string; updated_at: string; creator_email_notifications: boolean
  creator: UserBrief; assignee?: UserBrief; group?: HelpdeskGroupBrief; watchers?: UserBrief[]; category: Category; school?: School
}
export interface Comment { id: number; body: string; is_internal: boolean; created_at: string; updated_at?: string; author: UserBrief }
export interface Attachment { id: number; original_name: string; content_type: string; size: number; created_at: string }
export interface TicketEvent { id: number; event_type: string; message: string; created_at: string; actor?: UserBrief | null }
export interface TicketDetail extends TicketListItem { description: string; comments: Comment[]; attachments: Attachment[]; events: TicketEvent[] }
export interface PaginatedTickets { items: TicketListItem[]; total: number; page: number; size: number }
export interface KnowledgeArticle { id: number; title: string; body: string; is_published: boolean; category_id?: number | null; category?: Category | null; updated_at: string }

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

export async function createTicket(payload: { title: string; description: string; category_id: number; school_id: number; priority: string; watcher_ids?: number[]; group_ids?: number[]; creator_email_notifications?: boolean; escalate?: boolean }) {
  const { data } = await api.post<TicketDetail>('/api/v1/tickets', payload)
  return data
}

export async function uploadTicketAttachment(ticketId: number, file: File) {
  const payload = new FormData()
  payload.append('file', file)
  const { data } = await api.post<Attachment>(`/api/v1/tickets/${ticketId}/attachments`, payload)
  return data
}

export async function updateTicket(id: number, payload: Partial<{ status: string; assignee_id: number | null; group_id: number | null; priority: string; creator_email_notifications: boolean; title: string; description: string }>) {
  const { data } = await api.patch<TicketDetail>(`/api/v1/tickets/${id}`, payload)
  return data
}

export async function fetchAttachmentBlob(ticketId: number, attachmentId: number): Promise<string> {
  const resp = await api.get(`/api/v1/tickets/${ticketId}/attachments/${attachmentId}/download`, { responseType: 'blob' })
  return URL.createObjectURL(resp.data)
}

export async function downloadAttachment(ticketId: number, attachmentId: number, filename: string) {
  const url = await fetchAttachmentBlob(ticketId, attachmentId)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

export async function adminUpdateTicket(id: number, payload: Partial<{ status: string; assignee_id: number | null; group_id: number | null; priority: string; creator_email_notifications: boolean; title: string; description: string }>) {
  const { data } = await api.patch<TicketDetail>(`/api/v1/admin/tickets/${id}`, payload)
  return data
}

export async function escalateTicket(id: number) {
  const { data } = await api.post<TicketDetail>(`/api/v1/tickets/${id}/escalate`)
  return data
}

export async function addWatcher(ticketId: number, userId: number) {
  const { data } = await api.post<TicketDetail>(`/api/v1/tickets/${ticketId}/watchers`, { user_id: userId })
  return data
}

export async function removeWatcher(ticketId: number, userId: number) {
  const { data } = await api.delete<TicketDetail>(`/api/v1/tickets/${ticketId}/watchers/${userId}`)
  return data
}

export async function adminBulkUpdateTickets(payload: { ids: number[]; status?: string; assignee_id?: number | null; group_id?: number | null; priority?: string; creator_email_notifications?: boolean }) {
  const { data } = await api.patch<TicketDetail[]>('/api/v1/admin/tickets/bulk', payload)
  return data
}

export async function adminBulkActionTickets(payload: { ids: number[]; action: 'archive' | 'delete' }) {
  const { data } = await api.post<{ affected: number }>('/api/v1/admin/tickets/bulk-action', payload)
  return data
}

export async function syncMailReplies() {
  const { data } = await api.post<{ processed: number; skipped: number }>('/api/v1/admin/mail/sync')
  return data
}

export async function addComment(ticketId: number, body: string, is_internal = false) {
  const { data } = await api.post<Comment>(`/api/v1/tickets/${ticketId}/comments`, { body, is_internal })
  return data
}

export async function updateComment(ticketId: number, commentId: number, body: string) {
  const { data } = await api.patch<Comment>(`/api/v1/tickets/${ticketId}/comments/${commentId}`, { body })
  return data
}

export async function deleteComment(ticketId: number, commentId: number) {
  await api.delete(`/api/v1/tickets/${ticketId}/comments/${commentId}`)
}

export async function getRoutingRules() {
  const { data } = await api.get('/api/v1/admin/routing-rules')
  return data
}

export async function createRoutingRule(payload: { category_id?: number | null; school_id?: number | null; group_id?: number | null; assignee_id?: number | null; priority?: number }) {
  const { data } = await api.post('/api/v1/admin/routing-rules', payload)
  return data
}

export async function deleteRoutingRule(id: number) {
  await api.delete(`/api/v1/admin/routing-rules/${id}`)
}

export async function getCategories() {
  const { data } = await api.get<Category[]>('/api/v1/categories')
  return data
}

export async function createCategory(payload: { name: string; description?: string; email_to?: string; color: string; icon: string; sla_hours: number }) {
  const { data } = await api.post<Category>('/api/v1/categories', payload)
  return data
}

export async function updateCategory(id: number, payload: Partial<{ name: string; description?: string; email_to?: string; color: string; icon: string; sla_hours: number }>) {
  const { data } = await api.patch<Category>(`/api/v1/categories/${id}`, payload)
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

export async function getBackupConfig() {
  const { data } = await api.get('/api/v1/admin/backup/config')
  return data
}

export async function updateBackupConfig(payload: { enabled: boolean; interval_hours: number; directory: string; retention: number; secondary_directory?: string }) {
  const { data } = await api.patch('/api/v1/admin/backup/config', payload)
  return data
}

export async function runServerBackup() {
  const { data } = await api.post('/api/v1/admin/backup/run')
  return data as { filename: string; path: string; locations: string[]; secondary_error?: string }
}

export interface BackupHistoryEntry {
  id: number
  filename: string
  path: string
  locations: string[]
  date: string
  ok: boolean
  source: 'manual' | 'auto'
  secondary_error?: string
}

export async function getBackupHistory() {
  const { data } = await api.get<BackupHistoryEntry[]>('/api/v1/admin/backup/history')
  return data
}

export async function getKnowledgeArticles(admin = false) {
  const { data } = await api.get<KnowledgeArticle[]>(admin ? '/api/v1/knowledge/admin' : '/api/v1/knowledge')
  return data
}

export async function createKnowledgeArticle(payload: { title: string; body: string; category_id?: number | null; is_published?: boolean }) {
  const { data } = await api.post<KnowledgeArticle>('/api/v1/knowledge/admin', payload)
  return data
}

export async function updateKnowledgeArticle(id: number, payload: Partial<{ title: string; body: string; category_id: number | null; is_published: boolean }>) {
  const { data } = await api.patch<KnowledgeArticle>(`/api/v1/knowledge/admin/${id}`, payload)
  return data
}

export async function deleteKnowledgeArticle(id: number) {
  await api.delete(`/api/v1/knowledge/admin/${id}`)
}
