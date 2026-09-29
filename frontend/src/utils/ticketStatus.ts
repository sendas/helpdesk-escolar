// Ticket states as shown to people (one place, so every page uses the same words)
export const STATUS_LABELS: Record<string, string> = {
  open: 'Aberto',
  assigned: 'Atribuído',
  in_progress: 'Em Curso',
  waiting_user: 'A aguardar utilizador',
  resolved: 'Resolvido',
  closed: 'Fechado',
}

/** Label for a state; `short` gives "A aguardar" where space is tight (dashboard tiles). */
export function statusLabel(status: string, short = false): string {
  if (short && status === 'waiting_user') return 'A aguardar'
  return STATUS_LABELS[status] ?? status
}

// Accent colour per state (row borders, pills), same as the Painel inicial
export const STATUS_COLORS: Record<string, string> = {
  open: '#3B82F6', assigned: '#F59E0B', in_progress: '#8B5CF6', waiting_user: '#06B6D4', resolved: '#10B981', closed: '#94A3B8',
}

export function statusColor(status: string): string {
  return STATUS_COLORS[status] ?? '#94A3B8'
}
