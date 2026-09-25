// "Maria Leonor Marinho Nunes Serra Docente-510 - Física e Química" → "Maria Serra"
export function shortName(name?: string | null): string {
  if (!name) return ''
  const base = name.split(/\s+(?:Docente|Não Docente|Nao Docente|Funcionári[oa])[-\s]/i)[0].split(' - ')[0].trim()
  const parts = base.split(/\s+/).filter(Boolean)
  return parts.length > 2 ? `${parts[0]} ${parts[parts.length - 1]}` : base
}
