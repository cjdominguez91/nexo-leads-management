<script setup lang="ts">
import { Building2, Layers, MapPinned, Plus } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'

import * as accountsApi from '@/api/accounts'
import type { Division } from '@/api/accounts'
import * as geoApi from '@/api/geo'
import type { Agencia, Territorio } from '@/api/geo'
import ActionButton from '@/components/ActionButton.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useAuthStore } from '@/stores/auth'

const confirm = useConfirm()
const authStore = useAuthStore()

// ADMIN global ve y crea en cualquier división (elige cuál). ADMIN_DIVISION
// solo ve la suya y el backend fija la división al crear.
const esAdminGlobal = computed(() => authStore.isGlobalAdmin)

const divisiones = ref<Division[]>([])
const territorios = ref<Territorio[]>([])
const agencias = ref<Agencia[]>([])
const loading = ref(false)
const filtroDivision = ref<number | null>(null)

const territorioForm = ref({ nombre: '', codigo: '', division: null as number | null })
const agenciaForm = ref({ nombre: '', codigo: '', territorio: null as number | null })
const error = ref<string | null>(null)

const editingTerritorioId = ref<number | null>(null)
const territorioEdit = ref({ nombre: '', codigo: '' })
const editingAgenciaId = ref<number | null>(null)
const agenciaEdit = ref({ nombre: '', codigo: '', territorio: null as number | null })

const territoriosVisibles = computed(() =>
  filtroDivision.value ? territorios.value.filter((t) => t.division === filtroDivision.value) : territorios.value,
)
const agenciasVisibles = computed(() =>
  filtroDivision.value ? agencias.value.filter((a) => a.division === filtroDivision.value) : agencias.value,
)
// Al editar, una agencia solo puede moverse a distritos de su misma división.
function territoriosParaAgencia(a: Agencia) {
  return territorios.value.filter((t) => t.division === a.division)
}

async function loadData() {
  loading.value = true
  try {
    const [territoriosRes, agenciasRes] = await Promise.all([geoApi.fetchTerritorios(), geoApi.fetchAgencias()])
    territorios.value = territoriosRes.results
    agencias.value = agenciasRes.results
    if (esAdminGlobal.value && divisiones.value.length === 0) {
      divisiones.value = (await accountsApi.fetchDivisions()).results
    }
  } finally {
    loading.value = false
  }
}

async function handleCreateTerritorio() {
  error.value = null
  try {
    await geoApi.createTerritorio({
      nombre: territorioForm.value.nombre,
      codigo: territorioForm.value.codigo,
      division: esAdminGlobal.value ? territorioForm.value.division : undefined,
    })
    territorioForm.value = { nombre: '', codigo: '', division: territorioForm.value.division }
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear el territorio.')
  }
}

async function handleCreateAgencia() {
  const territorio = agenciaForm.value.territorio
  if (!territorio) return
  error.value = null
  try {
    await geoApi.createAgencia({ nombre: agenciaForm.value.nombre, codigo: agenciaForm.value.codigo, territorio })
    agenciaForm.value = { nombre: '', codigo: '', territorio: null }
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear la agencia.')
  }
}

function startEditTerritorio(t: Territorio) {
  editingTerritorioId.value = t.id
  territorioEdit.value = { nombre: t.nombre, codigo: t.codigo }
}

async function saveTerritorio(t: Territorio) {
  error.value = null
  try {
    await geoApi.updateTerritorio(t.id, territorioEdit.value)
    editingTerritorioId.value = null
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar el territorio.')
  }
}

async function toggleTerritorioActivo(t: Territorio) {
  if (t.activo && !(await confirm({ title: `¿Desactivar "${t.nombre}"?`, message: 'Deja de estar disponible para asignar agencias y campañas.' }))) {
    return
  }
  error.value = null
  try {
    await geoApi.updateTerritorio(t.id, { activo: !t.activo })
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo actualizar el territorio.')
  }
}

function startEditAgencia(a: Agencia) {
  editingAgenciaId.value = a.id
  agenciaEdit.value = { nombre: a.nombre, codigo: a.codigo, territorio: a.territorio }
}

