<script setup lang="ts">
import { onMounted, ref } from 'vue'

import * as leadsApi from '@/api/leads'
import type { Category, SubCategory, SubCategoryEfecto } from '@/api/leads'
import { useConfirm } from '@/composables/useConfirm'

const confirm = useConfirm()

const EFECTOS: { value: SubCategoryEfecto; label: string }[] = [
  { value: 'SIN_EFECTO', label: 'Sin efecto' },
  { value: 'ABRE_OPORTUNIDAD', label: 'Abre/mantiene oportunidad' },
  { value: 'GANADA', label: 'Ganada (cierra lead y oportunidad)' },
  { value: 'PERDIDA', label: 'Perdida (cierra lead y oportunidad)' },
]

const categories = ref<Category[]>([])
const subcategories = ref<SubCategory[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const categoryForm = ref({ nombre: '' })
const subcategoryForm = ref({
  category: null as number | null,
  nombre: '',
  efecto: 'SIN_EFECTO' as SubCategoryEfecto,
  requiere_proximo_contacto: false,
})

const editingCategoryId = ref<number | null>(null)
const categoryEdit = ref({ nombre: '' })
const editingSubcategoryId = ref<number | null>(null)
const subcategoryEdit = ref({
  category: null as number | null,
  nombre: '',
  efecto: 'SIN_EFECTO' as SubCategoryEfecto,
  requiere_proximo_contacto: false,
})

async function loadData() {
  loading.value = true
  try {
    const [catRes, subcatRes] = await Promise.all([leadsApi.fetchCategories(), leadsApi.fetchSubCategories()])
    categories.value = catRes.results
    subcategories.value = subcatRes.results
  } finally {
    loading.value = false
  }
}

async function handleCreateCategory() {
  error.value = null
  try {
    await leadsApi.createCategory(categoryForm.value)
    categoryForm.value = { nombre: '' }
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear.')
  }
}

async function handleCreateSubcategory() {
  if (!subcategoryForm.value.category) return
  error.value = null
  try {
    await leadsApi.createSubCategory(subcategoryForm.value as any)
    subcategoryForm.value = { category: null, nombre: '', efecto: 'SIN_EFECTO', requiere_proximo_contacto: false }
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear.')
  }
}

function startEditCategory(c: Category) {
  editingCategoryId.value = c.id
  categoryEdit.value = { nombre: c.nombre }
}

function cancelEditCategory() {
  editingCategoryId.value = null
}

async function saveCategory(c: Category) {
  error.value = null
  try {
    await leadsApi.updateCategory(c.id, categoryEdit.value)
    editingCategoryId.value = null
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar la categoría.')
  }
}

async function toggleCategoryActivo(c: Category) {
  if (c.activo && !(await confirm({ title: `¿Desactivar "${c.nombre}"?`, message: 'Deja de estar disponible para tipificar leads.' }))) {
    return
  }
  error.value = null
  try {
    await leadsApi.updateCategory(c.id, { activo: !c.activo })
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo actualizar la categoría.')
  }
}

function startEditSubcategory(s: SubCategory) {
  editingSubcategoryId.value = s.id
  subcategoryEdit.value = {
    category: s.category,
    nombre: s.nombre,
    efecto: s.efecto,
    requiere_proximo_contacto: s.requiere_proximo_contacto,
  }
}

function cancelEditSubcategory() {
  editingSubcategoryId.value = null
}

async function saveSubcategory(s: SubCategory) {
  if (!subcategoryEdit.value.category) return
  error.value = null
  try {
    await leadsApi.updateSubCategory(s.id, subcategoryEdit.value)
    editingSubcategoryId.value = null
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar la subcategoría.')
  }
}

async function toggleSubcategoryActivo(s: SubCategory) {
  if (s.activo && !(await confirm({ title: `¿Desactivar "${s.nombre}"?`, message: 'Deja de estar disponible para tipificar leads.' }))) {
    return
  }
  error.value = null
  try {
    await leadsApi.updateSubCategory(s.id, { activo: !s.activo })
    await loadData()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo actualizar la subcategoría.')
  }
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-10">
    <div>
      <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">Catálogos</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400">Categorías y subcategorías de tipificación. Solo ADMIN.</p>
    </div>

    <p v-if="error" class="max-w-2xl text-xs text-red-600">{{ error }}</p>

    <section class="card p-4">
      <h2 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Categorías</h2>
      <form class="mb-4 flex flex-wrap items-center gap-2" @submit.prevent="handleCreateCategory">
        <input v-model="categoryForm.nombre" placeholder="Nombre (ej. Contacto Efectivo)" required class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
        <button type="submit" class="rounded-md bg-slate-900 px-3 py-2 text-sm text-white dark:bg-slate-100 dark:text-slate-900">+ Agregar</button>
      </form>
      <ul class="mb-6 space-y-1 text-sm text-slate-700 dark:text-slate-300">
        <li v-for="c in categories" :key="c.id">
          <div v-if="editingCategoryId === c.id" class="flex items-center gap-2 py-1">
            <input v-model="categoryEdit.nombre" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
            <button class="text-xs text-emerald-600 underline" @click="saveCategory(c)">Guardar</button>
            <button class="text-xs text-slate-400 underline" @click="cancelEditCategory">Cancelar</button>
          </div>
          <div v-else class="flex items-center justify-between gap-2 py-1" :class="{ 'opacity-50': !c.activo }">
            <span>{{ c.nombre }}<span v-if="!c.activo" class="ml-1 text-xs text-slate-400">— inactiva</span></span>
            <span class="flex shrink-0 gap-2 text-xs">
              <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="startEditCategory(c)">Editar</button>
              <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="toggleCategoryActivo(c)">
                {{ c.activo ? 'Desactivar' : 'Reactivar' }}
              </button>
            </span>
          </div>
        </li>
      </ul>

      <h3 class="mb-1 text-sm font-semibold text-slate-700 dark:text-slate-300">Subcategorías</h3>
      <p class="mb-3 text-xs text-slate-400">
        "Efecto" define, al tipificar con esta subcategoría, qué pasa a la vez con el Lead y su Oportunidad —
        ej. bajo "Contacto Efectivo": "Volver a Llamar" = Abre, "Venta Efectiva" = Ganada, "No le interesa" = Perdida.
        "Requiere próximo contacto" agrega el campo de fecha/hora al formulario de gestión.
      </p>
      <form class="grid max-w-2xl grid-cols-2 gap-2" @submit.prevent="handleCreateSubcategory">
        <select v-model="subcategoryForm.category" required class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
          <option :value="null" disabled>Categoría…</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.nombre }}</option>
        </select>
        <input v-model="subcategoryForm.nombre" placeholder="Nombre (ej. Venta Efectiva)" required class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
        <select v-model="subcategoryForm.efecto" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
          <option v-for="e in EFECTOS" :key="e.value" :value="e.value">{{ e.label }}</option>
        </select>
        <label class="flex items-center gap-1 text-xs text-slate-500">
          <input v-model="subcategoryForm.requiere_proximo_contacto" type="checkbox" /> Requiere próximo contacto
        </label>
        <button type="submit" class="col-span-2 rounded-md bg-slate-900 px-3 py-2 text-sm text-white dark:bg-slate-100 dark:text-slate-900">+ Agregar</button>
      </form>
      <table class="mt-4 w-full max-w-3xl text-left text-xs">
        <thead class="text-slate-400">
          <tr><th class="pb-1 pr-3">Categoría</th><th class="pb-1 pr-3">Subcategoría</th><th class="pb-1 pr-3">Efecto</th><th class="pb-1 pr-3">Próx. contacto</th><th class="pb-1 pr-3">Estado</th><th class="pb-1 pr-3" /></tr>
        </thead>
        <tbody>
          <template v-for="s in subcategories" :key="s.id">
            <tr v-if="editingSubcategoryId === s.id" class="text-slate-700 dark:text-slate-300">
              <td class="py-1 pr-3">
                <select v-model="subcategoryEdit.category" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
                  <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.nombre }}</option>
                </select>
              </td>
              <td class="py-1 pr-3">
                <input v-model="subcategoryEdit.nombre" class="w-full rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900" />
              </td>
              <td class="py-1 pr-3">
                <select v-model="subcategoryEdit.efecto" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
                  <option v-for="e in EFECTOS" :key="e.value" :value="e.value">{{ e.label }}</option>
                </select>
              </td>
              <td class="py-1 pr-3">
                <input v-model="subcategoryEdit.requiere_proximo_contacto" type="checkbox" />
              </td>
              <td class="py-1 pr-3" colspan="2">
                <button class="mr-2 text-emerald-600 underline" @click="saveSubcategory(s)">Guardar</button>
                <button class="text-slate-400 underline" @click="cancelEditSubcategory">Cancelar</button>
              </td>
            </tr>
            <tr v-else class="text-slate-700 dark:text-slate-300" :class="{ 'opacity-50': !s.activo }">
              <td class="py-1 pr-3">{{ s.category_nombre }}</td>
              <td class="py-1 pr-3">{{ s.nombre }}</td>
              <td class="py-1 pr-3">{{ s.efecto_display }}</td>
              <td class="py-1 pr-3">{{ s.requiere_proximo_contacto ? 'Sí' : 'No' }}</td>
              <td class="py-1 pr-3">{{ s.activo ? 'Activa' : 'Inactiva' }}</td>
              <td class="py-1 pr-3 whitespace-nowrap">
                <button class="mr-2 text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="startEditSubcategory(s)">Editar</button>
                <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="toggleSubcategoryActivo(s)">
                  {{ s.activo ? 'Desactivar' : 'Reactivar' }}
                </button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </section>

    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
