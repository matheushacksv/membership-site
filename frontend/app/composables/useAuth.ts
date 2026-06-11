interface TokenPair {
  access: string
  refresh: string
}

const COOKIE_OPTS = {
  sameSite: 'lax' as const,
  secure: !import.meta.dev,
  path: '/',
}

export const useAuth = () => {
  const api = useApi()

  const access = useCookie<string | null>('access', {
    ...COOKIE_OPTS,
    maxAge: 60 * 30,
  })
  const refresh = useCookie<string | null>('refresh', {
    ...COOKIE_OPTS,
    maxAge: 60 * 60 * 24 * 7,
  })

  const isAuthenticated = computed(() => !!access.value || !!refresh.value)

  const login = async (email: string, password: string, redirect = '/') => {
    const data = await api<TokenPair>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    access.value = data.access
    refresh.value = data.refresh
    await navigateTo(redirect)
  }

  const register = async (email: string, password: string, name: string, redirect = '/') => {
    const data = await api<TokenPair>('/auth/register', {
      method: 'POST',
      body: { email, password, name },
    })
    access.value = data.access
    refresh.value = data.refresh
    await navigateTo(redirect)
  }

  const logout = async () => {
    access.value = null
    refresh.value = null
    await navigateTo('/login')
  }

  return { login, register, logout, isAuthenticated, access, refresh }
}
