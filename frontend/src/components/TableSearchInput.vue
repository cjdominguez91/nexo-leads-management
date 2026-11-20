<script setup lang="ts">
import { Search } from '@lucide/vue'
import { ref } from 'vue'

const props = defineProps<{ placeholder?: string }>()
const emit = defineEmits<{ search: [string] }>()

const value = ref('')

function onInput(event: Event) {
  value.value = (event.target as HTMLInputElement).value
  emit('search', value.value)
}
</script>

<template>
  <div class="relative max-w-xs">
    <Search :size="16" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
    <input
      :value="value"
      type="text"
      :placeholder="props.placeholder ?? 'Buscar…'"
      class="w-full rounded-md border border-slate-300 py-2 pl-9 pr-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-900"
      @input="onInput"
    />
  </div>
</template>
