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
