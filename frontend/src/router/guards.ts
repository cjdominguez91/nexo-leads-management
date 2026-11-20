import type { NavigationGuardWithThis } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

export const authGuard: NavigationGuardWithThis<undefined> = async (to) => {
  const authStore = useAuthStore()

  if (to.meta.public) {
    return true
  }

  if (!authStore.isAuthenticated) {
    if (localStorage.getItem('nexo_access_token') && !authStore.user) {
      try {
        await authStore.fetchCurrentUser()
      } catch {
        authStore.clearSession()
        return { name: 'login', query: { redirect: to.fullPath } }
      }
    } else {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
  }

  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && authStore.roleName && !allowedRoles.includes(authStore.roleName)) {
    return { name: 'home' }
  }

  return true
}
