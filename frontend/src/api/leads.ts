import { apiClient } from './client'
import type { Paginated } from './accounts'
import type { Opportunity } from './opportunities'

export interface Lead {
  id: number
  campaign: number
  campaign_nombre: string
  lote_carga: number | null
  cliente_nombre: string
  telefono: string
  documento_identidad: string
  agencia: number
  agencia_nombre: string
  distrito: number | null
  usuario_asignado: number | null
  usuario_asignado_email: string | null
  fecha_asignacion: string | null
  estado: 'NUEVO' | 'ASIGNADO' | 'GESTIONADO' | 'GANADO' | 'PERDIDO'
  categoria_actual: number | null
  categoria_actual_nombre: string | null
  subcategoria_actual: number | null
  subcategoria_actual_nombre: string | null
  fecha_ultima_gestion: string | null
  monto_oferta: string | null
  atributos: Record<string, unknown>
  atributos_captura: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface Assignment {
  id: number
  lead: number
  usuario_origen: number | null
  usuario_origen_email: string | null
  usuario_destino: number
  usuario_destino_email: string
  agencia_origen: number | null
  agencia_origen_nombre: string | null
  agencia_destino: number | null
  agencia_destino_nombre: string | null
  asignado_por: number
  asignado_por_email: string
  timestamp: string
}

export interface Category {
  id: number
  nombre: string
  activo: boolean
}

export type SubCategoryEfecto = 'SIN_EFECTO' | 'ABRE_OPORTUNIDAD' | 'GANADA' | 'PERDIDA'

export interface SubCategory {
  id: number
  category: number
  category_nombre: string
  nombre: string
  efecto: SubCategoryEfecto
  efecto_display: string
  requiere_proximo_contacto: boolean
  activo: boolean
}

export interface ManagementLog {
  id: number
  lead: number
  usuario: number
  usuario_email: string
  category: number
  category_nombre: string
  subcategory: number | null
  subcategory_nombre: string | null
  comentario: string
  fecha_proximo_contacto: string | null
  timestamp: string
}

export interface CaptureEntry {
  id: number
  lead: number
  usuario: number
  usuario_email: string
  datos: Record<string, unknown>
  timestamp: string
}

export interface GestionarResult {
  log: ManagementLog
  opportunity: Opportunity | null
}

export interface AsignableUser {
  id: number
  email: string
  first_name: string
  last_name: string
  role_nombre: string | null
  agencia_principal_nombre: string | null
}

export function fetchUsuariosAsignables() {
  return apiClient.get<Paginated<AsignableUser>>('/leads/usuarios-asignables/').then((res) => res.data)
}

export function fetchLeads(
  campaignId: number,
  params?: { ordering?: string; page?: number } & Record<string, string | number | undefined>,
) {
  return apiClient
    .get<Paginated<Lead>>('/leads/leads/', { params: { campaign: campaignId, ...params } })
    .then((res) => res.data)
}

export function fetchLead(id: number) {
  return apiClient.get<Lead>(`/leads/leads/${id}/`).then((res) => res.data)
}

export function fetchCustodia(leadId: number) {
  return apiClient.get<Assignment[]>(`/leads/leads/${leadId}/custodia/`).then((res) => res.data)
}

export function asignarLead(leadId: number, usuarioDestino: number) {
  return apiClient
    .post<Assignment>(`/leads/leads/${leadId}/asignar/`, { usuario_destino: usuarioDestino })
    .then((res) => res.data)
}

export function asignarMasivo(leadIds: number[], usuarioDestino: number) {
  return apiClient
    .post('/leads/leads/asignar-masivo/', { lead_ids: leadIds, usuario_destino: usuarioDestino })
    .then((res) => res.data)
}

export function fetchCategories() {
  return apiClient.get<Paginated<Category>>('/leads/categories/').then((res) => res.data)
}

export function createCategory(payload: { nombre: string }) {
  return apiClient.post<Category>('/leads/categories/', payload).then((res) => res.data)
}

export function updateCategory(id: number, payload: Partial<{ nombre: string; activo: boolean }>) {
  return apiClient.patch<Category>(`/leads/categories/${id}/`, payload).then((res) => res.data)
}

export function fetchSubCategories() {
  return apiClient.get<Paginated<SubCategory>>('/leads/subcategories/').then((res) => res.data)
}

export function createSubCategory(payload: {
  category: number
  nombre: string
  efecto: SubCategoryEfecto
  requiere_proximo_contacto: boolean
}) {
  return apiClient.post<SubCategory>('/leads/subcategories/', payload).then((res) => res.data)
}

export function updateSubCategory(
  id: number,
  payload: Partial<{
    category: number
    nombre: string
    efecto: SubCategoryEfecto
    requiere_proximo_contacto: boolean
    activo: boolean
  }>,
) {
  return apiClient.patch<SubCategory>(`/leads/subcategories/${id}/`, payload).then((res) => res.data)
}

export function fetchEvolucion(leadId: number) {
  return apiClient.get<ManagementLog[]>(`/leads/leads/${leadId}/evolucion/`).then((res) => res.data)
}

export function fetchCapturas(leadId: number) {
  return apiClient.get<CaptureEntry[]>(`/leads/leads/${leadId}/capturas/`).then((res) => res.data)
}

export function fetchLeadOportunidad(leadId: number) {
  return apiClient.get<Opportunity | null>(`/leads/leads/${leadId}/oportunidad/`).then((res) => res.data)
}

export interface CrearProspectoResult {
  lead: Lead
  reclamado: boolean
}

export function crearProspecto(payload: { campaign: number; agencia?: number | null; atributos: Record<string, unknown> }) {
  return apiClient.post<CrearProspectoResult>('/leads/leads/', payload).then((res) => res.data)
}

export function gestionarLead(
  leadId: number,
  payload: {
    category: number
    subcategory?: number | null
    comentario: string
    fecha_proximo_contacto?: string | null
    datos_captura?: Record<string, unknown>
  },
) {
  return apiClient.post<GestionarResult>(`/leads/leads/${leadId}/gestionar/`, payload).then((res) => res.data)
}
