<script setup lang="ts">
import { Layers, Plus } from '@lucide/vue'
import { onMounted, ref } from 'vue'

import * as accountsApi from '@/api/accounts'
import type { Division } from '@/api/accounts'
import ActionButton from '@/components/ActionButton.vue'
import StatusBadge from '@/components/StatusBadge.vue'
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
    <div class="flex items-start gap-3">
      <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent-50 text-accent-700 dark:bg-accent-500/15 dark:text-accent-400">
        <Layers :size="20" />
      </span>
      <div>
        <h1 class="text-xl font-semibold text-slate-700 dark:text-slate-200">Divisiones</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400">
          Unidades de negocio (ej. "Red de Agencias", "Banca Empresas"). Usuarios, distritos, agencias, tipos de
          campaña, campañas y catálogos pertenecen a una división y quedan aislados dentro de ella.
        </p>
      </div>
    </div>

    <form class="card flex max-w-lg gap-2 p-4" @submit.prevent="handleCreate">
      <input v-model="form.nombre" placeholder="Nombre (ej. Banca Empresas)" required class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <input v-model="form.codigo" placeholder="Código" required class="w-28 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <button type="submit" class="inline-flex items-center gap-1 rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-sm font-medium text-white">
        <Plus :size="15" /> Agregar
      </button>
    </form>
    <p v-if="error" class="max-w-lg text-xs text-red-600">{{ error }}</p>

    <ul class="card max-w-lg divide-y divide-slate-100 px-4 py-2 text-sm text-slate-600 dark:divide-slate-800 dark:text-slate-300">
      <li v-for="division in divisiones" :key="division.id" class="py-2">
        <div v-if="editingId === division.id" class="flex items-center gap-2">
          <input v-model="edit.nombre" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
          <input v-model="edit.codigo" class="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
          <ActionButton variant="success" icon="save" label="Guardar" icon-only @click="save(division)" />
          <ActionButton variant="neutral" icon="cancel" label="Cancelar" icon-only @click="cancelEdit" />
        </div>
        <div v-else class="flex items-center justify-between gap-2">
          <span class="font-medium" :class="{ 'text-slate-400': !division.activo }">
            {{ division.nombre }} <span class="font-normal text-slate-400">({{ division.codigo }})</span>
          </span>
          <span class="flex shrink-0 items-center gap-1.5">
            <StatusBadge :active="division.activo" active-label="Activa" inactive-label="Inactiva" />
            <ActionButton variant="edit" icon="edit" label="Editar" icon-only @click="startEdit(division)" />
            <ActionButton
              :variant="division.activo ? 'danger' : 'success'"
              icon="power"
              :label="division.activo ? 'Desactivar' : 'Reactivar'"
              icon-only
              @click="toggleActivo(division)"
            />
          </span>
        </div>
      </li>
      <p v-if="!loading && divisiones.length === 0" class="text-sm text-slate-400">No hay divisiones todavía.</p>
    </ul>

    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
