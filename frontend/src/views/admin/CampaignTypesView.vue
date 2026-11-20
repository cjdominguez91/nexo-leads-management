<script setup lang="ts">
import { ClipboardList, Layers, Plus } from '@lucide/vue'
import { computed, onMounted, ref } from 'vue'

import * as accountsApi from '@/api/accounts'
import type { Division } from '@/api/accounts'
import * as campaignsApi from '@/api/campaigns'
import type {
  CampaignFieldDataType,
  CampaignFieldDefinition,
  CampaignFieldOrigen,
  CampaignModoCarga,
  CampaignType,
} from '@/api/campaigns'
import ActionButton from '@/components/ActionButton.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useAuthStore } from '@/stores/auth'

const confirm = useConfirm()
const authStore = useAuthStore()
// Los tipos son por división: ADMIN global elige en cuál crear; ADMIN_DIVISION
// crea siempre en la suya (el backend la fija).
const esAdminGlobal = computed(() => authStore.isGlobalAdmin)
const divisiones = ref<Division[]>([])
const filtroDivision = ref<number | null>(null)

const DATA_TYPES: CampaignFieldDataType[] = ['TEXTO', 'NUMERO', 'FECHA', 'BOOLEANO', 'SELECT', 'MULTISELECT']
const ORIGENES: { value: CampaignFieldOrigen; label: string }[] = [
  { value: 'CARGA', label: 'Se carga desde el archivo' },
  { value: 'CAPTURA_GESTION', label: 'Se captura al gestionar (formulario en el detalle del lead)' },
]
const MODOS_CARGA: { value: CampaignModoCarga; label: string }[] = [
  { value: 'MASIVA', label: 'Campaña — carga masiva (archivo)' },
  { value: 'INDIVIDUAL', label: 'Prospección — registro individual (uno por uno)' },
]

function origenesPara(type: CampaignType) {
  return type.modo_carga === 'INDIVIDUAL' ? ORIGENES.filter((o) => o.value === 'CARGA') : ORIGENES
}

const types = ref<CampaignType[]>([])
const tiposVisibles = computed(() =>
  filtroDivision.value ? types.value.filter((t) => t.division === filtroDivision.value) : types.value,
)
const loading = ref(false)
const error = ref<string | null>(null)

const typeForm = ref({
  nombre: '',
  categoria: 'VENTAS' as 'VENTAS' | 'COBROS',
  modo_carga: 'MASIVA' as CampaignModoCarga,
  division: null as number | null,
})

const fieldForms = ref<Record<number, any>>({})
const sectionForms = ref<Record<number, string>>({})

const editingTypeId = ref<number | null>(null)
const typeEdit = ref({ nombre: '', categoria: 'VENTAS' as 'VENTAS' | 'COBROS' })
const editingFieldId = ref<number | null>(null)
const fieldEdit = ref<any>(null)

function emptyFieldForm(defaultSeccionId: number | null) {
  return {
    field_key: '',
    label: '',
    data_type: 'TEXTO' as CampaignFieldDataType,
    origen: 'CARGA' as CampaignFieldOrigen,
    required: false,
    options: '',
    orden: 1,
    mostrar_en_tabla: true,
    mostrar_en_detalle: true,
    seccion: defaultSeccionId as number | null,
    es_nombre_cliente: false,
    es_telefono_contacto: false,
    es_documento_identidad: false,
  }
}

function faltantes(fields: CampaignFieldDefinition[]): string[] {
  const cargaFields = fields.filter((f) => f.origen === 'CARGA')
  const requeridos: { flag: keyof CampaignFieldDefinition; etiqueta: string }[] = [
    { flag: 'es_nombre_cliente', etiqueta: 'nombre del cliente' },
    { flag: 'es_telefono_contacto', etiqueta: 'teléfono de contacto' },
    { flag: 'es_documento_identidad', etiqueta: 'documento de identidad' },
  ]
  return requeridos.filter((r) => !cargaFields.some((f) => f[r.flag])).map((r) => r.etiqueta)
}

