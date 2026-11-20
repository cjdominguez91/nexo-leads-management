<script setup lang="ts">
import { computed, ref } from 'vue'

export interface PickerOption {
  id: number
  label: string
}

const props = defineProps<{
  options: PickerOption[]
  modelValue: number[]
  placeholder?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [number[]] }>()

const query = ref('')
const open = ref(false)

const selectedOptions = computed(() => props.options.filter((o) => props.modelValue.includes(o.id)))

const filteredOptions = computed(() => {
  const q = query.value.trim().toLowerCase()
  const base = props.options.filter((o) => !props.modelValue.includes(o.id))
  const matches = q ? base.filter((o) => o.label.toLowerCase().includes(q)) : base
  return matches.slice(0, 50)
})

function add(id: number) {
  emit('update:modelValue', [...props.modelValue, id])
  query.value = ''
  open.value = false
}

function remove(id: number) {
  emit('update:modelValue', props.modelValue.filter((v) => v !== id))
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
    <div
      v-if="selectedOptions.length"
      class="mb-1.5 flex flex-wrap gap-1.5"
    >
      <span
        v-for="opt in selectedOptions"
        :key="opt.id"
        class="inline-flex items-center gap-1 rounded-full bg-slate-200 px-2 py-0.5 text-xs text-slate-700 dark:bg-slate-800 dark:text-slate-200"
      >
        {{ opt.label }}
        <button type="button" class="text-slate-500 hover:text-red-600" @click="remove(opt.id)">×</button>
      </span>
    </div>

    <input
      v-model="query"
      type="text"
      :placeholder="placeholder ?? 'Buscar…'"
      class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
      @focus="open = true"
      @blur="onBlur"
    />

    <div
      v-if="open"
      class="card absolute z-10 mt-1 max-h-48 w-full overflow-y-auto shadow-lg"
    >
      <button
        v-for="opt in filteredOptions"
        :key="opt.id"
        type="button"
        class="block w-full px-3 py-1.5 text-left text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
        @mousedown.prevent="add(opt.id)"
      >
        {{ opt.label }}
      </button>
      <p v-if="filteredOptions.length === 0" class="px-3 py-1.5 text-xs text-slate-400">Sin resultados.</p>
    </div>
  </div>
</template>
