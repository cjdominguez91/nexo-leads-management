export type RoleName = 'ADMIN' | 'ADMIN_DIVISION' | 'GERENTE' | 'SUPERVISOR' | 'JEFE' | 'SUBJEFE' | 'EJECUTIVO'

/** Roles que administran (usuarios, catálogos, campañas). ADMIN_DIVISION, solo su división. */
export const ADMIN_ROLES: RoleName[] = ['ADMIN', 'ADMIN_DIVISION']

/** Roles que un ADMIN_DIVISION puede asignar (espejo de backend/accounts/constants.py). */
export const ROLES_GESTIONABLES_POR_ADMIN_DIVISION: RoleName[] = ['GERENTE', 'SUPERVISOR', 'JEFE', 'SUBJEFE', 'EJECUTIVO']

export interface AuthConfig {
  google_enabled: boolean
  local_enabled: boolean
  google_client_id: string
}

export interface UserAgenciaAsignacion {
  id: number
  agencia: number
  agencia_nombre: string
  fecha_asignacion: string
  activo: boolean
}

export interface UserTerritorioAsignacion {
  id: number
  territorio: number
  territorio_nombre: string
  fecha_asignacion: string
  activo: boolean
}

export interface NexoUser {
  id: number
  email: string
  first_name: string
  last_name: string
  codigo_empleado: string | null
  role: number | null
  role_nombre: RoleName | null
  division: number | null
  division_nombre: string | null
  agencia_principal: number | null
  agencia_principal_nombre: string | null
  auth_provider: 'google' | 'local'
  avatar_url: string
  is_active: boolean
  is_superuser: boolean
  date_joined: string
  last_login: string | null
  agencias: UserAgenciaAsignacion[]
  territorios: UserTerritorioAsignacion[]
}

export interface TokenResponse {
  access: string
  refresh: string
  user: NexoUser
}
