<script setup lang="ts">
import { computed, ref } from 'vue'

import type { EfectividadRow } from '@/api/dashboards'

const props = defineProps<{
  rows: EfectividadRow[]
  columnaLabel: string
  clickable?: boolean
}>()

const emit = defineEmits<{ 'row-click': [row: EfectividadRow] }>()

const sort = ref<{ campo: keyof EfectividadRow; desc: boolean }>({ campo: 'total', desc: true })

function toggleSort(campo: keyof EfectividadRow) {
  sort.value = sort.value.campo === campo ? { campo, desc: !sort.value.desc } : { campo, desc: true }
}

const ordenadas = computed(() => {
  const { campo, desc } = sort.value
  return [...props.rows].sort((a, b) => {
    const va = a[campo]
    const vb = b[campo]
    const diff = typeof va === 'string' && typeof vb === 'string' ? va.localeCompare(vb) : Number(va) - Number(vb)
    return desc ? -diff : diff
  })
})

function fmtPct(value: number) {
  return `${Math.round(value * 100)}%`
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-left text-sm">
      <thead class="text-slate-500 dark:text-slate-400">
        <tr>
          <th class="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 pb-2 pr-4 dark:border-slate-800" @click="toggleSort('nombre')">{{ columnaLabel }}</th>
          <th class="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 pb-2 pr-4 text-right dark:border-slate-800" @click="toggleSort('total')">Total</th>
          <th class="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 pb-2 pr-4 text-right dark:border-slate-800" @click="toggleSort('contactados')">Contactados</th>
          <th class="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 pb-2 pr-4 text-right dark:border-slate-800" @click="toggleSort('tasa_contacto')">% Contacto</th>
          <th class="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 pb-2 pr-4 text-right dark:border-slate-800" @click="toggleSort('ganados')">Ganados</th>
          <th class="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 pb-2 pr-4 text-right dark:border-slate-800" @click="toggleSort('tasa_efectividad')">% Efectividad</th>
          <th class="cursor-pointer select-none whitespace-nowrap border-b border-slate-200 pb-2 text-right dark:border-slate-800" @click="toggleSort('perdidos')">Perdidos</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in ordenadas"
          :key="row.id"
          class="text-slate-800 dark:text-slate-200"
          :class="clickable ? 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900' : ''"
          @click="clickable && emit('row-click', row)"
        >
          <td class="border-b border-slate-100 py-2 pr-4 font-medium dark:border-slate-900">{{ row.nombre }}</td>
          <td class="border-b border-slate-100 py-2 pr-4 text-right tabular-nums dark:border-slate-900">{{ row.total }}</td>
          <td class="border-b border-slate-100 py-2 pr-4 text-right tabular-nums dark:border-slate-900">{{ row.contactados }}</td>
          <td class="border-b border-slate-100 py-2 pr-4 text-right tabular-nums dark:border-slate-900">{{ fmtPct(row.tasa_contacto) }}</td>
          <td class="border-b border-slate-100 py-2 pr-4 text-right tabular-nums text-emerald-600 dark:border-slate-900 dark:text-emerald-400">{{ row.ganados }}</td>
          <td class="border-b border-slate-100 py-2 pr-4 text-right tabular-nums dark:border-slate-900">{{ fmtPct(row.tasa_efectividad) }}</td>
          <td class="border-b border-slate-100 py-2 text-right tabular-nums text-red-600 dark:border-slate-900 dark:text-red-400">{{ row.perdidos }}</td>
        </tr>
        <tr v-if="ordenadas.length === 0">
          <td colspan="7" class="py-6 text-center text-slate-400">Sin datos dentro de tu alcance.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
