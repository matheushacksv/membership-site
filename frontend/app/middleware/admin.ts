export default defineNuxtRouteMiddleware(async () => {
  const { data: me } = await useMe()
  if (!me.value?.is_staff) {
    return navigateTo('/')
  }
})
