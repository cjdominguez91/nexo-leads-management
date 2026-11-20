<script setup lang="ts">
import { ArrowDown, ArrowUp, ArrowUpDown, Layers, Lock, UserPlus, Users as UsersIcon } from '@lucide/vue'
import { createColumnHelper, FlexRender, getCoreRowModel, useVueTable } from '@tanstack/vue-table'
import { computed, onMounted, ref } from 'vue'

import * as accountsApi from '@/api/accounts'
import type { Division, Role } from '@/api/accounts'
import { ROLES_GESTIONABLES_POR_ADMIN_DIVISION } from '@/api/types'
import type { NexoUser } from '@/api/types'
import * as geoApi from '@/api/geo'
import type { Agencia, Territorio } from '@/api/geo'
import ActionButton from '@/components/ActionButton.vue'
import MultiSelectPicker from '@/components/MultiSelectPicker.vue'
import SingleSelectPicker from '@/components/SingleSelectPicker.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import TablePagination from '@/components/TablePagination.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useAuthStore } from '@/stores/auth'

// Igual que en DynamicTable.vue: guarda el query param de filtro de cada
// columna en su columnDef (meta.filterParam).
declare module '@tanstack/vue-table' {
  interface ColumnMeta<TData, TValue> {
    filterParam?: string
  }
}

const confirm = useConfirm()
const authStore = useAuthStore()

// ADMIN global elige división y cualquier rol. ADMIN_DIVISION: división fija
// (la suya) y solo roles de Gerente hacia abajo. Es solo UI: el backend
// rechaza cualquier otra cosa igual (accounts.serializers).
const esAdminGlobal = computed(() => authStore.isGlobalAdmin)
const rolesAsignables = computed(() =>
  esAdminGlobal.value ? roles.value : roles.value.filter((r) => ROLES_GESTIONABLES_POR_ADMIN_DIVISION.includes(r.nombre as never)),
)
function puedoGestionar(user: NexoUser) {
  return esAdminGlobal.value || !user.role_nombre || ROLES_GESTIONABLES_POR_ADMIN_DIVISION.includes(user.role_nombre)
}
const ROLES_TODA_LA_DIVISION = ['ADMIN_DIVISION', 'GERENTE']

// Un color por nivel jerárquico: de más poder (violeta/índigo) a operación (gris).
const ROLE_LABEL: Record<string, string> = {
  ADMIN: 'Administrador',
  ADMIN_DIVISION: 'Admin de división',
  GERENTE: 'Gerente',
  SUPERVISOR: 'Supervisor',
  JEFE: 'Jefe',
  SUBJEFE: 'Subjefe',
  EJECUTIVO: 'Ejecutivo',
}
const ROLE_BADGE: Record<string, string> = {
  ADMIN: 'bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-300',
  ADMIN_DIVISION: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300',
  GERENTE: 'bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300',
  SUPERVISOR: 'bg-teal-100 text-teal-700 dark:bg-teal-500/15 dark:text-teal-300',
  JEFE: 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300',
  SUBJEFE: 'bg-orange-100 text-orange-700 dark:bg-orange-500/15 dark:text-orange-300',
  EJECUTIVO: 'bg-slate-100 text-slate-600 dark:bg-slate-700/50 dark:text-slate-300',
}

const users = ref<NexoUser[]>([])
const usersCount = ref(0)
const usersColumnFilters = ref<Record<string, string>>({})
const usersOrdering = ref('email')
const usersPage = ref(1)
const usersPageSize = 25
let usersFilterDebounce: ReturnType<typeof setTimeout> | null = null

const roles = ref<Role[]>([])
const divisions = ref<Division[]>([])
const agencias = ref<Agencia[]>([])
const territorios = ref<Territorio[]>([])
const loading = ref(false)
const submitting = ref(false)
const formError = ref<string | null>(null)
const scopeError = ref<string | null>(null)
const expandedUserId = ref<number | null>(null)

const pendingAgenciaPrincipal = ref<number | null>(null)
const pendingAgenciasSet = ref<number[]>([])
const pendingTerritoriosSet = ref<number[]>([])
// Filtro de solo-UI para acortar la lista de agencias al buscar — no se
// guarda en ningún lado, un JEFE puede terminar con agencias en distintos
// distritos aunque las haya agregado filtrando por uno a la vez.
const pendingAgenciaDistrito = ref<number | null>(null)

const editingUserId = ref<number | null>(null)
const editForm = ref({
  email: '',
  first_name: '',
  last_name: '',
  codigo_empleado: '',
  role: null as number | null,
  division: null as number | null,
})
const editError = ref<string | null>(null)

