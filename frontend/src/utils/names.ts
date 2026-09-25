// Display names come from the directory as e.g. "Maria Leonor Marinho Nunes Serra Docente-510 - Física e Química".

const ROLE_SPLIT = /\s+(?:Docente|Não Docente|Nao Docente|Funcionári[oa])[-\s]/i

// Usual abbreviations of the recruitment groups (grupos de recrutamento)
const GROUP_ABBR: Record<string, string> = {
  '100': 'EPE', '110': '1.º CEB', '120': 'ING', '200': 'PHGP', '210': 'PF', '220': 'PI', '230': 'MCN',
  '240': 'EVT', '250': 'EM', '260': 'EF', '290': 'EMRC', '300': 'PORT', '310': 'LAT', '320': 'FR',
  '330': 'ING', '340': 'AL', '350': 'ESP', '400': 'HIST', '410': 'FIL', '420': 'GEO', '430': 'ECO',
  '500': 'MAT', '510': 'FQ', '520': 'BG', '530': 'ET', '540': 'ELT', '550': 'INF', '560': 'CAP',
  '600': 'AV', '610': 'MUS', '620': 'EF', '910': 'EE', '920': 'EE', '930': 'EE',
}
const SMALL_WORDS = new Set(['e', 'de', 'da', 'do', 'das', 'dos', 'a', 'o'])

// "Maria Leonor Marinho Nunes Serra Docente-510 - Física e Química" → "Maria Serra"
export function shortName(name?: string | null): string {
  if (!name) return ''
  const base = name.split(ROLE_SPLIT)[0].split(' - ')[0].trim()
  const parts = base.split(/\s+/).filter(Boolean)
  return parts.length > 2 ? `${parts[0]} ${parts[parts.length - 1]}` : base
}

// "… Docente-510 - Física e Química" → "510 FQ" ('' when the name has no recruitment group)
export function groupTag(name?: string | null): string {
  const m = (name ?? '').match(/Docente[-\s]*(\d{3})(?:\s*-\s*(.+))?$/i)
  if (!m) return ''
  const [, code, subject] = m
  let abbr = GROUP_ABBR[code] ?? ''
  if (!abbr && subject) {
    const words = subject.trim().split(/\s+/).filter((w) => !SMALL_WORDS.has(w.toLowerCase()))
    abbr = words.length > 1 ? words.map((w) => w[0]).join('').toUpperCase() : words[0]?.slice(0, 3).toUpperCase() ?? ''
  }
  return abbr ? `${code} ${abbr}` : code
}

// "Maria Serra · 510 FQ"
export function personLabel(name?: string | null): string {
  const tag = groupTag(name)
  return tag ? `${shortName(name)} · ${tag}` : shortName(name)
}
