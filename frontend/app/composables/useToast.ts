export interface ToastMessage {
  id: number
  type: 'success' | 'error' | 'info'
  text: string
}

const _toasts = ref<ToastMessage[]>([])
let _id = 0

export const useToast = () => {
  const push = (type: ToastMessage['type'], text: string, timeout = 3500) => {
    const id = ++_id
    _toasts.value.push({ id, type, text })
    setTimeout(() => {
      _toasts.value = _toasts.value.filter((t) => t.id !== id)
    }, timeout)
  }

  return {
    toasts: _toasts,
    success: (t: string) => push('success', t),
    error: (t: string) => push('error', t),
    info: (t: string) => push('info', t),
  }
}
