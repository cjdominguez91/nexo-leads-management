import { apiClient } from './client'
import type { Paginated } from './accounts'

export interface Territorio {
  id: number
  nombre: string
  codigo: string
  division: number
  division_nombre: string
  activo: boolean
}

export interface Agencia {
  id: number
  nombre: string
  codigo: string
  territorio: number
  territorio_nombre: string
  /** Derivada del distrito (solo lectura). */
  division: number
  division_nombre: string
  activo: boolean
}

export function fetchTerritorios() {
  return apiClient.get<Paginated<Territorio>>('/geo/territorios/').then((res) => res.data)
}

/** `division` solo la usa ADMIN global; para ADMIN_DIVISION el backend fija la suya. */
export function createTerritorio(payload: { nombre: string; codigo: string; division?: number | null }) {
  return apiClient.post<Territorio>('/geo/territorios/', payload).then((res) => res.data)
}

export function updateTerritorio(id: number, payload: Partial<{ nombre: string; codigo: string; activo: boolean }>) {
  return apiClient.patch<Territorio>(`/geo/territorios/${id}/`, payload).then((res) => res.data)
}

export function fetchAgencias() {
  return apiClient.get<Paginated<Agencia>>('/geo/agencias/').then((res) => res.data)
}

export function createAgencia(payload: { nombre: string; codigo: string; territorio: number }) {
  return apiClient.post<Agencia>('/geo/agencias/', payload).then((res) => res.data)
}

export function updateAgencia(
  id: number,
  payload: Partial<{ nombre: string; codigo: string; territorio: number; activo: boolean }>,
) {
  return apiClient.patch<Agencia>(`/geo/agencias/${id}/`, payload).then((res) => res.data)
}
