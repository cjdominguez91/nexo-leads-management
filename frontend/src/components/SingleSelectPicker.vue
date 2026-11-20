<script setup lang="ts">
import { computed, ref } from 'vue'

import type { PickerOption } from './MultiSelectPicker.vue'

const props = defineProps<{
  options: PickerOption[]
  modelValue: number | null
  placeholder?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [number | null] }>()

const query = ref('')
const open = ref(false)

const selectedOption = computed(() => props.options.find((o) => o.id === props.modelValue) ?? null)

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase()
  const matches = q ? props.options.filter((o) => o.label.toLowerCase().includes(q)) : props.options
  return matches.slice(0, 50)
})

function select(id: number) {
  emit('update:modelValue', id)
  query.value = ''
  open.value = false
}

function clear() {
  emit('update:modelValue', null)
}

function onBlur() {
  // timeout para permitir que el click en una opción se registre antes de cerrar
  setTimeout(() => {
    open.value = false
  }, 150)
}
</script>

<template>
  <div class="relative">
    <div v-if="selectedOption" class="mb-1.5 flex flex-wrap gap-1.5">
      <span class="inline-flex items-center gap-1 rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-200">
        {{ selectedOption.label }}
        <button type="button" class="text-slate-500 hover:text-red-600" @click="clear">×</button>
      </span>
    </div>

    <input
      v-model="query"
      type="text"
      :placeholder="selectedOption ? 'Buscar para cambiar…' : (placeholder ?? 'Buscar…')"
      class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
      @focus="open = true"
      @blur="onBlur"
    />

    <div v-if="open" class="card absolute z-10 mt-1 max-h-48 w-full overflow-y-auto shadow-lg">
      <button
        v-for="opt in filteredOptions"
        :key="opt.id"
        type="button"
        class="block w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
        :class="{ 'bg-brand-50 dark:bg-brand-950': opt.id === modelValue }"
        @mousedown.prevent="select(opt.id)"
      >
        {{ opt.label }}
      </button>
      <p v-if="filteredOptions.length === 0" class="px-3 py-1.5 text-xs text-slate-400">Sin resultados.</p>
    </div>
  </div>
</template>
