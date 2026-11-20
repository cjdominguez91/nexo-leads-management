import { apiClient } from './client'
import type { Paginated } from './accounts'

export type CampaignFieldDataType = 'TEXTO' | 'NUMERO' | 'FECHA' | 'BOOLEANO' | 'SELECT' | 'MULTISELECT'
export type CampaignFieldOrigen = 'CARGA' | 'CAPTURA_GESTION'
export type CampaignModoCarga = 'MASIVA' | 'INDIVIDUAL'

export interface CampaignSection {
  id: number
  campaign_type: number
  nombre: string
  orden: number
  es_obligatoria: boolean
}

export interface CampaignFieldDefinition {
  id: number
  campaign_type: number
  field_key: string
  label: string
  data_type: CampaignFieldDataType
  origen: CampaignFieldOrigen
  required: boolean
  options: string[] | null
  orden: number
  mostrar_en_tabla: boolean
  mostrar_en_detalle: boolean
  seccion: number
  es_nombre_cliente: boolean
  es_telefono_contacto: boolean
  es_documento_identidad: boolean
}

export interface CampaignType {
  id: number
  nombre: string
  division: number
  division_nombre: string
  categoria: 'VENTAS' | 'COBROS'
  modo_carga: CampaignModoCarga
  secciones: CampaignSection[]
  field_definitions: CampaignFieldDefinition[]
}

export interface Campaign {
  id: number
  nombre: string
  campaign_type: number
  campaign_type_nombre: string
  campaign_type_modo_carga: CampaignModoCarga
  division: number
  division_nombre: string
  fecha_inicio: string
  fecha_fin: string | null
  estado: 'ACTIVA' | 'CERRADA'
  esta_cerrada: boolean
  producto_default: string
  agencias_habilitadas: number[]
  distritos_habilitados: number[]
}

export interface LoteCarga {
  id: number
  campaign: number
  usuario_carga: number
  usuario_carga_email: string
  nombre_archivo: string
  archivo: string
  cantidad_registros: number
  producto: string
  agencia_restriccion: number | null
  distrito_restriccion: number | null
  estado: 'PROCESANDO' | 'COMPLETADO' | 'ERROR'
  errores: { fila: number | null; error: string }[] | null
  created_at: string
}

export function fetchCampaignTypes(params?: { modo_carga?: CampaignModoCarga }) {
  return apiClient.get<Paginated<CampaignType>>('/campaigns/campaign-types/', { params }).then((res) => res.data)
}

export function fetchCampaignType(id: number) {
  return apiClient.get<CampaignType>(`/campaigns/campaign-types/${id}/`).then((res) => res.data)
}

/** `division` solo la usa ADMIN global; para ADMIN_DIVISION el backend fija la suya. */
export function createCampaignType(payload: {
  nombre: string
  division?: number | null
  categoria: 'VENTAS' | 'COBROS'
  modo_carga?: CampaignModoCarga
}) {
  return apiClient.post<CampaignType>('/campaigns/campaign-types/', payload).then((res) => res.data)
}

export function updateCampaignType(
  id: number,
  payload: Partial<{ nombre: string; categoria: 'VENTAS' | 'COBROS'; modo_carga: CampaignModoCarga }>,
) {
  return apiClient.patch<CampaignType>(`/campaigns/campaign-types/${id}/`, payload).then((res) => res.data)
}

export function deleteCampaignType(id: number) {
  return apiClient.delete(`/campaigns/campaign-types/${id}/`)
}

export function fetchSections(campaignTypeId: number) {
  return apiClient
    .get<Paginated<CampaignSection>>('/campaigns/sections/', { params: { campaign_type: campaignTypeId } })
    .then((res) => res.data)
}

export function createSection(payload: { campaign_type: number; nombre: string; orden: number }) {
  return apiClient.post<CampaignSection>('/campaigns/sections/', payload).then((res) => res.data)
}

export function updateSection(id: number, payload: Partial<{ nombre: string; orden: number }>) {
  return apiClient.patch<CampaignSection>(`/campaigns/sections/${id}/`, payload).then((res) => res.data)
}

export function deleteSection(id: number) {
  return apiClient.delete(`/campaigns/sections/${id}/`)
}

export function createFieldDefinition(payload: Partial<CampaignFieldDefinition>) {
  return apiClient.post<CampaignFieldDefinition>('/campaigns/field-definitions/', payload).then((res) => res.data)
}

export function updateFieldDefinition(id: number, payload: Partial<CampaignFieldDefinition>) {
  return apiClient.patch<CampaignFieldDefinition>(`/campaigns/field-definitions/${id}/`, payload).then((res) => res.data)
}

export function deleteFieldDefinition(id: number) {
  return apiClient.delete(`/campaigns/field-definitions/${id}/`)
}

export function setFieldFlag(
  id: number,
  flag: 'es_nombre_cliente' | 'es_telefono_contacto' | 'es_documento_identidad',
  value: boolean,
) {
  return apiClient
    .patch<CampaignFieldDefinition>(`/campaigns/field-definitions/${id}/`, { [flag]: value })
    .then((res) => res.data)
}

export function fetchCampaigns(params?: {
  campaign_type__modo_carga?: CampaignModoCarga
  search?: string
  ordering?: string
  page?: number
}) {
  return apiClient.get<Paginated<Campaign>>('/campaigns/campaigns/', { params }).then((res) => res.data)
}

export function fetchCampaign(id: number) {
  return apiClient.get<Campaign>(`/campaigns/campaigns/${id}/`).then((res) => res.data)
}

export function createCampaign(payload: {
  nombre: string
  campaign_type: number
  division: number
  fecha_inicio: string
  fecha_fin?: string | null
  estado?: string
  agencias_habilitadas?: number[]
  distritos_habilitados?: number[]
}) {
  return apiClient.post<Campaign>('/campaigns/campaigns/', payload).then((res) => res.data)
}

export function updateCampaign(
  id: number,
  payload: Partial<{
    nombre: string
    fecha_inicio: string
    fecha_fin: string | null
    estado: 'ACTIVA' | 'CERRADA'
    producto_default: string
    agencias_habilitadas: number[]
    distritos_habilitados: number[]
  }>,
) {
  return apiClient.patch<Campaign>(`/campaigns/campaigns/${id}/`, payload).then((res) => res.data)
}

export function deleteCampaign(id: number) {
  return apiClient.delete(`/campaigns/campaigns/${id}/`)
}

export function fetchLotesCarga(campaignId: number) {
  return apiClient
    .get<Paginated<LoteCarga>>('/campaigns/lotes-carga/', { params: { campaign: campaignId } })
    .then((res) => res.data)
}

export function uploadLoteCarga(
  campaignId: number,
  file: File,
  restricciones?: { agencia_restriccion?: number | null; distrito_restriccion?: number | null },
) {
  const formData = new FormData()
  formData.append('campaign', String(campaignId))
  formData.append('archivo', file)
  if (restricciones?.agencia_restriccion) {
    formData.append('agencia_restriccion', String(restricciones.agencia_restriccion))
  }
  if (restricciones?.distrito_restriccion) {
    formData.append('distrito_restriccion', String(restricciones.distrito_restriccion))
  }
  return apiClient
    .post<LoteCarga>('/campaigns/lotes-carga/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((res) => res.data)
}
