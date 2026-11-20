<script setup lang="ts">
import { onMounted, ref } from 'vue'

import * as geoApi from '@/api/geo'
import type { Agencia, Territorio } from '@/api/geo'
import { useConfirm } from '@/composables/useConfirm'

const confirm = useConfirm()

const territorios = ref<Territorio[]>([])
const agencias = ref<Agencia[]>([])
const loading = ref(false)

const territorioForm = ref({ nombre: '', codigo: '' })
const agenciaForm = ref({ nombre: '', codigo: '', territorio: null as number | null })
const error = ref<string | null>(null)

const editingTerritorioId = ref<number | null>(null)
const territorioEdit = ref({ nombre: '', codigo: '' })
const editingAgenciaId = ref<number | null>(null)
const agenciaEdit = ref({ nombre: '', codigo: '', territorio: null as number | null })

async function loadData() {
  loading.value = true
  try {
    const [territoriosRes, agenciasRes] = await Promise.all([geoApi.fetchTerritorios(), geoApi.fetchAgencias()])
    territorios.value = territoriosRes.results
    agencias.value = agenciasRes.results
  } finally {
    loading.value = false
  }
}

async function handleCreateTerritorio() {
  error.value = null
  try {
    await geoApi.createTerritorio(territorioForm.value)
    territorioForm.value = { nombre: '', codigo: '' }
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear el territorio.')
  }
}

async function handleCreateAgencia() {
  if (!agenciaForm.value.territorio) return
  error.value = null
  try {
    await geoApi.createAgencia({
      nombre: agenciaForm.value.nombre,
      codigo: agenciaForm.value.codigo,
      territorio: agenciaForm.value.territorio,
    })
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

function cancelEditTerritorio() {
  editingTerritorioId.value = null
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

function cancelEditAgencia() {
  editingAgenciaId.value = null
}

async function saveAgencia(a: Agencia) {
  if (!agenciaEdit.value.territorio) return
  error.value = null
  try {
    await geoApi.updateAgencia(a.id, agenciaEdit.value)
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
    <div>
      <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">Territorios y Agencias</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400">Catálogo administrable. Solo ADMIN.</p>
    </div>

    <p v-if="error" class="max-w-2xl text-xs text-red-600">{{ error }}</p>

    <div class="grid gap-8 md:grid-cols-2">
      <section class="card p-4">
        <h2 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Territorios (distritos)</h2>
        <form class="mb-4 flex gap-2" @submit.prevent="handleCreateTerritorio">
          <input v-model="territorioForm.nombre" placeholder="Nombre" required class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
          <input v-model="territorioForm.codigo" placeholder="Código" required class="w-28 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
          <button type="submit" class="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900">+</button>
        </form>
        <ul class="space-y-1 text-sm text-slate-700 dark:text-slate-300">
          <li v-for="territorio in territorios" :key="territorio.id">
            <div v-if="editingTerritorioId === territorio.id" class="flex items-center gap-2 py-1">
              <input v-model="territorioEdit.nombre" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
              <input v-model="territorioEdit.codigo" class="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
              <button class="text-xs text-emerald-600 underline" @click="saveTerritorio(territorio)">Guardar</button>
              <button class="text-xs text-slate-400 underline" @click="cancelEditTerritorio">Cancelar</button>
            </div>
            <div v-else class="flex items-center justify-between gap-2 py-1" :class="{ 'opacity-50': !territorio.activo }">
              <span>{{ territorio.nombre }} ({{ territorio.codigo }})<span v-if="!territorio.activo" class="ml-1 text-xs text-slate-400">— inactivo</span></span>
              <span class="flex shrink-0 gap-2 text-xs">
                <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="startEditTerritorio(territorio)">Editar</button>
                <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="toggleTerritorioActivo(territorio)">
                  {{ territorio.activo ? 'Desactivar' : 'Reactivar' }}
                </button>
              </span>
            </div>
          </li>
        </ul>
      </section>

      <section class="card p-4">
        <h2 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Agencias</h2>
        <form class="mb-4 space-y-2" @submit.prevent="handleCreateAgencia">
          <div class="flex gap-2">
            <input v-model="agenciaForm.nombre" placeholder="Nombre" required class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
            <input v-model="agenciaForm.codigo" placeholder="Código" required class="w-28 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
          </div>
          <div class="flex gap-2">
            <select v-model="agenciaForm.territorio" required class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
              <option :value="null" disabled>Territorio…</option>
              <option v-for="territorio in territorios" :key="territorio.id" :value="territorio.id">{{ territorio.nombre }}</option>
            </select>
            <button type="submit" class="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900">+</button>
          </div>
        </form>
        <ul class="space-y-1 text-sm text-slate-700 dark:text-slate-300">
          <li v-for="agencia in agencias" :key="agencia.id">
            <div v-if="editingAgenciaId === agencia.id" class="space-y-2 py-1">
              <div class="flex gap-2">
                <input v-model="agenciaEdit.nombre" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
                <input v-model="agenciaEdit.codigo" class="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
              </div>
              <div class="flex items-center gap-2">
                <select v-model="agenciaEdit.territorio" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900">
                  <option v-for="territorio in territorios" :key="territorio.id" :value="territorio.id">{{ territorio.nombre }}</option>
                </select>
                <button class="text-xs text-emerald-600 underline" @click="saveAgencia(agencia)">Guardar</button>
                <button class="text-xs text-slate-400 underline" @click="cancelEditAgencia">Cancelar</button>
              </div>
            </div>
            <div v-else class="flex items-center justify-between gap-2 py-1" :class="{ 'opacity-50': !agencia.activo }">
              <span>{{ agencia.nombre }} ({{ agencia.codigo }}) — {{ agencia.territorio_nombre }}<span v-if="!agencia.activo" class="ml-1 text-xs text-slate-400">— inactiva</span></span>
              <span class="flex shrink-0 gap-2 text-xs">
                <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="startEditAgencia(agencia)">Editar</button>
                <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="toggleAgenciaActivo(agencia)">
                  {{ agencia.activo ? 'Desactivar' : 'Reactivar' }}
                </button>
              </span>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
