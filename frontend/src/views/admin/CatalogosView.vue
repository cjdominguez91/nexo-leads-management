<script setup lang="ts">
import { Layers, ListTree, Plus, Tags } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'

import * as accountsApi from '@/api/accounts'
import type { Division } from '@/api/accounts'
import * as leadsApi from '@/api/leads'
import type { Category, SubCategory, SubCategoryEfecto } from '@/api/leads'
import ActionButton from '@/components/ActionButton.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useAuthStore } from '@/stores/auth'

const confirm = useConfirm()
const authStore = useAuthStore()

// El catálogo es por división. ADMIN global ve todas (puede filtrar) y elige
// en cuál crear; ADMIN_DIVISION solo ve/crea en la suya.
const esAdminGlobal = computed(() => authStore.isGlobalAdmin)
const divisiones = ref<Division[]>([])
const filtroDivision = ref<number | null>(null)

// Color por efecto: verde = ganada, rojo = perdida, azul = abre oportunidad.
const EFECTO_BADGE: Record<SubCategoryEfecto, string> = {
  SIN_EFECTO: 'bg-slate-100 text-slate-600 dark:bg-slate-700/50 dark:text-slate-300',
  ABRE_OPORTUNIDAD: 'bg-primary-50 text-primary-700 dark:bg-primary-600/15 dark:text-primary-500',
  GANADA: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400',
  PERDIDA: 'bg-red-50 text-red-700 dark:bg-red-500/15 dark:text-red-400',
}

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

const categoryForm = ref({ nombre: '', division: null as number | null })
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
    if (esAdminGlobal.value && divisiones.value.length === 0) {
      divisiones.value = (await accountsApi.fetchDivisions()).results
    }
  } finally {
    loading.value = false
  }
}