function datosClienteId(type: CampaignType): number | null {
  return type.secciones.find((s) => s.es_obligatoria)?.id ?? type.secciones[0]?.id ?? null
}

async function loadTypes() {
  loading.value = true
  try {
    const res = await campaignsApi.fetchCampaignTypes()
    types.value = res.results
    if (esAdminGlobal.value && divisiones.value.length === 0) {
      divisiones.value = (await accountsApi.fetchDivisions()).results
    }
    for (const t of types.value) {
      if (!fieldForms.value[t.id]) fieldForms.value[t.id] = emptyFieldForm(datosClienteId(t))
      if (sectionForms.value[t.id] === undefined) sectionForms.value[t.id] = ''
    }
  } finally {
    loading.value = false
  }
}

async function handleCreateType() {
  error.value = null
  try {
    await campaignsApi.createCampaignType({
      ...typeForm.value,
      division: esAdminGlobal.value ? typeForm.value.division : undefined,
    })
    typeForm.value = { nombre: '', categoria: 'VENTAS', modo_carga: 'MASIVA', division: typeForm.value.division }
    await loadTypes()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear.')
  }
}

async function handleCreateField(campaignTypeId: number) {
  const form = fieldForms.value[campaignTypeId]
  if (!form.seccion) return
  error.value = null
  try {
    const needsOptions = form.data_type === 'SELECT' || form.data_type === 'MULTISELECT'
    await campaignsApi.createFieldDefinition({
      campaign_type: campaignTypeId,
      field_key: form.field_key,
      label: form.label,
      data_type: form.data_type,
      origen: form.origen,
      required: form.required,
      options: needsOptions ? form.options.split(',').map((o: string) => o.trim()).filter(Boolean) : null,
      orden: Number(form.orden),
      mostrar_en_tabla: form.mostrar_en_tabla,
      mostrar_en_detalle: form.mostrar_en_detalle,
      seccion: form.seccion,
      es_nombre_cliente: form.es_nombre_cliente,
      es_telefono_contacto: form.es_telefono_contacto,
      es_documento_identidad: form.es_documento_identidad,
    })
    const type = types.value.find((t) => t.id === campaignTypeId)
    fieldForms.value[campaignTypeId] = emptyFieldForm(type ? datosClienteId(type) : null)
    await loadTypes()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear el campo.')
  }
}

async function handleCreateSection(campaignTypeId: number) {
  const nombre = sectionForms.value[campaignTypeId]?.trim()
  if (!nombre) return
  error.value = null
  try {
    await campaignsApi.createSection({ campaign_type: campaignTypeId, nombre, orden: 1 })
    sectionForms.value[campaignTypeId] = ''
    await loadTypes()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear la sección.')
  }
}

async function handleDeleteSection(section: { id: number; nombre: string }) {
  const confirmed = await confirm({ title: `¿Eliminar la sección "${section.nombre}"?`, confirmText: 'Eliminar', danger: true })
  if (!confirmed) return
  error.value = null
  try {
    await campaignsApi.deleteSection(section.id)
    await loadTypes()
  } catch (err: any) {
    error.value = err?.response?.data?.[0] ?? err?.response?.data?.detail ?? 'No se pudo eliminar la sección.'
  }
}

function startEditType(type: CampaignType) {
  editingTypeId.value = type.id
  typeEdit.value = { nombre: type.nombre, categoria: type.categoria }
}

function cancelEditType() {
  editingTypeId.value = null
}

async function saveType(type: CampaignType) {
  error.value = null
  try {
    await campaignsApi.updateCampaignType(type.id, typeEdit.value)
    editingTypeId.value = null
    await loadTypes()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar el tipo de campaña.')
  }
}

