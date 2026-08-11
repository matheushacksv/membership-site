export interface MeUser {
  id: number
  name: string | null
  email: string
  phone: string | null
  cpf: string
  avatar: string | null
  is_staff: boolean
}

export const useMe = () => {
  const api = useApi()
  return useAsyncData<MeUser>('me', () => api<MeUser>('/auth/me'))
}
