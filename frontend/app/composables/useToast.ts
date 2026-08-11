export interface ToastAction {
  label: string
  to: string // rota para navegar ao clicar
}

export interface ToastMessage {
  id: number
  type: 'success' | 'error' | 'info'
  text: string
  action?: ToastAction
}

const _toasts = ref<ToastMessage[]>([])
let _id = 0

export const useToast = () => {
  const push = (type: ToastMessage['type'], text: string, timeout = 3500, action?: ToastAction) => {
    const id = ++_id
    _toasts.value.push({ id, type, text, action })
    setTimeout(() => {
      _toasts.value = _toasts.value.filter((t) => t.id !== id)
    }, timeout)
  }

  const dismiss = (id: number) => {
    _toasts.value = _toasts.value.filter((t) => t.id !== id)
  }

  return {
    toasts: _toasts,
    dismiss,
    success: (t: string) => push('success', t),
    // action opcional (ex.: botão "Ir ao perfil"); com ação, fica mais tempo na tela
    error: (t: string, action?: ToastAction) => push('error', t, action ? 8000 : 3500, action),
    info: (t: string) => push('info', t),
  }
}
