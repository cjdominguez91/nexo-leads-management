<script setup lang="ts">
import { computed, ref } from 'vue'

export interface TrendSeries {
  name: string
  color: string
  points: { date: string; value: number }[]
}

const props = defineProps<{ series: TrendSeries[] }>()

const WIDTH = 600
const HEIGHT = 200
const PAD_LEFT = 32
const PAD_BOTTOM = 20
const PAD_TOP = 10

const svgRef = ref<SVGSVGElement | null>(null)
const hoverIndex = ref<number | null>(null)

const labels = computed(() => props.series[0]?.points.map((p) => p.date) ?? [])
const maxValue = computed(() => Math.max(1, ...props.series.flatMap((s) => s.points.map((p) => p.value))))

const plotWidth = WIDTH - PAD_LEFT - 8
const plotHeight = HEIGHT - PAD_TOP - PAD_BOTTOM

function xAt(index: number) {
  const n = labels.value.length
  return PAD_LEFT + (n <= 1 ? 0 : (index / (n - 1)) * plotWidth)
}
function yAt(value: number) {
  return PAD_TOP + plotHeight - (value / maxValue.value) * plotHeight
}

function linePath(points: { value: number }[]) {
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yAt(p.value)}`).join(' ')
}
function areaPath(points: { value: number }[]) {
  const baseline = PAD_TOP + plotHeight
  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yAt(p.value)}`).join(' ')
  return `${line} L ${xAt(points.length - 1)} ${baseline} L ${xAt(0)} ${baseline} Z`
}

const gridSteps = [0, 0.25, 0.5, 0.75, 1]

function formatDate(iso: string) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' })
}

function onMove(event: MouseEvent) {
  if (!svgRef.value || labels.value.length === 0) return
  const rect = svgRef.value.getBoundingClientRect()
  const relX = ((event.clientX - rect.left) / rect.width) * WIDTH
  const n = labels.value.length
  const ratio = n <= 1 ? 0 : (relX - PAD_LEFT) / plotWidth
  const index = Math.min(n - 1, Math.max(0, Math.round(ratio * (n - 1))))
  hoverIndex.value = index
}
function onLeave() {
  hoverIndex.value = null
}
</script>

<template>
  <div class="space-y-2">
    <div v-if="series.length > 1" class="flex flex-wrap gap-4 text-xs text-slate-600 dark:text-slate-300">
      <span v-for="s in series" :key="s.name" class="flex items-center gap-1.5">
        <span class="inline-block h-0.5 w-4 rounded-full" :style="{ backgroundColor: s.color }" />
        {{ s.name }}
      </span>
    </div>

    <div class="relative">
      <svg
        ref="svgRef"
        :viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
        class="w-full"
        style="max-height: 220px"
        @mousemove="onMove"
        @mouseleave="onLeave"
      >
        <line
          v-for="step in gridSteps"
          :key="step"
          :x1="PAD_LEFT"
          :x2="WIDTH - 8"
          :y1="PAD_TOP + plotHeight * (1 - step)"
          :y2="PAD_TOP + plotHeight * (1 - step)"
          stroke="currentColor"
          class="text-slate-200 dark:text-slate-800"
          stroke-width="1"
        />
        <text
          v-for="step in gridSteps"
          :key="`t-${step}`"
          :x="PAD_LEFT - 6"
          :y="PAD_TOP + plotHeight * (1 - step) + 3"
          text-anchor="end"
          class="fill-slate-400 text-[9px]"
        >
          {{ Math.round(maxValue * step) }}
        </text>

        <template v-for="s in series" :key="s.name">
          <path :d="areaPath(s.points)" :fill="s.color" opacity="0.1" stroke="none" />
          <path :d="linePath(s.points)" fill="none" :stroke="s.color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </template>

        <line
          v-if="hoverIndex !== null"
          :x1="xAt(hoverIndex)"
          :x2="xAt(hoverIndex)"
          :y1="PAD_TOP"
          :y2="PAD_TOP + plotHeight"
          stroke="currentColor"
          class="text-slate-300 dark:text-slate-700"
          stroke-width="1"
        />
        <template v-if="hoverIndex !== null">
          <circle
            v-for="s in series"
            :key="`dot-${s.name}`"
            :cx="xAt(hoverIndex)"
            :cy="yAt(s.points[hoverIndex]?.value ?? 0)"
            r="4"
            :fill="s.color"
            class="stroke-white dark:stroke-[#2A3042]"
            stroke-width="2"
          />
        </template>

        <text v-if="labels.length" :x="PAD_LEFT" :y="HEIGHT - 4" class="fill-slate-400 text-[9px]">
          {{ formatDate(labels[0]) }}
        </text>
        <text v-if="labels.length > 1" :x="WIDTH - 8" :y="HEIGHT - 4" text-anchor="end" class="fill-slate-400 text-[9px]">
          {{ formatDate(labels[labels.length - 1]) }}
        </text>
      </svg>

      <div
        v-if="hoverIndex !== null"
        class="card pointer-events-none absolute top-0 z-10 -translate-x-1/2 px-2 py-1.5 text-xs shadow-lg"
        :style="{ left: `${(xAt(hoverIndex) / WIDTH) * 100}%` }"
      >
        <p class="mb-1 font-medium text-slate-700 dark:text-slate-200">{{ formatDate(labels[hoverIndex]) }}</p>
        <p v-for="s in series" :key="s.name" class="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
          <span class="inline-block h-0.5 w-3 rounded-full" :style="{ backgroundColor: s.color }" />
          <span class="font-semibold tabular-nums text-slate-800 dark:text-slate-100">{{ s.points[hoverIndex]?.value ?? 0 }}</span>
          {{ s.name }}
        </p>
      </div>
    </div>

    <p v-if="labels.length === 0" class="py-4 text-center text-xs text-slate-400">Sin actividad en este período.</p>
  </div>
</template>