const form = ref({
  email: '',
  first_name: '',
  last_name: '',
  codigo_empleado: '',
  role: null as number | null,
  division: null as number | null,
  agencia_principal: null as number | null,
  password: '',
})

const selectedRoleNombre = computed(() => roles.value.find((r) => r.id === form.value.role)?.nombre ?? null)

// En el panel de "Alcance", solo agencias/distritos de la división del usuario
// que se está editando (el backend rechaza asignar de otra división).
const expandedUser = computed(() => users.value.find((u) => u.id === expandedUserId.value) ?? null)
const territoriosDeLaDivision = computed(() =>
  territorios.value.filter((t) => !expandedUser.value?.division || t.division === expandedUser.value.division),
)
const agenciasFiltradas = computed(() =>
  agencias.value
    .filter((a) => !expandedUser.value?.division || a.division === expandedUser.value.division)
    .filter((a) => !pendingAgenciaDistrito.value || a.territorio === pendingAgenciaDistrito.value),
)
const agenciaPickerOptions = computed(() => agenciasFiltradas.value.map((a) => ({ id: a.id, label: a.nombre })))
const territorioPickerOptions = computed(() => territoriosDeLaDivision.value.map((t) => ({ id: t.id, label: t.nombre })))
// En el alta, la agencia de un EJECUTIVO debe ser de la división elegida.
const agenciasAlta = computed(() => {
  const division = esAdminGlobal.value ? form.value.division : authStore.user?.division
  return division ? agencias.value.filter((a) => a.division === division) : agencias.value
})

function usersParams() {
  return {
    ordering: usersOrdering.value || undefined,
    page: usersPage.value,
    ...usersColumnFilters.value,
  }
}

async function loadUsers() {
  const res = await accountsApi.fetchUsers(usersParams())
  users.value = res.results
  usersCount.value = res.count
}

function onUsersFilterInput(filterParam: string, event: Event) {
  const value = (event.target as HTMLInputElement).value
  usersColumnFilters.value = { ...usersColumnFilters.value, [filterParam]: value }
  if (usersFilterDebounce) clearTimeout(usersFilterDebounce)
  usersFilterDebounce = setTimeout(() => {
    usersPage.value = 1
    loadUsers()
  }, 350)
}

function handleUsersSort(ordering: string) {
  usersOrdering.value = ordering
  usersPage.value = 1
  loadUsers()
}

function handleUsersPage(page: number) {
  usersPage.value = page
  loadUsers()
}

// Solo las cabeceras de esta tabla vienen de TanStack (orden + fila de
// filtros) — el cuerpo se sigue armando a mano con `users` porque varias
// columnas (Correo+código, Alcance, Estado) necesitan markup condicional
// que no vale la pena forzar dentro de un cell renderer genérico.
const columnHelper = createColumnHelper<NexoUser>()
const columns = [
  columnHelper.accessor('email', { id: 'email', header: 'Correo', meta: { filterParam: 'email' } }),
  columnHelper.accessor('role_nombre', { id: 'role__nombre', header: 'Rol', meta: { filterParam: 'role__nombre' } }),
  columnHelper.accessor('division_nombre', {
    id: 'division__nombre',
    header: 'División',
    meta: { filterParam: 'division__nombre' },
  }),
  columnHelper.display({ id: 'alcance', header: 'Alcance', enableSorting: false }),
  columnHelper.accessor('is_active', { id: 'is_active', header: 'Estado' }),
  columnHelper.display({ id: 'acciones', header: '', enableSorting: false }),
]

const sortColumnId = ref<string | null>('email')
const sortDesc = ref(false)

const table = useVueTable({
  get data() {
    return users.value
  },
  columns,
  getCoreRowModel: getCoreRowModel(),
  manualSorting: true,
  enableMultiSort: false,
  state: {
    get sorting() {
      return sortColumnId.value ? [{ id: sortColumnId.value, desc: sortDesc.value }] : []
    },
  },
  onSortingChange: (updater) => {
    const current = sortColumnId.value ? [{ id: sortColumnId.value, desc: sortDesc.value }] : []
    const next = typeof updater === 'function' ? updater(current) : updater
    const first = next[0]
    sortColumnId.value = first?.id ?? null
    sortDesc.value = first?.desc ?? false
    handleUsersSort(first ? `${first.desc ? '-' : ''}${first.id}` : '')
  },
})

