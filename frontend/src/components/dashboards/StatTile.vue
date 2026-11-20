<script setup lang="ts">
defineProps<{
  label: string
  value: string
  alert?: boolean
  /** Puntos porcentuales vs el período anterior — ej. 0.05 = +5 pts. */
  deltaPts?: number | null
}>()

function deltaLabel(delta: number) {
  const pts = Math.round(delta * 1000) / 10
  return `${pts > 0 ? '+' : ''}${pts} pts vs período anterior`
}
</script>

<template>
  <div class="card p-4">
    <p class="text-xs text-slate-500 dark:text-slate-400">{{ label }}</p>
    <p
      class="mt-1 text-2xl font-semibold"
      :class="alert ? 'text-amber-600 dark:text-amber-400' : 'text-slate-900 dark:text-slate-100'"
    >
      {{ value }}
    </p>
    <p
      v-if="deltaPts !== undefined && deltaPts !== null"
      class="mt-0.5 text-xs font-medium"
      :class="deltaPts > 0 ? 'text-emerald-600 dark:text-emerald-400' : deltaPts < 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-400'"
    >
      {{ deltaLabel(deltaPts) }}
    </p>
  </div>
</template>
