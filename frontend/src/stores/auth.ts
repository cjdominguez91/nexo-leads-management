import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '@/api/auth'
import type { AuthConfig, NexoUser } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<NexoUser | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('nexo_access_token'))
  const config = ref<AuthConfig | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value))
  const roleName = computed(() => user.value?.role_nombre ?? null)

  function persistTokens(access: string, refresh: string) {
    localStorage.setItem('nexo_access_token', access)
    localStorage.setItem('nexo_refresh_token', refresh)
    accessToken.value = access
  }

  function clearSession() {
    localStorage.removeItem('nexo_access_token')
    localStorage.removeItem('nexo_refresh_token')
    accessToken.value = null
    user.value = null
  }

  async function loadConfig() {
    config.value = await authApi.fetchAuthConfig()
    return config.value
  }

  async function loginLocal(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.loginLocal(email, password)
      persistTokens(data.access, data.refresh)
      user.value = data.user
    } catch (err: any) {
      error.value = err?.response?.data?.detail ?? 'No se pudo iniciar sesión.'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function loginGoogle(idToken: string) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.loginGoogle(idToken)
      persistTokens(data.access, data.refresh)
      user.value = data.user
    } catch (err: any) {
      error.value = err?.response?.data?.detail ?? 'No se pudo iniciar sesión con Google.'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrentUser() {
    user.value = await authApi.fetchMe()
    return user.value
  }

  async function logout() {
    const refreshToken = localStorage.getItem('nexo_refresh_token')
    try {
      if (refreshToken) await authApi.logout(refreshToken)
    } finally {
      clearSession()
    }
  }

  return {
    user,
    accessToken,
    config,
    loading,
    error,
    isAuthenticated,
    roleName,
    loadConfig,
    loginLocal,
    loginGoogle,
    fetchCurrentUser,
    logout,
    clearSession,
  }
})
