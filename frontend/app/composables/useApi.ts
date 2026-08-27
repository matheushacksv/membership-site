import { $fetch } from 'ofetch'

interface TokenPair {
  access: string
  refresh: string
}

const COOKIE_OPTS = {
  sameSite: 'lax' as const,
  secure: !import.meta.dev,
  path: '/',
}

export const useApi = () => {
  const config = useRuntimeConfig()
  const access = useCookie<string | null>('access', {
    ...COOKIE_OPTS,
    maxAge: 60 * 30,
  })
  const refresh = useCookie<string | null>('refresh', {
    ...COOKIE_OPTS,
    maxAge: 60 * 60 * 24 * 7,
  })

  const nuxtApp = useNuxtApp()

  const build = (opts: Record<string, any>, token: string | null) => ({
    baseURL: config.public.apiBase,
    ...opts,
    headers: {
      ...(opts.headers || {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })

  // Single-flight: várias requests que estouram 401 ao mesmo tempo compartilham
  // UM refresh, evitando refreshes concorrentes (e o warn de override do cookie).
  // Guardado no nuxtApp (per-request no server) p/ não vazar token entre usuários no SSR.
  const doRefresh = (): Promise<TokenPair> => {
    const app = nuxtApp as any
    if (!app._authRefresh) {
      app._authRefresh = $fetch<TokenPair>('/auth/refresh', {
        baseURL: config.public.apiBase,
        method: 'POST',
        body: { refresh: refresh.value },
      }).finally(() => {
        app._authRefresh = null
      })
    }
    return app._authRefresh
  }

  // Wrapper: no 401, faz refresh e RETENTA a request original uma vez com o token novo.
  // Assim o access curto (30 min) fica transparente, o caller nunca vê o 401 de expiração.
  return async <T>(request: any, opts: Record<string, any> = {}): Promise<T> => {
    try {
      return await $fetch<T>(request, build(opts, access.value))
    } catch (e: any) {
      const is401 = e?.response?.status === 401
      const isRefreshCall = String(request).includes('/auth/refresh')
      if (!is401 || !refresh.value || isRefreshCall) throw e

      try {
        const data = await doRefresh()
        access.value = data.access
        refresh.value = data.refresh
        return await $fetch<T>(request, build(opts, data.access))
      } catch {
        access.value = null
        refresh.value = null
        if (import.meta.client) {
          await navigateTo('/login')
        }
        throw e
      }
    }
  }
}
