import type { MeUser } from './useMe'

export interface UpdateMePayload {
  name?: string
  phone?: string | null
  cpf?: string
  current_password?: string
  new_password?: string
}

export const useProfile = () => {
  const api = useApi()
  return {
    update: (payload: UpdateMePayload) =>
      api<MeUser>('/auth/me', { method: 'PUT', body: payload }),
    uploadAvatar: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return api<MeUser>('/auth/me/avatar', { method: 'POST', body: form })
    },
  }
}
