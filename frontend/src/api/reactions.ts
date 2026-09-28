import { api } from '../boot/axios'

export interface ReactionSummary { emoji: string; count: number; mine: boolean; names: string[] }
export type ReactionTarget = 'comment' | 'chat'
export const REACTION_EMOJIS = ['👍', '❤️', '😂', '😮', '🙏', '✅', '👀', '🎉']

export async function getReactions(target_type: ReactionTarget, ids: number[]) {
  if (!ids.length) return {} as Record<string, ReactionSummary[]>
  const { data } = await api.get<Record<string, ReactionSummary[]>>('/api/v1/reactions', { params: { target_type, ids: ids.join(',') } })
  return data
}

export async function toggleReaction(target_type: ReactionTarget, target_id: number, emoji: string) {
  const { data } = await api.post<ReactionSummary[]>('/api/v1/reactions/toggle', { target_type, target_id, emoji })
  return data
}
