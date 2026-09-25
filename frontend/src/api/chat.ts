import { api } from '../boot/axios'

export interface ChatUser { id: number; display_name: string; role_label?: string; online?: boolean }
export interface ChatMessage { id: number; conversation_id: number; body: string; is_system: boolean; created_at: string; author: ChatUser | null }
export interface ChatConversation {
  id: number
  kind: 'direct' | 'group' | 'support'
  title: string
  role_key: string | null
  members: ChatUser[]
  last_message: ChatMessage | null
  unread: number
  updated_at: string
  created_at: string
  support_status: 'waiting' | 'active' | 'closed' | 'converted' | null
  ticket_id: number | null
  requester_id: number | null
  agent_id: number | null
}
export interface SupportDay { enabled: boolean; start: string; end: string }
export interface SupportStatus {
  enabled: boolean
  open_now: boolean
  hours: Record<string, SupportDay>
  hours_text: string
  wait_minutes: number
  agents_online: number
  conversation_id: number | null
  is_responder: boolean
  available: boolean | null
}

export async function getConversations() {
  const { data } = await api.get<ChatConversation[]>('/api/v1/chat/conversations')
  return data
}

export async function getChatPeople() {
  const { data } = await api.get<ChatUser[]>('/api/v1/chat/people')
  return data
}

export async function getChatUnread() {
  const { data } = await api.get<{ unread: number }>('/api/v1/chat/unread')
  return data.unread
}

export async function openDirect(user_id: number) {
  const { data } = await api.post<ChatConversation>('/api/v1/chat/conversations/direct', { user_id })
  return data
}

export async function createGroup(title: string, member_ids: number[]) {
  const { data } = await api.post<ChatConversation>('/api/v1/chat/conversations/group', { title, member_ids })
  return data
}

export async function updateGroup(id: number, payload: { title?: string; member_ids?: number[] }) {
  const { data } = await api.patch<ChatConversation>(`/api/v1/chat/conversations/${id}`, payload)
  return data
}

export async function getMessages(id: number, before?: number) {
  const { data } = await api.get<{ conversation: ChatConversation; messages: ChatMessage[] }>(`/api/v1/chat/conversations/${id}/messages`, { params: { before } })
  return data
}

export async function sendChatMessage(id: number, body: string) {
  const { data } = await api.post<ChatMessage>(`/api/v1/chat/conversations/${id}/messages`, { body })
  return data
}

export async function markRead(id: number) {
  await api.post(`/api/v1/chat/conversations/${id}/read`)
}

export async function getSupportStatus() {
  const { data } = await api.get<SupportStatus>('/api/v1/chat/support/status')
  return data
}

export async function getMySupport() {
  const { data } = await api.get<{ conversation: ChatConversation; messages: ChatMessage[] } | null>('/api/v1/chat/support/mine')
  return data
}

export async function startSupport(body: string, school_id: number | null) {
  const { data } = await api.post<{ conversation: ChatConversation; messages: ChatMessage[] }>('/api/v1/chat/support/start', { body, school_id })
  return data
}

export async function getSupportQueue() {
  const { data } = await api.get<ChatConversation[]>('/api/v1/chat/support/queue')
  return data
}

export async function setSupportAvailability(available: boolean) {
  const { data } = await api.put<{ available: boolean }>('/api/v1/chat/support/availability', { available })
  return data.available
}

export async function acceptSupport(id: number) {
  const { data } = await api.post<ChatConversation>(`/api/v1/chat/support/${id}/accept`)
  return data
}

export async function closeSupport(id: number) {
  const { data } = await api.post<ChatConversation>(`/api/v1/chat/support/${id}/close`)
  return data
}

export async function convertSupport(id: number, payload: { title?: string; category_id?: number } = {}) {
  const { data } = await api.post<{ ticket_id: number | null }>(`/api/v1/chat/support/${id}/convert`, payload)
  return data.ticket_id
}
