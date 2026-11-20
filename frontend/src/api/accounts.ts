import { apiClient } from './client'
import type { NexoUser } from './types'

export interface Role {
  id: number
  nombre: string
  nombre_display: string
  nivel_jerarquico: number
  descripcion: string
}

export interface Division {
  id: number
  nombre: string
  codigo: string
  activo: boolean
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface UserCreatePayload {
  email: string
  first_name?: string
  last_name?: string
  codigo_empleado: string
  role?: number | null
  division?: number | null
  agencia_principal?: number | null
  password?: string
}

export function fetchUsers(params?: { ordering?: string; page?: number } & Record<string, string | number | undefined>) {
  return apiClient.get<Paginated<NexoUser>>('/auth/users/', { params }).then((res) => res.data)
}

export function createUser(payload: UserCreatePayload) {
  return apiClient.post<NexoUser>('/auth/users/', payload).then((res) => res.data)
}

export function setUserActive(userId: number, isActive: boolean) {
  return apiClient.patch<NexoUser>(`/auth/users/${userId}/`, { is_active: isActive }).then((res) => res.data)
}

export function updateUser(
  userId: number,
  payload: Partial<{
    email: string
    first_name: string
    last_name: string
    codigo_empleado: string
    role: number | null
    division: number | null
  }>,
) {
  return apiClient.patch<NexoUser>(`/auth/users/${userId}/`, payload).then((res) => res.data)
}

export function setAgenciaPrincipal(userId: number, agenciaId: number | null) {
  return apiClient.patch<NexoUser>(`/auth/users/${userId}/`, { agencia_principal: agenciaId }).then((res) => res.data)
}

export function fetchDivisions() {
  return apiClient.get<Paginated<Division>>('/auth/divisions/').then((res) => res.data)
}

export function createDivision(payload: { nombre: string; codigo: string }) {
  return apiClient.post<Division>('/auth/divisions/', payload).then((res) => res.data)
}

export function updateDivision(id: number, payload: Partial<{ nombre: string; codigo: string; activo: boolean }>) {
  return apiClient.patch<Division>(`/auth/divisions/${id}/`, payload).then((res) => res.data)
}

export function addUserAgencia(userId: number, agenciaId: number) {
  return apiClient.post(`/auth/users/${userId}/agencias/`, { agencia: agenciaId }).then((res) => res.data)
}

export function removeUserAgencia(userId: number, agenciaId: number) {
  return apiClient.delete(`/auth/users/${userId}/agencias/${agenciaId}/`)
}

export function addUserTerritorio(userId: number, territorioId: number) {
  return apiClient.post(`/auth/users/${userId}/territorios/`, { territorio: territorioId }).then((res) => res.data)
}

export function removeUserTerritorio(userId: number, territorioId: number) {
  return apiClient.delete(`/auth/users/${userId}/territorios/${territorioId}/`)
}

export function fetchRoles() {
  return apiClient.get<Paginated<Role>>('/auth/roles/').then((res) => res.data)
}
