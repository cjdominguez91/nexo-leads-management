<script setup lang="ts">
/** Píldora de estado Activo/Inactivo con punto de color. */
withDefaults(defineProps<{ active: boolean; activeLabel?: string; inactiveLabel?: string }>(), {
  activeLabel: 'Activo',
  inactiveLabel: 'Inactivo',
})
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium"
    :class="
      active
        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400'
        : 'bg-slate-100 text-slate-500 dark:bg-slate-700/50 dark:text-slate-400'
    "
  >
    <span class="h-1.5 w-1.5 rounded-full" :class="active ? 'bg-emerald-500' : 'bg-slate-400'" />
    {{ active ? activeLabel : inactiveLabel }}
  </span>
</template>