async function handleDeleteType(type: CampaignType) {
  const confirmed = await confirm({
    title: `¿Eliminar "${type.nombre}"?`,
    message: 'Se rechaza si ya tiene campañas creadas.',
    confirmText: 'Eliminar',
    danger: true,
  })
  if (!confirmed) return
  error.value = null
  try {
    await campaignsApi.deleteCampaignType(type.id)
    await loadTypes()
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'No se pudo eliminar el tipo de campaña.'
  }
}

function startEditField(field: CampaignFieldDefinition) {
  editingFieldId.value = field.id
  fieldEdit.value = {
    field_key: field.field_key,
    label: field.label,
    data_type: field.data_type,
    origen: field.origen,
    required: field.required,
    options: field.options ? field.options.join(', ') : '',
    orden: field.orden,
    mostrar_en_tabla: field.mostrar_en_tabla,
    mostrar_en_detalle: field.mostrar_en_detalle,
    seccion: field.seccion,
    es_nombre_cliente: field.es_nombre_cliente,
    es_telefono_contacto: field.es_telefono_contacto,
    es_documento_identidad: field.es_documento_identidad,
  }
}

function cancelEditField() {
  editingFieldId.value = null
  fieldEdit.value = null
}

async function saveField(field: CampaignFieldDefinition) {
  error.value = null
  try {
    const needsOptions = fieldEdit.value.data_type === 'SELECT' || fieldEdit.value.data_type === 'MULTISELECT'
    await campaignsApi.updateFieldDefinition(field.id, {
      field_key: fieldEdit.value.field_key,
      label: fieldEdit.value.label,
      data_type: fieldEdit.value.data_type,
      origen: fieldEdit.value.origen,
      required: fieldEdit.value.required,
      options: needsOptions
        ? fieldEdit.value.options.split(',').map((o: string) => o.trim()).filter(Boolean)
        : null,
      orden: Number(fieldEdit.value.orden),
      mostrar_en_tabla: fieldEdit.value.mostrar_en_tabla,
      mostrar_en_detalle: fieldEdit.value.mostrar_en_detalle,
      seccion: fieldEdit.value.seccion,
      es_nombre_cliente: fieldEdit.value.es_nombre_cliente,
      es_telefono_contacto: fieldEdit.value.es_telefono_contacto,
      es_documento_identidad: fieldEdit.value.es_documento_identidad,
    })
    editingFieldId.value = null
    await loadTypes()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar el campo.')
  }
}

async function handleDeleteField(field: CampaignFieldDefinition) {
  const confirmed = await confirm({ title: `¿Eliminar el campo "${field.label}"?`, confirmText: 'Eliminar', danger: true })
  if (!confirmed) return
  error.value = null
  try {
    await campaignsApi.deleteFieldDefinition(field.id)
    await loadTypes()
  } catch (err: any) {
    error.value = err?.response?.data?.detail ?? 'No se pudo eliminar el campo.'
  }
}

onMounted(loadTypes)
</script>

