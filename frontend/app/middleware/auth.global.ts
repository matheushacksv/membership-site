const PUBLIC_ROUTES = new Set<string>([
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
  '/magic',
])

const AUTH_ENTRY_ROUTES = new Set<string>(['/login', '/register'])

export default defineNuxtRouteMiddleware((to) => {
  const access = useCookie<string | null>('access')
  const refresh = useCookie<string | null>('refresh')
  // Access pode expirar (30 min) com refresh ainda válido (7 dias): deixa passar.
  // A camada useApi faz refresh-and-retry na primeira chamada e restaura o access.
  const isAuthenticated = !!access.value || !!refresh.value
  // LP de curso grátis é pública e dinâmica (/lp/<slug>) — Set não cobre, checa prefixo.
  const isPublic = PUBLIC_ROUTES.has(to.path) || to.path.startsWith('/lp/')

  if (!isAuthenticated && !isPublic) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }

  if (isAuthenticated && AUTH_ENTRY_ROUTES.has(to.path)) {
    return navigateTo('/')
  }
})
