const PUBLIC_ROUTES = new Set<string>([
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
])

const AUTH_ENTRY_ROUTES = new Set<string>(['/login', '/register'])

export default defineNuxtRouteMiddleware((to) => {
  const access = useCookie<string | null>('access')
  const isAuthenticated = !!access.value
  const isPublic = PUBLIC_ROUTES.has(to.path)

  if (!isAuthenticated && !isPublic) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }

  if (isAuthenticated && AUTH_ENTRY_ROUTES.has(to.path)) {
    return navigateTo('/')
  }
})