async function handleCreateCategory() {
  error.value = null
  try {
    await leadsApi.createCategory({
      nombre: categoryForm.value.nombre,
      division: esAdminGlobal.value ? categoryForm.value.division : undefined,
    })
    categoryForm.value = { nombre: '', division: categoryForm.value.division }
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
  const { category, ...resto } = subcategoryEdit.value
  if (!category) return
  error.value = null
  try {
    await leadsApi.updateSubCategory(s.id, { ...resto, category })
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

const categoriasVisibles = computed(() =>
  filtroDivision.value ? categories.value.filter((c) => c.division === filtroDivision.value) : categories.value,
)
const subcategoriasVisibles = computed(() =>
  filtroDivision.value ? subcategories.value.filter((s) => s.division === filtroDivision.value) : subcategories.value,
)
// Al editar, una subcategoría solo puede moverse a categorías de su división.
function categoriasPara(s: SubCategory) {
  return categories.value.filter((c) => c.division === s.division)
}
function divisionDe(c: Category) {
  return esAdminGlobal.value ? ` · ${c.division_nombre}` : ''
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-10">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="flex items-start gap-3">
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-600/15 dark:text-primary-500">
          <Tags :size="20" />
        </span>
        <div>
          <h1 class="text-xl font-semibold text-slate-700 dark:text-slate-200">Catálogos</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            Categorías y subcategorías de tipificación<template v-if="!esAdminGlobal"> de {{ authStore.user?.division_nombre ?? 'tu división' }}</template>.
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

    <section class="card p-4">
      <h2 class="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
        <Tags :size="16" class="text-primary-600" /> Categorías
      </h2>
      <form class="mb-4 flex flex-wrap items-center gap-2" @submit.prevent="handleCreateCategory">
        <input v-model="categoryForm.nombre" placeholder="Nombre (ej. Contacto Efectivo)" required class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
        <select
          v-if="esAdminGlobal"
          v-model="categoryForm.division"
          required
          class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
        >
          <option :value="null" disabled>División…</option>
          <option v-for="d in divisiones" :key="d.id" :value="d.id">{{ d.nombre }}</option>
        </select>
        <button type="submit" class="inline-flex items-center gap-1 rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-sm font-medium text-white">
          <Plus :size="15" /> Agregar
        </button>
      </form>
      <ul class="mb-6 max-w-2xl divide-y divide-slate-100 text-sm text-slate-600 dark:divide-slate-800 dark:text-slate-300">
        <li v-for="c in categoriasVisibles" :key="c.id" class="py-2">
          <div v-if="editingCategoryId === c.id" class="flex items-center gap-2">
            <input v-model="categoryEdit.nombre" class="flex-1 rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
            <ActionButton variant="success" icon="save" label="Guardar" icon-only @click="saveCategory(c)" />
            <ActionButton variant="neutral" icon="cancel" label="Cancelar" icon-only @click="cancelEditCategory" />
          </div>
          <div v-else class="flex items-center justify-between gap-2">
            <span class="min-w-0">
              <span class="font-medium" :class="{ 'text-slate-400': !c.activo }">{{ c.nombre }}</span>
              <span v-if="esAdminGlobal" class="ml-2 inline-flex items-center gap-1 text-xs text-slate-400">
                <Layers :size="11" class="text-accent-600" />{{ c.division_nombre }}
              </span>
            </span>
            <span class="flex shrink-0 items-center gap-1.5">
              <StatusBadge :active="c.activo" active-label="Activa" inactive-label="Inactiva" />
              <ActionButton variant="edit" icon="edit" label="Editar" icon-only @click="startEditCategory(c)" />
              <ActionButton
                :variant="c.activo ? 'danger' : 'success'"
                icon="power"
                :label="c.activo ? 'Desactivar' : 'Reactivar'"
                icon-only
                @click="toggleCategoryActivo(c)"
              />
            </span>
          </div>
        </li>
      </ul>

      <h3 class="mb-1 flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300">
        <ListTree :size="16" class="text-violet-600" /> Subcategorías
      </h3>
      <p class="mb-3 text-xs text-slate-400">
        "Efecto" define, al tipificar con esta subcategoría, qué pasa a la vez con el Lead y su Oportunidad —
        ej. bajo "Contacto Efectivo": "Volver a Llamar" = Abre, "Venta Efectiva" = Ganada, "No le interesa" = Perdida.
        "Requiere próximo contacto" agrega el campo de fecha/hora al formulario de gestión.
      </p>
      <form class="grid max-w-2xl grid-cols-2 gap-2" @submit.prevent="handleCreateSubcategory">
        <select v-model="subcategoryForm.category" required class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
          <option :value="null" disabled>Categoría…</option>
          <option v-for="c in categoriasVisibles" :key="c.id" :value="c.id">{{ c.nombre }}{{ divisionDe(c) }}</option>
        </select>
        <input v-model="subcategoryForm.nombre" placeholder="Nombre (ej. Venta Efectiva)" required class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
        <select v-model="subcategoryForm.efecto" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
          <option v-for="e in EFECTOS" :key="e.value" :value="e.value">{{ e.label }}</option>
        </select>
        <label class="flex items-center gap-1 text-xs text-slate-500">
          <input v-model="subcategoryForm.requiere_proximo_contacto" type="checkbox" /> Requiere próximo contacto
        </label>
        <button type="submit" class="col-span-2 inline-flex items-center justify-center gap-1 rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-sm font-medium text-white">
          <Plus :size="15" /> Agregar
        </button>
      </form>
      <div class="mt-4 max-w-4xl overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table class="data-table text-xs">
        <thead class="text-slate-500 dark:text-slate-400">
          <tr><th class="py-2">Categoría</th><th class="py-2">Subcategoría</th><th class="py-2">Efecto</th><th class="py-2">Próx. contacto</th><th class="py-2">Estado</th><th class="py-2" /></tr>
        </thead>
        <tbody>
          <template v-for="s in subcategoriasVisibles" :key="s.id">
            <tr v-if="editingSubcategoryId === s.id" class="text-slate-700 dark:text-slate-300">
              <td class="py-1 pr-3">
                <select v-model="subcategoryEdit.category" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
                  <option v-for="c in categoriasPara(s)" :key="c.id" :value="c.id">{{ c.nombre }}</option>
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
                <span class="inline-flex gap-1">
                  <ActionButton variant="success" icon="save" label="Guardar" icon-only @click="saveSubcategory(s)" />
                  <ActionButton variant="neutral" icon="cancel" label="Cancelar" icon-only @click="cancelEditSubcategory" />
                </span>
              </td>
            </tr>
            <tr v-else class="text-slate-600 dark:text-slate-300">
              <td class="border-t border-slate-100 py-2 dark:border-slate-800">{{ s.category_nombre }}</td>
              <td class="border-t border-slate-100 py-2 font-medium dark:border-slate-800">{{ s.nombre }}</td>
              <td class="border-t border-slate-100 py-2 dark:border-slate-800">
                <span class="rounded-full px-2 py-0.5 font-medium" :class="EFECTO_BADGE[s.efecto]">{{ s.efecto_display }}</span>
              </td>
              <td class="border-t border-slate-100 py-2 dark:border-slate-800">{{ s.requiere_proximo_contacto ? 'Sí' : 'No' }}</td>
              <td class="border-t border-slate-100 py-2 dark:border-slate-800">
                <StatusBadge :active="s.activo" active-label="Activa" inactive-label="Inactiva" />
              </td>
              <td class="whitespace-nowrap border-t border-slate-100 py-2 text-right dark:border-slate-800">
                <span class="inline-flex gap-1">
                  <ActionButton variant="edit" icon="edit" label="Editar" icon-only @click="startEditSubcategory(s)" />
                  <ActionButton
                    :variant="s.activo ? 'danger' : 'success'"
                    icon="power"
                    :label="s.activo ? 'Desactivar' : 'Reactivar'"
                    icon-only
                    @click="toggleSubcategoryActivo(s)"
                  />
                </span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      </div>
    </section>

    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