<template>
  <div class="space-y-8">
    <div>
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="flex items-start gap-3">
          <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-primary-600 dark:bg-primary-600/15 dark:text-primary-500">
            <ClipboardList :size="20" />
          </span>
          <div>
            <h1 class="text-xl font-semibold text-slate-700 dark:text-slate-200">Tipos de campaña</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400">
              Define el esquema dinámico de cada producto: qué campos captura y cómo se muestran.
              <template v-if="!esAdminGlobal">Tipos de {{ authStore.user?.division_nombre ?? 'tu división' }}.</template>
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
      <p class="mt-1 text-xs text-slate-400">
        Cada tipo de campaña necesita exactamente un campo marcado "nombre", uno "teléfono" y uno "documento de
        identidad" — son los únicos 3 con comportamiento especial. El documento (no el teléfono) es lo que usa
        el dedup al cargar, porque los números de teléfono se reciclan entre personas y los nombres pueden
        repetirse (homónimos). Todo lo demás lo diseñas libre.
      </p>
      <p class="mt-1 text-xs text-slate-400">
        "Se carga desde el archivo" es el caso normal. "Se captura al gestionar" es para campañas de actualización
        de datos: el campo no viene en la base, se llena en un formulario dentro del detalle del lead cuando el
        ejecutivo llama al cliente.
      </p>
    </div>

    <form class="card grid max-w-lg grid-cols-2 gap-2 p-4" @submit.prevent="handleCreateType">
      <input v-model="typeForm.nombre" placeholder="Nombre (ej. Créditos Personales)" required class="col-span-2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <select v-model="typeForm.categoria" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option value="VENTAS">Ventas</option>
        <option value="COBROS">Cobros</option>
      </select>
      <select v-model="typeForm.modo_carga" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option v-for="m in MODOS_CARGA" :key="m.value" :value="m.value">{{ m.label }}</option>
      </select>
      <select
        v-if="esAdminGlobal"
        v-model="typeForm.division"
        required
        class="col-span-2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
      >
        <option :value="null" disabled>División…</option>
        <option v-for="d in divisiones" :key="d.id" :value="d.id">{{ d.nombre }}</option>
      </select>
      <button type="submit" class="col-span-2 inline-flex items-center justify-center gap-1.5 rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-sm font-medium text-white">
        <Plus :size="16" /> Crear tipo
      </button>
    </form>
    <p v-if="error" class="max-w-lg text-xs text-red-600">{{ error }}</p>

    <div v-for="type in tiposVisibles" :key="type.id" class="card p-4">
      <div v-if="editingTypeId === type.id" class="flex items-center gap-2">
        <input v-model="typeEdit.nombre" class="rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900" />
        <select v-model="typeEdit.categoria" class="rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900">
          <option value="VENTAS">Ventas</option>
          <option value="COBROS">Cobros</option>
        </select>
        <ActionButton variant="success" icon="save" label="Guardar" @click="saveType(type)" />
        <ActionButton variant="neutral" icon="cancel" label="Cancelar" @click="cancelEditType" />
      </div>
      <div v-else class="flex items-center justify-between">
        <h2 class="font-medium text-slate-700 dark:text-slate-200">
          {{ type.nombre }}
          <span
            class="ml-1 rounded-full px-2 py-0.5 text-xs"
            :class="type.modo_carga === 'INDIVIDUAL' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800'"
          >
            {{ type.modo_carga === 'INDIVIDUAL' ? 'Prospección' : 'Campaña (masiva)' }}
          </span>
          <span
            class="ml-1 rounded-full px-2 py-0.5 text-xs"
            :class="type.categoria === 'COBROS' ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'"
          >
            {{ type.categoria === 'COBROS' ? 'Cobros' : 'Ventas' }}
          </span>
          <span v-if="esAdminGlobal" class="ml-1 inline-flex items-center gap-1 text-xs font-normal text-slate-400">
            <Layers :size="11" class="text-accent-600" /> {{ type.division_nombre }}
          </span>
        </h2>
        <span class="flex gap-1.5">
          <ActionButton variant="edit" icon="edit" label="Editar" @click="startEditType(type)" />
          <ActionButton variant="danger" icon="delete" label="Eliminar" @click="handleDeleteType(type)" />
        </span>
      </div>

      <div class="mt-3">
        <h3 class="mb-1 text-xs font-semibold uppercase text-slate-400">Secciones</h3>
        <div class="flex flex-wrap items-center gap-2">
          <span
            v-for="s in type.secciones"
            :key="s.id"
            class="inline-flex items-center gap-1.5 rounded-full bg-slate-200 px-2 py-0.5 text-xs dark:bg-slate-800"
          >
            {{ s.nombre }}
            <span v-if="s.es_obligatoria" class="text-slate-400">(obligatoria)</span>
            <button v-else class="text-slate-500 hover:text-red-600" @click="handleDeleteSection(s)">×</button>
          </span>
          <form class="flex items-center gap-1" @submit.prevent="handleCreateSection(type.id)">
            <input
              v-model="sectionForms[type.id]"
              placeholder="+ nueva sección (ej. Datos Laborales)"
              class="rounded-md border border-slate-300 px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-900"
            />
            <button type="submit" class="rounded-md border border-slate-300 px-2 py-1 text-xs dark:border-slate-700">Agregar</button>
          </form>
        </div>
      </div>

      <table v-if="type.field_definitions.length" class="mt-3 w-full text-left text-xs">
        <thead class="text-slate-400">
          <tr><th class="pb-1 pr-3">Campo</th><th class="pb-1 pr-3">Etiqueta</th><th class="pb-1 pr-3">Tipo</th><th class="pb-1 pr-3">Origen</th><th class="pb-1 pr-3">Sección</th><th class="pb-1 pr-3">Tabla</th><th class="pb-1 pr-3">Detalle</th><th class="pb-1 pr-3">Especial</th><th class="pb-1 pr-3" /></tr>
        </thead>
        <tbody>
          <template v-for="f in type.field_definitions" :key="f.id">
            <tr v-if="editingFieldId === f.id" class="text-slate-700 dark:text-slate-300">
              <td class="py-1 pr-3" colspan="9">
                <form class="grid grid-cols-3 gap-2 text-sm" @submit.prevent="saveField(f)">
                  <input v-model="fieldEdit.field_key" placeholder="field_key" required class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900" />
                  <input v-model="fieldEdit.label" placeholder="Etiqueta visible" required class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900" />
                  <select v-model="fieldEdit.data_type" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
                    <option v-for="dt in DATA_TYPES" :key="dt" :value="dt">{{ dt }}</option>
                  </select>
                  <select v-model="fieldEdit.origen" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
                    <option v-for="o in origenesPara(type)" :key="o.value" :value="o.value">{{ o.label }}</option>
                  </select>
                  <select v-model.number="fieldEdit.seccion" required class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
                    <option v-for="s in type.secciones" :key="s.id" :value="s.id">{{ s.nombre }}</option>
                  </select>
                  <input v-model.number="fieldEdit.orden" type="number" placeholder="Orden" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900" />
                  <input
                    v-if="fieldEdit.data_type === 'SELECT' || fieldEdit.data_type === 'MULTISELECT'"
                    v-model="fieldEdit.options"
                    placeholder="Opciones separadas por coma"
                    class="col-span-2 rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900"
                  />
                  <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldEdit.required" type="checkbox" /> Obligatorio</label>
                  <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldEdit.mostrar_en_tabla" type="checkbox" /> Mostrar en tabla</label>
                  <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldEdit.mostrar_en_detalle" type="checkbox" /> Mostrar en detalle</label>
                  <template v-if="fieldEdit.origen === 'CARGA'">
                    <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldEdit.es_nombre_cliente" type="checkbox" /> Es el nombre del cliente</label>
                    <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldEdit.es_telefono_contacto" type="checkbox" /> Es el teléfono de contacto</label>
                    <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldEdit.es_documento_identidad" type="checkbox" /> Es el documento de identidad</label>
                  </template>
                  <div class="col-span-3 flex gap-2">
                    <button type="submit" class="rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700">Guardar</button>
                    <button type="button" class="text-sm text-slate-400 underline" @click="cancelEditField">Cancelar</button>
                  </div>
                </form>
              </td>
            </tr>
            <tr v-else class="text-slate-700 dark:text-slate-300">
              <td class="py-1 pr-3">{{ f.field_key }}</td>
              <td class="py-1 pr-3">{{ f.label }}</td>
              <td class="py-1 pr-3">{{ f.data_type }}</td>
              <td class="py-1 pr-3">{{ f.origen === 'CAPTURA_GESTION' ? 'Captura' : 'Carga' }}</td>
              <td class="py-1 pr-3">{{ type.secciones.find((s) => s.id === f.seccion)?.nombre ?? '—' }}</td>
              <td class="py-1 pr-3">{{ f.mostrar_en_tabla ? 'Sí' : 'No' }}</td>
              <td class="py-1 pr-3">{{ f.mostrar_en_detalle ? 'Sí' : 'No' }}</td>
              <td class="py-1 pr-3 space-x-1">
                <span v-if="f.es_nombre_cliente" class="rounded bg-slate-200 px-1.5 py-0.5 dark:bg-slate-800">Nombre</span>
                <span v-if="f.es_telefono_contacto" class="rounded bg-slate-200 px-1.5 py-0.5 dark:bg-slate-800">Teléfono</span>
                <span v-if="f.es_documento_identidad" class="rounded bg-slate-200 px-1.5 py-0.5 dark:bg-slate-800">Documento</span>
              </td>
              <td class="py-1 pr-3 whitespace-nowrap">
                <span class="inline-flex gap-1">
                  <ActionButton variant="edit" icon="edit" label="Editar" icon-only @click="startEditField(f)" />
                  <ActionButton variant="danger" icon="delete" label="Eliminar" icon-only @click="handleDeleteField(f)" />
                </span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-if="type.field_definitions.length && faltantes(type.field_definitions).length" class="mt-2 text-xs text-amber-600">
        ⚠ Falta marcar el campo de {{ faltantes(type.field_definitions).join(' y el campo de ') }} —
        la carga de leads no va a funcionar hasta que los 3 estén definidos.
      </p>

      <form v-if="fieldForms[type.id]" class="mt-3 grid grid-cols-3 gap-2 text-sm" @submit.prevent="handleCreateField(type.id)">
        <input v-model="fieldForms[type.id].field_key" placeholder="field_key (ej. monto_linea)" required class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900" />
        <input v-model="fieldForms[type.id].label" placeholder="Etiqueta visible" required class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900" />
        <select v-model="fieldForms[type.id].data_type" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
          <option v-for="dt in DATA_TYPES" :key="dt" :value="dt">{{ dt }}</option>
        </select>
        <select v-model="fieldForms[type.id].origen" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
          <option v-for="o in origenesPara(type)" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <select v-model.number="fieldForms[type.id].seccion" required class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
          <option :value="null" disabled>Sección…</option>
          <option v-for="s in type.secciones" :key="s.id" :value="s.id">{{ s.nombre }}</option>
        </select>
        <input v-model.number="fieldForms[type.id].orden" type="number" placeholder="Orden" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900" />
        <input
          v-if="fieldForms[type.id].data_type === 'SELECT' || fieldForms[type.id].data_type === 'MULTISELECT'"
          v-model="fieldForms[type.id].options"
          placeholder="Opciones separadas por coma"
          class="col-span-2 rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900"
        />
        <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldForms[type.id].required" type="checkbox" /> Obligatorio</label>
        <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldForms[type.id].mostrar_en_tabla" type="checkbox" /> Mostrar en tabla</label>
        <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldForms[type.id].mostrar_en_detalle" type="checkbox" /> Mostrar en detalle</label>
        <template v-if="fieldForms[type.id].origen === 'CARGA'">
          <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldForms[type.id].es_nombre_cliente" type="checkbox" /> Es el nombre del cliente</label>
          <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldForms[type.id].es_telefono_contacto" type="checkbox" /> Es el teléfono de contacto</label>
          <label class="flex items-center gap-1 text-xs text-slate-500"><input v-model="fieldForms[type.id].es_documento_identidad" type="checkbox" /> Es el documento de identidad</label>
        </template>
        <button type="submit" class="col-span-3 rounded-md border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-700">+ Agregar campo</button>
      </form>
    </div>
    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
