export function parseServerDate(value: string) {
  if (!value) return new Date(NaN)
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value)
  return new Date(hasTimezone ? value : `${value}Z`)
}

export function formatDateTime(value: string) {
  return parseServerDate(value).toLocaleString('pt-PT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function timeAgo(value: string) {
  const diff = Date.now() - parseServerDate(value).getTime()
  const hours = Math.max(0, Math.floor(diff / 3600000))
  if (hours < 1) return 'agora'
  if (hours < 24) return `há ${hours}h`
  return `há ${Math.floor(hours / 24)} d`
}
