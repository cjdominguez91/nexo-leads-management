import { apiClient } from './client'
import type { Paginated } from './accounts'

export type NotificationTipo = 'ASIGNACION_RECIBIDA' | 'OPORTUNIDAD_CREADA' | 'OPORTUNIDAD_CERRADA'

export interface AsignacionPayload {
  campaign_id: number
  campaign_nombre: string
  campaign_modo_carga: 'MASIVA' | 'INDIVIDUAL'
  cantidad: number
  motivo: string
}

export interface OportunidadPayload {
  lead_id: number
  cliente_nombre: string
  campaign_id: number
  campaign_nombre: string
  opportunity_id: number
  estado: 'EN_PROGRESO' | 'GANADA' | 'PERDIDA'
}

interface NotificationBase {
  id: number
  leido: boolean
  created_at: string
}

// Unión discriminada por `tipo` (no una interfaz con `payload` unionado
// aparte) — así `if (n.tipo === 'ASIGNACION_RECIBIDA')` estrecha `n.payload`
// de verdad en vez de dejarlo como la unión completa.
export type AppNotification =
  | (NotificationBase & { tipo: 'ASIGNACION_RECIBIDA'; payload: AsignacionPayload })
  | (NotificationBase & { tipo: 'OPORTUNIDAD_CREADA' | 'OPORTUNIDAD_CERRADA'; payload: OportunidadPayload })

export function fetchNotifications(params?: { leido?: boolean }) {
  return apiClient
    .get<Paginated<AppNotification>>('/notifications/notifications/', { params })
    .then((res) => res.data)
}

export function marcarLeida(id: number) {
  return apiClient
    .post<AppNotification>(`/notifications/notifications/${id}/marcar-leida/`)
    .then((res) => res.data)
}

export function marcarTodasLeidas() {
  return apiClient.post('/notifications/notifications/marcar-todas-leidas/')
}

export function buildNotificationsSocketUrl(token: string): string {
  const httpBase = apiClient.defaults.baseURL ?? 'http://localhost:8000/api'
  const wsBase = httpBase.replace(/^http/, 'ws').replace(/\/api\/?$/, '')
  return `${wsBase}/ws/notifications/?token=${encodeURIComponent(token)}`
}
