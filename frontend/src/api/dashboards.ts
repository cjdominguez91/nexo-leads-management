import { apiClient } from './client'

export interface DashboardFiltros {
  campaign?: number
  agencia?: number
  distrito?: number
  usuario_asignado?: number
  fecha_desde?: string
  fecha_hasta?: string
}

export interface ResumenDashboard {
  total: number
  por_estado: Record<'NUEVO' | 'ASIGNADO' | 'GESTIONADO' | 'GANADO' | 'PERDIDO', number>
  por_categoria: { categoria: string; cantidad: number }[]
  por_subcategoria: { subcategoria: string; cantidad: number }[]
  tasa_contacto: number
  tasa_efectividad: number
  tasa_conversion: number
  sin_gestionar_hace_mas_de_7_dias: number
  sin_asignar: number
  campanas_activas: number
  leads_activos: number
  tiempo_promedio_primera_gestion_horas: number | null
  variacion: { tasa_contacto: number; tasa_efectividad: number } | null
}

export interface TendenciaDashboard {
  gestiones_por_dia: { fecha: string; cantidad: number }[]
  ganadas_por_dia: { fecha: string; cantidad: number }[]
}

export type AgruparPor = 'campaign' | 'distrito' | 'agencia' | 'usuario_asignado'

export interface EfectividadRow {
  id: number
  nombre: string
  total: number
  contactados: number
  tasa_contacto: number
  ganados: number
  tasa_efectividad: number
  perdidos: number
}

export function fetchResumen(filtros?: DashboardFiltros) {
  return apiClient.get<ResumenDashboard>('/dashboards/resumen/', { params: filtros }).then((res) => res.data)
}

export function fetchTendencia(filtros?: DashboardFiltros & { dias?: number }) {
  return apiClient.get<TendenciaDashboard>('/dashboards/tendencia/', { params: filtros }).then((res) => res.data)
}

export function fetchEfectividad(agruparPor: AgruparPor, filtros?: DashboardFiltros) {
  return apiClient
    .get<EfectividadRow[]>('/dashboards/efectividad/', { params: { agrupar_por: agruparPor, ...filtros } })
    .then((res) => res.data)
}
