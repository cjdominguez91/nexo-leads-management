<script setup lang="ts">
import { Search, X } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import { useUserPickerStore } from '@/stores/userPicker'

const store = useUserPickerStore()
const query = ref('')

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return store.users
  return store.users.filter((u) => {
    const haystack = [u.email, u.first_name, u.last_name, u.role_nombre, u.agencia_principal_nombre]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return haystack.includes(q)
  })
})

watch(
  () => store.visible,
  (visible) => {
    if (visible) query.value = ''
  },
)

function onKeydown(event: KeyboardEvent) {
  if (!store.visible) return
  if (event.key === 'Escape') store.cancel()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div
    v-if="store.visible"
    class="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/50 p-4 pt-24"
    @click.self="store.cancel()"
  >
    <div class="card flex max-h-[65vh] w-full max-w-lg flex-col rounded-xl shadow-xl">
      <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
        <h2 class="text-sm font-semibold text-slate-900 dark:text-slate-100">{{ store.title }}</h2>
        <button class="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200" @click="store.cancel()">
          <X :size="18" />
        </button>
      </div>

      <div class="border-b border-slate-200 p-3 dark:border-slate-800">
        <div class="relative">
          <Search :size="16" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            v-model="query"
            type="text"
            autofocus
            placeholder="Buscar por nombre, correo, rol o agencia…"
            class="w-full rounded-md border border-slate-300 py-2 pl-9 pr-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-900"
          />
        </div>
      </div>

      <div class="flex-1 overflow-y-auto">
        <button
          v-for="user in filtered"
          :key="user.id"
          type="button"
          class="flex w-full items-center justify-between gap-3 border-b border-slate-100 px-4 py-2.5 text-left hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800"
          @click="store.select(user)"
        >
          <div class="min-w-0">
            <p class="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
              {{ user.first_name }} {{ user.last_name }}
            </p>
            <p class="truncate text-xs text-slate-500 dark:text-slate-400">{{ user.email }}</p>
          </div>
          <div class="shrink-0 text-right text-xs">
            <span class="block rounded-full bg-brand-100 px-2 py-0.5 font-medium text-brand-700 dark:bg-brand-950 dark:text-brand-300">
              {{ user.role_nombre ?? '—' }}
            </span>
            <span v-if="user.agencia_principal_nombre" class="mt-1 block text-slate-400">{{ user.agencia_principal_nombre }}</span>
          </div>
        </button>
        <p v-if="filtered.length === 0" class="px-4 py-6 text-center text-sm text-slate-400">Sin resultados.</p>
      </div>
    </div>
  </div>
</template>