async function loadData() {
  loading.value = true
  try {
    const [rolesRes, divisionsRes, agenciasRes, territoriosRes] = await Promise.all([
      accountsApi.fetchRoles(),
      accountsApi.fetchDivisions(),
      geoApi.fetchAgencias(),
      geoApi.fetchTerritorios(),
      loadUsers(),
    ])
    roles.value = rolesRes.results
    divisions.value = divisionsRes.results
    agencias.value = agenciasRes.results
    territorios.value = territoriosRes.results
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  formError.value = null
  submitting.value = true
  try {
    await accountsApi.createUser({
      ...form.value,
      role: form.value.role || undefined,
      agencia_principal: selectedRoleNombre.value === 'EJECUTIVO' ? form.value.agencia_principal : undefined,
    })
    form.value = {
      email: '',
      first_name: '',
      last_name: '',
      codigo_empleado: '',
      role: null,
      division: null,
      agencia_principal: null,
      password: '',
    }
    await loadUsers()
  } catch (err: any) {
    formError.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear el usuario.')
  } finally {
    submitting.value = false
  }
}

async function toggleActive(user: NexoUser) {
  if (user.is_active && !(await confirm({ title: `¿Desactivar a "${user.email}"?`, message: 'Deja de poder iniciar sesión y de recibir asignaciones.' }))) {
    return
  }
  await accountsApi.setUserActive(user.id, !user.is_active)
  await loadUsers()
}

function toggleExpand(user: NexoUser) {
  expandedUserId.value = expandedUserId.value === user.id ? null : user.id
  pendingAgenciaPrincipal.value = user.agencia_principal
  pendingAgenciaDistrito.value = null
  pendingAgenciasSet.value = user.agencias.filter((a) => a.activo).map((a) => a.agencia)
  pendingTerritoriosSet.value = user.territorios.filter((t) => t.activo).map((t) => t.territorio)
  scopeError.value = null
}

function startEditUser(user: NexoUser) {
  editingUserId.value = user.id
  editForm.value = {
    email: user.email,
    first_name: user.first_name,
    last_name: user.last_name,
    codigo_empleado: user.codigo_empleado ?? '',
    role: user.role,
    division: user.division,
  }
  editError.value = null
}

function cancelEditUser() {
  editingUserId.value = null
}

async function saveEditUser(user: NexoUser) {
  editError.value = null
  try {
    await accountsApi.updateUser(user.id, editForm.value)
    editingUserId.value = null
    await loadUsers()
  } catch (err: any) {
    editError.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar el usuario.')
  }
}

async function handleSetAgenciaPrincipal(user: NexoUser) {
  scopeError.value = null
  try {
    await accountsApi.setAgenciaPrincipal(user.id, pendingAgenciaPrincipal.value)
    await loadUsers()
  } catch (err: any) {
    scopeError.value = JSON.stringify(err?.response?.data ?? 'No se pudo actualizar la agencia.')
  }
}

async function handleSaveAgencias(user: NexoUser) {
  scopeError.value = null
  const current = new Set(user.agencias.filter((a) => a.activo).map((a) => a.agencia))
  const next = new Set(pendingAgenciasSet.value)
  const toAdd = [...next].filter((id) => !current.has(id))
  const toRemove = [...current].filter((id) => !next.has(id))
  if (toAdd.length === 0 && toRemove.length === 0) return
  try {
    await Promise.all([
      ...toAdd.map((id) => accountsApi.addUserAgencia(user.id, id)),
      ...toRemove.map((id) => accountsApi.removeUserAgencia(user.id, id)),
    ])
    await loadUsers()
  } catch (err: any) {
    scopeError.value = JSON.stringify(err?.response?.data ?? 'No se pudieron guardar las agencias.')
  }
}

async function handleSaveTerritorios(user: NexoUser) {
  scopeError.value = null
  const current = new Set(user.territorios.filter((t) => t.activo).map((t) => t.territorio))
  const next = new Set(pendingTerritoriosSet.value)
  const toAdd = [...next].filter((id) => !current.has(id))
  const toRemove = [...current].filter((id) => !next.has(id))
  if (toAdd.length === 0 && toRemove.length === 0) return
  try {
    await Promise.all([
      ...toAdd.map((id) => accountsApi.addUserTerritorio(user.id, id)),
      ...toRemove.map((id) => accountsApi.removeUserTerritorio(user.id, id)),
    ])
    await loadUsers()
  } catch (err: any) {
    scopeError.value = JSON.stringify(err?.response?.data ?? 'No se pudieron guardar los distritos.')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-8">
    <div class="flex items-start gap-3">
      <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-600/15 dark:text-primary-500">
        <UsersIcon :size="20" />
      </span>
      <div>
        <h1 class="text-xl font-semibold text-slate-700 dark:text-slate-200">Usuarios</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400">
          Alta, rol, alcance territorial y activación de cuentas{{ esAdminGlobal ? '' : ` de ${authStore.user?.division_nombre ?? 'tu división'}` }}.
        </p>
      </div>
    </div>

    <form class="card grid max-w-2xl grid-cols-2 gap-3 p-4" @submit.prevent="handleCreate">
      <input v-model="form.email" type="email" placeholder="Correo" required class="col-span-2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <input v-model="form.first_name" placeholder="Nombre" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <input v-model="form.last_name" placeholder="Apellido" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <input
        v-model="form.codigo_empleado"
        placeholder="Código de empleado"
        required
        class="col-span-2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
      />
      <select v-model="form.role" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option :value="null">Sin rol</option>
        <option v-for="role in rolesAsignables" :key="role.id" :value="role.id">{{ role.nombre_display }}</option>
      </select>
      <select v-if="esAdminGlobal" v-model="form.division" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option :value="null">División…</option>
        <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.nombre }}</option>
      </select>
      <div v-else class="flex items-center gap-2 rounded-md border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-500 dark:border-slate-700">
        <Layers :size="14" class="text-accent-600" />
        {{ authStore.user?.division_nombre }}
      </div>
      <select
        v-if="selectedRoleNombre === 'EJECUTIVO'"
        v-model="form.agencia_principal"
        class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
      >
        <option :value="null">Agencia (obligatoria para EJECUTIVO)…</option>
        <option v-for="a in agenciasAlta" :key="a.id" :value="a.id">{{ a.nombre }}</option>
      </select>
      <p v-else-if="selectedRoleNombre && ['JEFE', 'SUBJEFE', 'SUPERVISOR'].includes(selectedRoleNombre)" class="col-span-2 text-xs text-slate-400">
        {{ selectedRoleNombre === 'SUPERVISOR' ? 'Los distritos' : 'Las agencias' }} se asignan después de crear el usuario, desde "Alcance" en la tabla de abajo — un {{ selectedRoleNombre.toLowerCase() }} puede cubrir varios.
      </p>
      <input v-model="form.password" type="password" placeholder="Contraseña (login local)" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <button type="submit" :disabled="submitting" class="col-span-2 inline-flex items-center justify-center gap-1.5 rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-sm font-medium text-white disabled:opacity-50">
        <UserPlus :size="16" />
        {{ submitting ? 'Creando…' : 'Crear usuario' }}
      </button>
      <p v-if="formError" class="col-span-2 text-xs text-red-600">{{ formError }}</p>
    </form>

    <div class="card overflow-x-auto">
    <table class="data-table">
      <thead class="text-slate-500 dark:text-slate-400">
        <tr v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
          <th
            v-for="header in headerGroup.headers"
            :key="header.id"
            class="border-b border-slate-200 pb-2 dark:border-slate-800"
            :class="{ 'cursor-pointer select-none': header.column.getCanSort() }"
            @click="header.column.getToggleSortingHandler()?.($event)"
          >
            <span class="inline-flex items-center gap-1">
              <FlexRender :render="header.column.columnDef.header" :props="header.getContext()" />
              <template v-if="header.column.getCanSort()">
                <ArrowUp v-if="header.column.getIsSorted() === 'asc'" :size="12" />
                <ArrowDown v-else-if="header.column.getIsSorted() === 'desc'" :size="12" />
                <ArrowUpDown v-else :size="12" class="opacity-30" />
              </template>
            </span>
          </th>
        </tr>
        <tr v-for="headerGroup in table.getHeaderGroups()" :key="`${headerGroup.id}-filters`">
          <th
            v-for="header in headerGroup.headers"
            :key="`${header.id}-filter`"
            class="border-b border-slate-200 pb-2 font-normal dark:border-slate-800"
          >
            <input
              v-if="header.column.columnDef.meta?.filterParam"
              type="text"
              placeholder="Filtrar…"
              :value="usersColumnFilters[header.column.columnDef.meta.filterParam] ?? ''"
              class="w-full rounded-md border border-slate-300 px-2 py-1 text-xs font-normal dark:border-slate-700 dark:bg-slate-900"
              @input="onUsersFilterInput(header.column.columnDef.meta!.filterParam!, $event)"
            />
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="user in users" :key="user.id">
          <tr v-if="editingUserId === user.id" class="bg-slate-50 dark:bg-slate-900">
            <td colspan="6" class="border-b border-slate-100 p-4 dark:border-slate-900">
              <div class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <div class="col-span-2">
                  <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400" :for="`edit-email-${user.id}`">Correo</label>
                  <input
                    :id="`edit-email-${user.id}`"
                    v-model="editForm.email"
                    type="email"
                    class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                </div>
                <div>
                  <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400" :for="`edit-firstname-${user.id}`">Nombre</label>
                  <input
                    :id="`edit-firstname-${user.id}`"
                    v-model="editForm.first_name"
                    class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                </div>
                <div>
                  <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400" :for="`edit-lastname-${user.id}`">Apellido</label>
                  <input
                    :id="`edit-lastname-${user.id}`"
                    v-model="editForm.last_name"
                    class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                </div>
                <div>
                  <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400" :for="`edit-codigo-${user.id}`">Código de empleado</label>
                  <input
                    :id="`edit-codigo-${user.id}`"
                    v-model="editForm.codigo_empleado"
                    required
                    class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                  />
                </div>
                <div>
                  <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400" :for="`edit-role-${user.id}`">Rol</label>
                  <select
                    :id="`edit-role-${user.id}`"
                    v-model="editForm.role"
                    class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option :value="null">Sin rol</option>
                    <option v-for="role in rolesAsignables" :key="role.id" :value="role.id">{{ role.nombre_display }}</option>
                  </select>
                </div>
                <div v-if="esAdminGlobal">
                  <label class="mb-1 block text-xs text-slate-500 dark:text-slate-400" :for="`edit-division-${user.id}`">División</label>
                  <select
                    :id="`edit-division-${user.id}`"
                    v-model="editForm.division"
                    class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
                  >
                    <option :value="null">Sin división</option>
                    <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.nombre }}</option>
                  </select>
                </div>
              </div>
              <p v-if="esAdminGlobal" class="mt-2 text-xs text-slate-400">
                La división determina qué campañas, agencias y catálogos puede ver este usuario.
              </p>
              <div class="mt-3 flex gap-2">
                <ActionButton variant="success" icon="save" label="Guardar" @click="saveEditUser(user)" />
                <ActionButton variant="neutral" icon="cancel" label="Cancelar" @click="cancelEditUser" />
              </div>
            </td>
          </tr>
          <tr v-else class="text-slate-600 dark:text-slate-200">
            <td class="border-b border-slate-100 py-2 dark:border-slate-900">
              {{ user.email }}
              <span v-if="user.codigo_empleado" class="block text-xs text-slate-400">{{ user.codigo_empleado }}</span>
            </td>
            <td class="border-b border-slate-100 py-2 dark:border-slate-900">
              <span
                v-if="user.role_nombre"
                class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium"
                :class="ROLE_BADGE[user.role_nombre]"
              >
                {{ ROLE_LABEL[user.role_nombre] }}
              </span>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="border-b border-slate-100 py-2 text-xs dark:border-slate-900">
              <span v-if="user.division_nombre" class="inline-flex items-center gap-1">
                <Layers :size="12" class="text-accent-600" />{{ user.division_nombre }}
              </span>
              <span v-else-if="user.role_nombre === 'ADMIN'" class="text-slate-400">—</span>
              <span v-else class="text-amber-600">⚠ sin división</span>
            </td>
            <td class="border-b border-slate-100 py-2 text-xs dark:border-slate-900">
              <span v-if="user.role_nombre === 'ADMIN'" class="text-slate-400">Global</span>
              <span v-else-if="ROLES_TODA_LA_DIVISION.includes(user.role_nombre ?? '')" class="text-slate-400">Toda la división</span>
              <span v-else-if="user.role_nombre === 'EJECUTIVO'">{{ user.agencia_principal_nombre ?? '⚠ sin agencia' }}</span>
              <span v-else-if="['JEFE', 'SUBJEFE'].includes(user.role_nombre ?? '')">
                {{ user.agencias.filter((a) => a.activo).map((a) => a.agencia_nombre).join(', ') || '⚠ sin agencias' }}
              </span>
              <span v-else-if="user.role_nombre === 'SUPERVISOR'">
                {{ user.territorios.filter((t) => t.activo).map((t) => t.territorio_nombre).join(', ') || '⚠ sin distritos' }}
              </span>
              <span v-else class="text-slate-400">—</span>
            </td>
            <td class="border-b border-slate-100 py-2 dark:border-slate-900">
              <StatusBadge :active="user.is_active" />
            </td>
            <td class="border-b border-slate-100 py-2 dark:border-slate-900">
              <div v-if="puedoGestionar(user)" class="flex justify-end gap-1.5">
                <ActionButton variant="edit" icon="edit" label="Editar" @click="startEditUser(user)" />
                <ActionButton variant="scope" icon="scope" label="Alcance" @click="toggleExpand(user)" />
                <ActionButton
                  v-if="user.is_active"
                  variant="danger"
                  icon="deactivate"
                  label="Desactivar"
                  @click="toggleActive(user)"
                />
                <ActionButton v-else variant="success" icon="activate" label="Activar" @click="toggleActive(user)" />
              </div>
              <span v-else class="flex items-center justify-end gap-1 text-xs text-slate-400" title="Solo un administrador global puede modificar este usuario">
                <Lock :size="12" /> Solo lectura
              </span>
            </td>
          </tr>
          <tr v-if="editError && editingUserId === user.id">
            <td colspan="6" class="pb-2 text-xs text-red-600">{{ editError }}</td>
          </tr>
          <tr v-if="expandedUserId === user.id" class="bg-slate-50 dark:bg-slate-900">
            <td colspan="6" class="space-y-4 border-b border-slate-100 p-4 dark:border-slate-900">
              <div v-if="user.role_nombre === 'EJECUTIVO'" class="space-y-2 text-sm">
                <p class="text-slate-500">Agencia (solo una):</p>
                <div class="flex items-start gap-2">
                  <select v-model="pendingAgenciaDistrito" class="shrink-0 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900">
                    <option :value="null">Todos los distritos</option>
                    <option v-for="t in territoriosDeLaDivision" :key="t.id" :value="t.id">{{ t.nombre }}</option>
                  </select>
                  <div class="w-64">
                    <SingleSelectPicker v-model="pendingAgenciaPrincipal" :options="agenciaPickerOptions" placeholder="Buscar agencia…" />
                  </div>
                  <button class="shrink-0 rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-xs text-white" @click="handleSetAgenciaPrincipal(user)">
                    Guardar
                  </button>
                </div>
              </div>

              <div v-else-if="['JEFE', 'SUBJEFE'].includes(user.role_nombre ?? '')" class="space-y-2 text-sm">
                <p class="text-slate-500">Agencias asignadas (puede cubrir varias):</p>
                <div class="flex items-center gap-2">
                  <span class="shrink-0 text-xs text-slate-400">Filtrar por distrito:</span>
                  <select v-model="pendingAgenciaDistrito" class="rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900">
                    <option :value="null">Todos los distritos</option>
                    <option v-for="t in territoriosDeLaDivision" :key="t.id" :value="t.id">{{ t.nombre }}</option>
                  </select>
                </div>
                <div class="max-w-md">
                  <MultiSelectPicker v-model="pendingAgenciasSet" :options="agenciaPickerOptions" placeholder="Buscar agencia…" />
                </div>
                <button class="rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-1.5 text-xs text-white" @click="handleSaveAgencias(user)">
                  Guardar
                </button>
              </div>

              <div v-else-if="user.role_nombre === 'SUPERVISOR'" class="space-y-2 text-sm">
                <p class="text-slate-500">Distritos asignados (puede cubrir varios):</p>
                <div class="max-w-md">
                  <MultiSelectPicker v-model="pendingTerritoriosSet" :options="territorioPickerOptions" placeholder="Buscar distrito…" />
                </div>
                <button class="rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-1.5 text-xs text-white" @click="handleSaveTerritorios(user)">
                  Guardar
                </button>
              </div>

              <p v-else class="text-sm text-slate-400">
                {{
                  !user.role_nombre
                    ? 'Asigna un rol primero.'
                    : user.role_nombre === 'ADMIN'
                      ? 'Este rol tiene alcance global, no requiere agencia/distrito.'
                      : 'Este rol ve toda su división, no requiere agencia/distrito.'
                }}
              </p>

              <p v-if="scopeError" class="mt-2 text-xs text-red-600">{{ scopeError }}</p>
            </td>
          </tr>
        </template>
        <tr v-if="!loading && users.length === 0">
          <td colspan="6" class="py-6 text-center text-slate-400">Sin resultados.</td>
        </tr>
      </tbody>
    </table>
    </div>
    <TablePagination :page="usersPage" :page-size="usersPageSize" :count="usersCount" @update:page="handleUsersPage" />
    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
