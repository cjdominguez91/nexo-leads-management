import { apiClient } from './client'
import type { Paginated } from './accounts'

export type OpportunityEstado = 'EN_PROGRESO' | 'GANADA' | 'PERDIDA'
export type OpportunityPrioridad = 'ALTA' | 'MEDIA' | 'BAJA'

export interface Opportunity {
  id: number
  lead: number
  cliente_nombre: string
  documento_identidad: string
  campaign: number
  campaign_nombre: string
  modo_carga: 'MASIVA' | 'INDIVIDUAL'
  categoria_actual_nombre: string | null
  subcategoria_actual_nombre: string | null
  usuario_responsable: number
  usuario_responsable_email: string
  prioridad: OpportunityPrioridad
  estado: OpportunityEstado
  fecha_cierre: string | null
  fecha_proximo_contacto: string | null
  created_at: string
  updated_at: string
}

export function fetchOpportunities(
  params?: { ordering?: string; page?: number } & Record<string, string | number | undefined>,
) {
  return apiClient.get<Paginated<Opportunity>>('/opportunities/opportunities/', { params }).then((res) => res.data)
}

export function setOpportunityPrioridad(id: number, prioridad: OpportunityPrioridad) {
  return apiClient
    .post<Opportunity>(`/opportunities/opportunities/${id}/prioridad/`, { prioridad })
    .then((res) => res.data)
}
