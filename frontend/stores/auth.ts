import { defineStore } from 'pinia'
import type { Company, Token, User } from '~/types/api'

/**
 * Session state.
 *
 * The token is kept in a cookie rather than localStorage so it survives a page
 * reload and is readable during SSR. That is acceptable for this application
 * because the API is same-site and the cookie is not readable by the server
 * logic on other origins; a cross-site deployment should move to an httpOnly
 * cookie issued by the backend.
 *
 * Role checks here are for navigation only. The API is the security boundary:
 * every endpoint re-checks the role server-side, so a user who forces a menu
 * entry into the DOM gains nothing.
 */
export const useAuthStore = defineStore('auth', () => {
  const token = useCookie<string | null>('erp_token', {
    sameSite: 'lax',
    maxAge: 60 * 60 * 12,
  })
  const activeCompany = useCookie<string | null>('erp_company', {
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 30,
  })

  const user = ref<User | null>(null)
  const companies = ref<Company[]>([])

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const role = computed(() => user.value?.role ?? null)

  function setSession(payload: Token) {
    token.value = payload.access_token
    activeCompany.value = payload.active_company
    user.value = payload.user
  }

  function setCompanies(list: Company[]) {
    companies.value = list
  }

  function clear() {
    token.value = null
    activeCompany.value = null
    user.value = null
    companies.value = []
  }

  function hasRole(...roles: string[]): boolean {
    if (!role.value) return false
    return roles.includes(role.value)
  }

  /**
   * Navigation visibility per role.
   *
   * Buyers do not fulfil orders, logistics do not raise them, and Quality only
   * inspects what logistics has received. Mirrors the matrix in the backend
   * README so the two stay easy to compare.
   */
  const navigation = computed(() => {
    const current = role.value
    const all = [
      { key: 'dashboard', to: '/', roles: ['admin', 'buyer', 'logistics', 'quality'] },
      { key: 'sales', to: '/sales', roles: ['admin', 'buyer', 'logistics'] },
      { key: 'purchases', to: '/purchases', roles: ['admin', 'buyer', 'logistics', 'quality'] },
      { key: 'warehouse', to: '/warehouse', roles: ['admin', 'logistics'] },
      { key: 'demand', to: '/demand', roles: ['admin', 'buyer'] },
      { key: 'routes', to: '/routes', roles: ['admin', 'logistics'] },
      { key: 'activity', to: '/activity', roles: ['admin', 'buyer', 'logistics', 'quality'] },
    ]
    if (!current) return []
    return all.filter((entry) => entry.roles.includes(current))
  })

  return {
    token,
    user,
    companies,
    activeCompany,
    isAuthenticated,
    role,
    navigation,
    setSession,
    setCompanies,
    clear,
    hasRole,
  }
})