async function saveAgencia(a: Agencia) {
  const { nombre, codigo, territorio } = agenciaEdit.value
  if (!territorio) return
  error.value = null
  try {
    await geoApi.updateAgencia(a.id, { nombre, codigo, territorio })
    editingAgenciaId.value = null
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar la agencia.')
  }
}

async function toggleAgenciaActivo(a: Agencia) {
  if (a.activo && !(await confirm({ title: `¿Desactivar "${a.nombre}"?`, message: 'Deja de estar disponible para asignaciones y scoping territorial.' }))) {
    return
  }
  error.value = null
  try {
    await geoApi.updateAgencia(a.id, { activo: !a.activo })
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo actualizar la agencia.')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-8">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="flex items-start gap-3">
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-600/15 dark:text-primary-500">
          <Building2 :size="20" />
        </span>
        <div>
          <h1 class="text-xl font-semibold text-slate-700 dark:text-slate-200">Territorios y Agencias</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            {{ esAdminGlobal ? 'Catálogo de todas las divisiones.' : `Catálogo de ${authStore.user?.division_nombre ?? 'tu división'}.` }}
            Cada agencia pertenece a la división de su distrito.
          </p>
        </div>
      </div>
      <select
        v-if="esAdminGlobal"
        v-model="filtroDivision"
        class="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
      >
        <option :value="null">Todas las divisiones</option>
        <option v-for="d in divisiones" :key="d.id" :value="d.id">{{ d.nombre }}</option>
      </select>
    </div>

    <p v-if="error" class="max-w-2xl text-xs text-red-600">{{ error }}</p>

    <div class="grid gap-8 md:grid-cols-2">
      <section class="card p-4">
        <h2 class="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
          <MapPinned :size="16" class="text-teal-600" /> Territorios (distritos)
        </h2>
        <form class="mb-4 space-y-2" @submit.prevent="handleCreateTerritorio">
          <div class="flex gap-2">
            <input v-model="territorioForm.nombre" placeholder="Nombre" required class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
            <input v-model="territorioForm.codigo" placeholder="Código" required class="w-28 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
          </div>
          <div class="flex gap-2">
            <select
              v-if="esAdminGlobal"
              v-model="territorioForm.division"
              required
              class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              <option :value="null" disabled>División…</option>
              <option v-for="d in divisiones" :key="d.id" :value="d.id">{{ d.nombre }}</option>
            </select>
            <button type="submit" class="ml-auto inline-flex items-center gap-1 rounded-md bg-primary-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700">
              <Plus :size="15" /> Agregar
            </button>
          </div>
        </form>
        <ul class="divide-y divide-slate-100 text-sm text-slate-600 dark:divide-slate-800 dark:text-slate-300">
          <li v-for="territorio in territoriosVisibles" :key="territorio.id" class="py-2">
            <div v-if="editingTerritorioId === territorio.id" class="flex items-center gap-2">
              <input v-model="territorioEdit.nombre" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
              <input v-model="territorioEdit.codigo" class="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
              <ActionButton variant="success" icon="save" label="Guardar" icon-only @click="saveTerritorio(territorio)" />
              <ActionButton variant="neutral" icon="cancel" label="Cancelar" icon-only @click="editingTerritorioId = null" />
            </div>
            <div v-else class="flex items-center justify-between gap-2">
              <div class="min-w-0">
                <p class="truncate font-medium" :class="{ 'text-slate-400': !territorio.activo }">
                  {{ territorio.nombre }} <span class="font-normal text-slate-400">({{ territorio.codigo }})</span>
                </p>
                <p v-if="esAdminGlobal" class="flex items-center gap-1 text-xs text-slate-400">
                  <Layers :size="11" class="text-accent-600" /> {{ territorio.division_nombre }}
                </p>
              </div>
              <span class="flex shrink-0 items-center gap-1.5">
                <StatusBadge :active="territorio.activo" />
                <ActionButton variant="edit" icon="edit" label="Editar" icon-only @click="startEditTerritorio(territorio)" />
                <ActionButton
                  :variant="territorio.activo ? 'danger' : 'success'"
                  icon="power"
                  :label="territorio.activo ? 'Desactivar' : 'Reactivar'"
                  icon-only
                  @click="toggleTerritorioActivo(territorio)"
                />
              </span>
            </div>
          </li>
          <li v-if="!loading && territoriosVisibles.length === 0" class="py-4 text-center text-xs text-slate-400">Sin distritos todavía.</li>
        </ul>
      </section>

      <section class="card p-4">
        <h2 class="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
          <Building2 :size="16" class="text-primary-600" /> Agencias
        </h2>
        <form class="mb-4 space-y-2" @submit.prevent="handleCreateAgencia">
          <div class="flex gap-2">
            <input v-model="agenciaForm.nombre" placeholder="Nombre" required class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
            <input v-model="agenciaForm.codigo" placeholder="Código" required class="w-28 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
          </div>
          <div class="flex gap-2">
            <select v-model="agenciaForm.territorio" required class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
              <option :value="null" disabled>Distrito…</option>
              <option v-for="territorio in territoriosVisibles" :key="territorio.id" :value="territorio.id">
                {{ territorio.nombre }}{{ esAdminGlobal ? ` · ${territorio.division_nombre}` : '' }}
              </option>
            </select>
            <button type="submit" class="inline-flex items-center gap-1 rounded-md bg-primary-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-primary-700">
              <Plus :size="15" /> Agregar
            </button>
          </div>
        </form>
        <ul class="divide-y divide-slate-100 text-sm text-slate-600 dark:divide-slate-800 dark:text-slate-300">
          <li v-for="agencia in agenciasVisibles" :key="agencia.id" class="py-2">
            <div v-if="editingAgenciaId === agencia.id" class="space-y-2">
              <div class="flex gap-2">
                <input v-model="agenciaEdit.nombre" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
                <input v-model="agenciaEdit.codigo" class="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
              </div>
              <div class="flex items-center gap-2">
                <select v-model="agenciaEdit.territorio" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900">
                  <option v-for="territorio in territoriosParaAgencia(agencia)" :key="territorio.id" :value="territorio.id">{{ territorio.nombre }}</option>
                </select>
                <ActionButton variant="success" icon="save" label="Guardar" icon-only @click="saveAgencia(agencia)" />
                <ActionButton variant="neutral" icon="cancel" label="Cancelar" icon-only @click="editingAgenciaId = null" />
              </div>
            </div>
            <div v-else class="flex items-center justify-between gap-2">
              <div class="min-w-0">
                <p class="truncate font-medium" :class="{ 'text-slate-400': !agencia.activo }">
                  {{ agencia.nombre }} <span class="font-normal text-slate-400">({{ agencia.codigo }})</span>
                </p>
                <p class="flex items-center gap-1 text-xs text-slate-400">
                  <MapPinned :size="11" class="text-teal-600" /> {{ agencia.territorio_nombre }}
                  <template v-if="esAdminGlobal">
                    <span class="mx-0.5">·</span><Layers :size="11" class="text-accent-600" /> {{ agencia.division_nombre }}
                  </template>
                </p>
              </div>
              <span class="flex shrink-0 items-center gap-1.5">
                <StatusBadge :active="agencia.activo" active-label="Activa" inactive-label="Inactiva" />
                <ActionButton variant="edit" icon="edit" label="Editar" icon-only @click="startEditAgencia(agencia)" />
                <ActionButton
                  :variant="agencia.activo ? 'danger' : 'success'"
                  icon="power"
                  :label="agencia.activo ? 'Desactivar' : 'Reactivar'"
                  icon-only
                  @click="toggleAgenciaActivo(agencia)"
                />
              </span>
            </div>
          </li>
          <li v-if="!loading && agenciasVisibles.length === 0" class="py-4 text-center text-xs text-slate-400">Sin agencias todavía.</li>
        </ul>
      </section>
    </div>

    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
