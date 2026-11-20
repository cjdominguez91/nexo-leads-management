<script setup lang="ts">
import { ArrowDown, ArrowUp, ArrowUpDown } from '@lucide/vue'
import { createColumnHelper, FlexRender, getCoreRowModel, useVueTable } from '@tanstack/vue-table'
import { computed, ref } from 'vue'

import type { CampaignFieldDefinition } from '@/api/campaigns'
import type { Lead } from '@/api/leads'
import { formatFieldValue } from '@/composables/useFieldFormatter'

// Permite guardar el query param de filtro de cada columna en su columnDef
// (ver `meta: { filterParam }` abajo) — TanStack requiere esta ampliación
// de módulo para tipar `meta` más allá de su interfaz vacía por defecto.
declare module '@tanstack/vue-table' {
  interface ColumnMeta<TData, TValue> {
    filterParam?: string
  }
}

const props = withDefaults(
  defineProps<{
    fieldDefinitions: CampaignFieldDefinition[]
    leads: Lead[]
    selectable?: boolean
  }>(),
  { selectable: false },
)

const emit = defineEmits<{
  'row-click': [lead: Lead]
  'selection-change': [ids: number[]]
  'sort-change': [ordering: string]
  'filter-change': [filters: Record<string, string>]
}>()

const selected = ref<Set<number>>(new Set())
const sortColumnId = ref<string | null>(null)
const sortDesc = ref(false)
const columnFilters = ref<Record<string, string>>({})
let filterDebounce: ReturnType<typeof setTimeout> | null = null

const dynamicColumns = computed(() =>
  [...props.fieldDefinitions]
    .filter(
      (f) =>
        f.origen === 'CARGA' &&
        f.mostrar_en_tabla &&
        !f.es_nombre_cliente &&
        !f.es_telefono_contacto &&
        !f.es_documento_identidad,
    )
    .sort((a, b) => a.orden - b.orden),
)

function displayName(lead: Lead) {
  return lead.cliente_nombre || lead.documento_identidad || '—'
}

function formatFecha(value: string | null) {
  return value ? new Date(value).toLocaleString('es-PE') : '—'
}

function toggle(id: number) {
  if (selected.value.has(id)) selected.value.delete(id)
  else selected.value.add(id)
  emit('selection-change', [...selected.value])
}

function toggleAll(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  selected.value = checked ? new Set(props.leads.map((l) => l.id)) : new Set()
  emit('selection-change', [...selected.value])
}

function onFilterInput(filterParam: string, event: Event) {
  const value = (event.target as HTMLInputElement).value
  columnFilters.value = { ...columnFilters.value, [filterParam]: value }
  if (filterDebounce) clearTimeout(filterDebounce)
  filterDebounce = setTimeout(() => {
    const active = Object.fromEntries(Object.entries(columnFilters.value).filter(([, v]) => v.trim() !== ''))
    emit('filter-change', active)
  }, 350)
}

// El id de cada columna ordenable es el `ordering_fields` que espera el
// backend (ver apps.leads.views.LeadViewSet) — así el ordering string sale
// directo del id sin tabla de traducción aparte. `meta.filterParam` hace lo
// mismo para el query param del filtro por columna (ver apps.leads.filters.LeadFilter).
const columnHelper = createColumnHelper<Lead>()

