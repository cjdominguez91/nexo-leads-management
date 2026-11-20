import { apiClient } from './client'
import type { AuthConfig, NexoUser, TokenResponse } from './types'

export function fetchAuthConfig() {
  return apiClient.get<AuthConfig>('/auth/config/').then((res) => res.data)
}

export function loginLocal(email: string, password: string) {
  return apiClient.post<TokenResponse>('/auth/login/local/', { email, password }).then((res) => res.data)
}

export function loginGoogle(idToken: string) {
  return apiClient.post<TokenResponse>('/auth/login/google/', { id_token: idToken }).then((res) => res.data)
}

export function fetchMe() {
  return apiClient.get<NexoUser>('/auth/me/').then((res) => res.data)
}

export function logout(refreshToken: string) {
  return apiClient.post('/auth/logout/', { refresh: refreshToken })
}
