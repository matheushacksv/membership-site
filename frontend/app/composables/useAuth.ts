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

  // Grava a sessão (cookies). Reusado por login/register e pela LP de curso grátis.
  const setSession = (tokens: TokenPair) => {
    access.value = tokens.access
    refresh.value = tokens.refresh
  }

  const login = async (email: string, password: string, redirect = '/') => {
    const data = await api<TokenPair>('/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    setSession(data)
    await navigateTo(redirect)
  }

  const register = async (email: string, password: string, name: string, redirect = '/') => {
    const data = await api<TokenPair>('/auth/register', {
      method: 'POST',
      body: { email, password, name },
    })
    setSession(data)
    await navigateTo(redirect)
  }

  const logout = async () => {
    access.value = null
    refresh.value = null
    await navigateTo('/login')
  }

  return { login, register, logout, setSession, isAuthenticated, access, refresh }
}
