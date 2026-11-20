<script setup lang="ts">
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { computed } from 'vue'

const props = defineProps<{
  page: number
  pageSize: number
  count: number
}>()

const emit = defineEmits<{ 'update:page': [number] }>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.count / props.pageSize)))
const rangeStart = computed(() => (props.count === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const rangeEnd = computed(() => Math.min(props.page * props.pageSize, props.count))
</script>

<template>
  <div class="flex items-center justify-between gap-3 pt-3 text-xs text-slate-500 dark:text-slate-400">
    <span>{{ count === 0 ? 'Sin resultados' : `${rangeStart}–${rangeEnd} de ${count}` }}</span>
    <div class="flex items-center gap-1">
      <button
        type="button"
        :disabled="page <= 1"
        class="flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
        @click="emit('update:page', page - 1)"
      >
        <ChevronLeft :size="14" /> Anterior
      </button>
      <span class="px-1">Página {{ page }} de {{ totalPages }}</span>
      <button
        type="button"
        :disabled="page >= totalPages"
        class="flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:hover:bg-slate-800"
        @click="emit('update:page', page + 1)"
      >
        Siguiente <ChevronRight :size="14" />
      </button>
    </div>
  </div>
</template>