const columns = computed(() => [
  columnHelper.accessor('documento_identidad', {
    id: 'documento_identidad',
    header: 'Documento',
    meta: { filterParam: 'documento_identidad' },
  }),
  columnHelper.accessor('cliente_nombre', {
    id: 'cliente_nombre',
    header: 'Cliente',
    cell: (info) => displayName(info.row.original),
    meta: { filterParam: 'cliente_nombre' },
  }),
  columnHelper.accessor('telefono', {
    id: 'telefono',
    header: 'Teléfono',
    enableSorting: false,
    cell: (info) => info.getValue() || '—',
    meta: { filterParam: 'telefono' },
  }),
  columnHelper.accessor('agencia_nombre', {
    id: 'agencia__nombre',
    header: 'Agencia',
    meta: { filterParam: 'agencia__nombre' },
  }),
  columnHelper.accessor('estado', { id: 'estado', header: 'Estado', meta: { filterParam: 'estado' } }),
  columnHelper.accessor('usuario_asignado_email', {
    id: 'usuario_asignado__email',
    header: 'Asignado a',
    cell: (info) => info.getValue() ?? '—',
    meta: { filterParam: 'usuario_asignado__email' },
  }),
  ...dynamicColumns.value.map((col) =>
    columnHelper.display({
      id: `attr:${col.field_key}`,
      header: col.label,
      cell: (info) => formatFieldValue(info.row.original.atributos[col.field_key], col.data_type),
      meta: { filterParam: `attr__${col.field_key}` },
    }),
  ),
  columnHelper.accessor('categoria_actual_nombre', {
    id: 'categoria_actual_nombre',
    header: 'Categoría',
    enableSorting: false,
    cell: (info) => info.getValue() ?? '—',
    meta: { filterParam: 'categoria_actual__nombre' },
  }),
  columnHelper.accessor('subcategoria_actual_nombre', {
    id: 'subcategoria_actual_nombre',
    header: 'Subcategoría',
    enableSorting: false,
    cell: (info) => info.getValue() ?? '—',
    meta: { filterParam: 'subcategoria_actual__nombre' },
  }),
  columnHelper.accessor('fecha_ultima_gestion', {
    id: 'fecha_ultima_gestion',
    header: 'Última gestión',
    cell: (info) => formatFecha(info.getValue()),
  }),
])

const table = useVueTable({
  get data() {
    return props.leads
  },
  get columns() {
    return columns.value
  },
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
    emit('sort-change', first ? `${first.desc ? '-' : ''}${first.id}` : '')
  },
})
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-left text-sm">
      <thead class="text-slate-500 dark:text-slate-400">
        <tr v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
          <th v-if="selectable" class="border-b border-slate-200 pb-2 pr-2 dark:border-slate-800">
            <input type="checkbox" @change="toggleAll" />
          </th>
          <th
            v-for="header in headerGroup.headers"
            :key="header.id"
            class="border-b border-slate-200 pb-2 pr-4 dark:border-slate-800"
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
          <th v-if="selectable" class="border-b border-slate-200 pb-2 pr-2 dark:border-slate-800" />
          <th
            v-for="header in headerGroup.headers"
            :key="`${header.id}-filter`"
            class="border-b border-slate-200 pb-2 pr-4 font-normal dark:border-slate-800"
            @click.stop
          >
            <input
              v-if="header.column.columnDef.meta?.filterParam"
              type="text"
              placeholder="Filtrar…"
              :value="columnFilters[header.column.columnDef.meta.filterParam] ?? ''"
              class="w-full min-w-24 rounded-md border border-slate-300 px-2 py-1 text-xs font-normal focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-900"
              @input="onFilterInput(header.column.columnDef.meta!.filterParam!, $event)"
              @click.stop
            />
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in table.getRowModel().rows"
          :key="row.id"
          class="cursor-pointer text-slate-800 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-900"
          @click="emit('row-click', row.original)"
        >
          <td v-if="selectable" class="border-b border-slate-100 py-2 pr-2 dark:border-slate-900" @click.stop>
            <input type="checkbox" :checked="selected.has(row.original.id)" @change="toggle(row.original.id)" />
          </td>
          <td
            v-for="cell in row.getVisibleCells()"
            :key="cell.id"
            class="border-b border-slate-100 py-2 pr-4 dark:border-slate-900"
          >
            <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
          </td>
        </tr>
        <tr v-if="leads.length === 0">
          <td :colspan="columns.length + (selectable ? 1 : 0)" class="py-6 text-center text-slate-400">
            Sin registros.
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
