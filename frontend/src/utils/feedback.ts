// Shared feedback: readable error messages, error/success toasts and a confirmation dialog (instead of the
// browser's alert()/confirm(), which look out of place and ignore dark mode).
import { Dialog, Notify } from 'quasar'

/** A message for the user from an API error: the server's own text, or `fallback`. */
export function errorMessage(e: any, fallback = 'Ocorreu um erro. Tente novamente.'): string {
  const response = e?.response
  if (!response) {
    // No answer at all: offline, or the server is restarting
    return e?.code === 'ECONNABORTED' || e?.message === 'Network Error'
      ? 'Sem ligação ao servidor. Verifique a internet e tente novamente.'
      : fallback
  }
  const detail = response.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  // FastAPI validation errors come as a list
  if (Array.isArray(detail) && detail.length) return 'Há dados em falta ou inválidos no formulário.'
  if (response.status === 403) return 'Não tem permissão para esta ação.'
  if (response.status === 404) return 'Já não existe (pode ter sido apagado).'
  if (response.status === 429) return 'Demasiadas tentativas. Aguarde um pouco e tente novamente.'
  if (response.status >= 500) return 'Erro no servidor. Tente novamente dentro de momentos.'
  return fallback
}

export function notifyError(e: any, fallback?: string) {
  Notify.create({ type: 'negative', message: errorMessage(e, fallback), position: 'top', timeout: 5000 })
}

export function notifySuccess(message: string) {
  Notify.create({ type: 'positive', message, position: 'top', timeout: 2500 })
}

/** Ask before doing something. Resolves true when the person confirms. */
export function confirmDialog(message: string, opts: { title?: string; ok?: string; cancel?: string; danger?: boolean } = {}): Promise<boolean> {
  return new Promise((resolve) => {
    Dialog.create({
      title: opts.title,
      message,
      html: false,
      persistent: false,
      ok: { label: opts.ok ?? 'Confirmar', color: opts.danger ? 'negative' : 'primary', unelevated: true, noCaps: true },
      cancel: { label: opts.cancel ?? 'Cancelar', flat: true, noCaps: true, color: 'grey-8' },
      class: 'hd-confirm-dialog',
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false))
  })
}
