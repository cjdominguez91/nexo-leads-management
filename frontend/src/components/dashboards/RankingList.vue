<script setup lang="ts">
import { computed } from 'vue'

import type { EfectividadRow } from '@/api/dashboards'

const props = defineProps<{
  rows: EfectividadRow[]
  direccion: 'top' | 'bottom'
}>()

const items = computed(() => {
  const sorted = [...props.rows].sort((a, b) => b.tasa_efectividad - a.tasa_efectividad)
  return props.direccion === 'top' ? sorted.slice(0, 5) : sorted.slice(-5).reverse()
})

function fmtPct(value: number) {
  return `${Math.round(value * 100)}%`
}
</script>

<template>
  <ol class="space-y-1.5 text-sm">
    <li v-for="(row, i) in items" :key="row.id" class="flex items-center justify-between gap-2">
      <span class="flex items-center gap-2 text-slate-700 dark:text-slate-300">
        <span class="w-4 shrink-0 text-right text-xs text-slate-400">{{ i + 1 }}</span>
        {{ row.nombre }}
      </span>
      <span
        class="shrink-0 font-medium tabular-nums"
        :class="direccion === 'top' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
      >
        {{ fmtPct(row.tasa_efectividad) }}
      </span>
    </li>
    <li v-if="items.length === 0" class="text-sm text-slate-400">Sin datos.</li>
  </ol>
</template>
