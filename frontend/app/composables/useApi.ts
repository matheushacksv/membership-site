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

  return $fetch.create({
    baseURL: config.public.apiBase,
    onRequest({ options }) {
      if (access.value) {
        const headers = new Headers(options.headers)
        headers.set('Authorization', `Bearer ${access.value}`)
        options.headers = headers
      }
    },
    async onResponseError({ response, request, options }) {
      if (response.status !== 401 || !refresh.value) return
      // Avoid infinite loop on the refresh endpoint itself
      if (String(request).includes('/auth/refresh')) return

      try {
        const data = await $fetch<TokenPair>('/auth/refresh', {
          baseURL: config.public.apiBase,
          method: 'POST',
          body: { refresh: refresh.value },
        })
        access.value = data.access
        refresh.value = data.refresh
      } catch {
        access.value = null
        refresh.value = null
        if (import.meta.client) {
          await navigateTo('/login')
        }
      }
    },
  })
}
