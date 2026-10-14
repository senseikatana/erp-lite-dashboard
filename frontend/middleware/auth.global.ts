/**
 * Route guard.
 *
 * Redirects to the login page when there is no session, and blocks pages the
 * caller's role has no business opening. The role check is a convenience that
 * avoids showing a screen which would immediately fail; the API enforces the
 * same rules for real.
 */
export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuthStore()

  if (to.path === '/login') {
    if (auth.token) {
      return navigateTo('/')
    }
    return
  }

  if (!auth.token) {
    return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
  }

  // Restore the user and company list on a hard reload, where Pinia starts empty
  // but the token cookie survives.
  if (!auth.user) {
    try {
      const api = useApi()
      auth.user = await api.get('/auth/me')
      auth.setCompanies(await api.get('/companies'))
    } catch {
      auth.clear()
      return navigateTo({ path: '/login', query: { redirect: to.fullPath } })
    }
  }

  const allowed = auth.navigation.some(
    (entry) => entry.to === to.path || (entry.to !== '/' && to.path.startsWith(entry.to)),
  )

  if (!allowed && to.path !== '/') {
    return navigateTo('/')
  }
})