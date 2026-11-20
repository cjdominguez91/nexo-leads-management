<script setup lang="ts">
import { onMounted, ref } from 'vue'

import * as accountsApi from '@/api/accounts'
import type { Division } from '@/api/accounts'
import { useConfirm } from '@/composables/useConfirm'

const confirm = useConfirm()

const divisiones = ref<Division[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const form = ref({ nombre: '', codigo: '' })

const editingId = ref<number | null>(null)
const edit = ref({ nombre: '', codigo: '' })

async function loadData() {
  loading.value = true
  try {
    const res = await accountsApi.fetchDivisions()
    divisiones.value = res.results
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  error.value = null
  try {
    await accountsApi.createDivision(form.value)
    form.value = { nombre: '', codigo: '' }
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear la división.')
  }
}

function startEdit(d: Division) {
  editingId.value = d.id
  edit.value = { nombre: d.nombre, codigo: d.codigo }
}

function cancelEdit() {
  editingId.value = null
}

async function save(d: Division) {
  error.value = null
  try {
    await accountsApi.updateDivision(d.id, edit.value)
    editingId.value = null
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar la división.')
  }
}

async function toggleActivo(d: Division) {
  if (d.activo && !(await confirm({ title: `¿Desactivar "${d.nombre}"?`, message: 'Deja de estar disponible para usuarios y campañas.' }))) {
    return
  }
  error.value = null
  try {
    await accountsApi.updateDivision(d.id, { activo: !d.activo })
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo actualizar la división.')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-8">
    <div>
      <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">Divisiones</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400">
        Unidades de negocio (ej. "Red de Agencias", "Banca Empresas"). Cada usuario y cada campaña pertenecen a una
        — para ver una campaña, el usuario debe estar en la misma división. Solo ADMIN.
      </p>
    </div>

    <form class="card flex max-w-lg gap-2 p-4" @submit.prevent="handleCreate">
      <input v-model="form.nombre" placeholder="Nombre (ej. Banca Empresas)" required class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <input v-model="form.codigo" placeholder="Código" required class="w-28 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <button type="submit" class="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900">+</button>
    </form>
    <p v-if="error" class="max-w-lg text-xs text-red-600">{{ error }}</p>

    <ul class="card max-w-lg space-y-1 p-4 text-sm text-slate-700 dark:text-slate-300">
      <li v-for="division in divisiones" :key="division.id">
        <div v-if="editingId === division.id" class="flex items-center gap-2 py-1">
          <input v-model="edit.nombre" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
          <input v-model="edit.codigo" class="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
          <button class="text-xs text-emerald-600 underline" @click="save(division)">Guardar</button>
          <button class="text-xs text-slate-400 underline" @click="cancelEdit">Cancelar</button>
        </div>
        <div v-else class="flex items-center justify-between gap-2 py-1" :class="{ 'opacity-50': !division.activo }">
          <span>{{ division.nombre }} ({{ division.codigo }})<span v-if="!division.activo" class="ml-1 text-xs text-slate-400">— inactiva</span></span>
          <span class="flex shrink-0 gap-2 text-xs">
            <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="startEdit(division)">Editar</button>
            <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="toggleActivo(division)">
              {{ division.activo ? 'Desactivar' : 'Reactivar' }}
            </button>
          </span>
        </div>
      </li>
      <p v-if="!loading && divisiones.length === 0" class="text-sm text-slate-400">No hay divisiones todavía.</p>
    </ul>

    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
