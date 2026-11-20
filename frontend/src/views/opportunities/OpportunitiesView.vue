<script setup lang="ts">
import { ArrowDown, ArrowUp, ArrowUpDown } from '@lucide/vue'
import { createColumnHelper, FlexRender, getCoreRowModel, useVueTable } from '@tanstack/vue-table'
import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import type { AppNotification } from '@/api/notifications'
import * as opportunitiesApi from '@/api/opportunities'
import type { Opportunity } from '@/api/opportunities'
import TablePagination from '@/components/TablePagination.vue'

declare module '@tanstack/vue-table' {
  interface ColumnMeta<TData, TValue> {
    filterParam?: string
  }
}

const router = useRouter()

const opportunities = ref<Opportunity[]>([])
const count = ref(0)
const columnFilters = ref<Record<string, string>>({})
const ordering = ref('')
const page = ref(1)
const pageSize = 25
const loading = ref(false)
let filterDebounce: ReturnType<typeof setTimeout> | null = null

function params() {
  return { ordering: ordering.value || undefined, page: page.value, ...columnFilters.value }
}

async function loadData() {
  loading.value = true
  try {
    const res = await opportunitiesApi.fetchOpportunities(params())
    opportunities.value = res.results
    count.value = res.count
  } finally {
    loading.value = false
  }
}

function onFilterInput(filterParam: string, event: Event) {
  const value = (event.target as HTMLInputElement).value
  columnFilters.value = { ...columnFilters.value, [filterParam]: value }
  if (filterDebounce) clearTimeout(filterDebounce)
  filterDebounce = setTimeout(() => {
    page.value = 1
    loadData()
  }, 350)
}

function handleSort(nextOrdering: string) {
  ordering.value = nextOrdering
  page.value = 1
  loadData()
}

function handlePage(nextPage: number) {
  page.value = nextPage
  loadData()
}

function goToLead(opportunity: Opportunity) {
  router.push({ name: 'lead-detail', params: { id: opportunity.lead } })
}

function estadoClasses(estado: string) {
  if (estado === 'GANADA') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
  if (estado === 'PERDIDA') return 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
  return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
}

function formatFecha(value: string | null) {
  return value ? new Date(value).toLocaleString('es-PE') : '—'
}

function displayName(opp: Opportunity) {
  return opp.cliente_nombre || opp.documento_identidad || '—'
}

// Solo las cabeceras vienen de TanStack (orden + fila de filtros) — el
// cuerpo sigue armado a mano porque Origen y Estado son badges con clases
// condicionales, igual que en UsersView.vue.
const columnHelper = createColumnHelper<Opportunity>()
const columns = [
  columnHelper.accessor('documento_identidad', {
    id: 'lead__documento_identidad',
    header: 'Documento',
    meta: { filterParam: 'documento_identidad' },
  }),
  columnHelper.accessor('cliente_nombre', {
    id: 'lead__cliente_nombre',
    header: 'Cliente',
    meta: { filterParam: 'cliente_nombre' },
  }),
  columnHelper.accessor('campaign_nombre', {
    id: 'campaign__nombre',
    header: 'Campaña',
    meta: { filterParam: 'campaign_nombre' },
  }),
  columnHelper.display({ id: 'modo_carga', header: 'Origen', enableSorting: false }),
  columnHelper.accessor('fecha_proximo_contacto', { id: 'fecha_proximo_contacto', header: 'Próximo contacto' }),
  columnHelper.accessor('categoria_actual_nombre', {
    id: 'categoria_actual_nombre',
    header: 'Categoría',
    enableSorting: false,
    meta: { filterParam: 'categoria_actual_nombre' },
  }),
  columnHelper.accessor('subcategoria_actual_nombre', {
    id: 'subcategoria_actual_nombre',
    header: 'Subcategoría',
    enableSorting: false,
    meta: { filterParam: 'subcategoria_actual_nombre' },
  }),
  columnHelper.accessor('estado', { id: 'estado', header: 'Estado', meta: { filterParam: 'estado' } }),
]

const sortColumnId = ref<string | null>(null)
const sortDesc = ref(false)

const table = useVueTable({
  get data() {
    return opportunities.value
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
    handleSort(first ? `${first.desc ? '-' : ''}${first.id}` : '')
  },
})

function onLiveNotification(event: Event) {
  const notification = (event as CustomEvent<AppNotification>).detail
  if (notification.tipo === 'OPORTUNIDAD_CREADA' || notification.tipo === 'OPORTUNIDAD_CERRADA') {
    loadData()
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('nexo:notification', onLiveNotification)
})
onUnmounted(() => {
  window.removeEventListener('nexo:notification', onLiveNotification)
})
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-xl font-semibold text-slate-700 dark:text-slate-200">Oportunidades</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400">
        Nacen de tipificar un lead. Cada fila te lleva al detalle del lead — ahí está todo.
      </p>
    </div>

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
              :value="columnFilters[header.column.columnDef.meta.filterParam] ?? ''"
              class="w-full rounded-md border border-slate-300 px-2 py-1 text-xs font-normal dark:border-slate-700 dark:bg-slate-900"
              @input="onFilterInput(header.column.columnDef.meta!.filterParam!, $event)"
            />
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="opp in opportunities"
          :key="opp.id"
          class="cursor-pointer text-slate-600 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-900"
          @click="goToLead(opp)"
        >
          <td class="border-b border-slate-100 py-2 font-medium dark:border-slate-900">{{ opp.documento_identidad }}</td>
          <td class="border-b border-slate-100 py-2 dark:border-slate-900">{{ displayName(opp) }}</td>
          <td class="border-b border-slate-100 py-2 dark:border-slate-900">{{ opp.campaign_nombre }}</td>
          <td class="border-b border-slate-100 py-2 dark:border-slate-900">
            <span
              class="rounded-full px-2 py-0.5 text-xs"
              :class="opp.modo_carga === 'INDIVIDUAL' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800'"
            >
              {{ opp.modo_carga === 'INDIVIDUAL' ? 'Prospección' : 'Campaña' }}
            </span>
          </td>
          <td class="border-b border-slate-100 py-2 dark:border-slate-900">{{ formatFecha(opp.fecha_proximo_contacto) }}</td>
          <td class="border-b border-slate-100 py-2 dark:border-slate-900">{{ opp.categoria_actual_nombre ?? '—' }}</td>
          <td class="border-b border-slate-100 py-2 dark:border-slate-900">{{ opp.subcategoria_actual_nombre ?? '—' }}</td>
          <td class="border-b border-slate-100 py-2 dark:border-slate-900">
            <span class="rounded-full px-2 py-0.5 text-xs" :class="estadoClasses(opp.estado)">{{ opp.estado }}</span>
          </td>
        </tr>
        <tr v-if="!loading && opportunities.length === 0">
          <td colspan="8" class="py-6 text-center text-slate-400">Sin oportunidades todavía.</td>
        </tr>
      </tbody>
    </table>
    </div>
    <TablePagination :page="page" :page-size="pageSize" :count="count" @update:page="handlePage" />
    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
