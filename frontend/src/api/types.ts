export type RoleName = 'ADMIN' | 'GERENTE' | 'SUPERVISOR' | 'JEFE' | 'SUBJEFE' | 'EJECUTIVO'

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
