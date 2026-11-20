<script setup lang="ts">
import { ref } from 'vue'

export interface BarChartItem {
  label: string
  value: number
  color: string
}

const props = defineProps<{
  items: BarChartItem[]
  formatValue?: (value: number) => string
}>()

const emit = defineEmits<{ 'bar-click': [label: string] }>()

const hovered = ref<string | null>(null)
const tooltip = ref<{ x: number; y: number; label: string; value: string } | null>(null)

const maxValue = () => Math.max(1, ...props.items.map((i) => i.value))

function fmt(value: number) {
  return props.formatValue ? props.formatValue(value) : String(value)
}

function onEnter(item: BarChartItem, event: MouseEvent) {
  hovered.value = item.label
  tooltip.value = { x: event.clientX, y: event.clientY, label: item.label, value: fmt(item.value) }
}

function onMove(event: MouseEvent) {
  if (tooltip.value) {
    tooltip.value = { ...tooltip.value, x: event.clientX, y: event.clientY }
  }
}

function onLeave() {
  hovered.value = null
  tooltip.value = null
}
</script>

<template>
  <div class="space-y-2">
    <button
      v-for="item in items"
      :key="item.label"
      type="button"
      class="flex w-full items-center gap-3 rounded-md px-1 py-0.5 text-left transition-colors"
      :class="hovered === item.label ? 'bg-slate-100 dark:bg-slate-800' : ''"
      @mouseenter="onEnter(item, $event)"
      @mousemove="onMove"
      @mouseleave="onLeave"
      @click="emit('bar-click', item.label)"
    >
      <span class="w-28 shrink-0 truncate text-xs text-slate-600 dark:text-slate-300" :title="item.label">
        {{ item.label }}
      </span>
      <span class="relative h-5 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <span
          class="absolute inset-y-0 left-0 rounded-full transition-[width]"
          :style="{ width: `${(item.value / maxValue()) * 100}%`, backgroundColor: item.color }"
        />
      </span>
      <span class="w-12 shrink-0 text-right text-xs font-medium tabular-nums text-slate-700 dark:text-slate-200">
        {{ fmt(item.value) }}
      </span>
    </button>
    <p v-if="items.length === 0" class="py-4 text-center text-xs text-slate-400">Sin datos.</p>

    <Teleport to="body">
      <div
        v-if="tooltip"
        class="card pointer-events-none fixed z-50 px-2 py-1 text-xs shadow-lg"
        :style="{ left: `${tooltip.x + 12}px`, top: `${tooltip.y + 12}px` }"
      >
        <span class="font-medium text-slate-600 dark:text-slate-200">{{ tooltip.value }}</span>
        <span class="ml-1 text-slate-500 dark:text-slate-400">{{ tooltip.label }}</span>
      </div>
    </Teleport>
  </div>
</template>
