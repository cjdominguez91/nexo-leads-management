<script setup lang="ts">
import { CircleHelp, TriangleAlert } from '@lucide/vue'
import { onMounted, onUnmounted } from 'vue'

import { useConfirmStore } from '@/stores/confirm'

const store = useConfirmStore()

function onKeydown(event: KeyboardEvent) {
  if (!store.visible) return
  if (event.key === 'Escape') store.respond(false)
  if (event.key === 'Enter') store.respond(true)
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div
    v-if="store.visible"
    class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4"
    @click.self="store.respond(false)"
  >
    <div class="card w-full max-w-sm rounded-xl p-6 shadow-xl">
      <div class="flex items-start gap-3">
        <div
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
          :class="store.options.danger ? 'bg-red-100 dark:bg-red-950' : 'bg-brand-100 dark:bg-brand-950'"
        >
          <TriangleAlert v-if="store.options.danger" :size="20" class="text-red-600 dark:text-red-400" />
          <CircleHelp v-else :size="20" class="text-brand-600 dark:text-brand-400" />
        </div>
        <div class="flex-1 pt-1">
          <h2 class="text-sm font-semibold text-slate-900 dark:text-slate-100">{{ store.options.title }}</h2>
          <p v-if="store.options.message" class="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {{ store.options.message }}
          </p>
        </div>
      </div>

      <div class="mt-5 flex justify-end gap-2">
        <button
          class="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          @click="store.respond(false)"
        >
          {{ store.options.cancelText }}
        </button>
        <button
          class="rounded-md px-3 py-1.5 text-sm font-medium text-white"
          :class="store.options.danger ? 'bg-red-600 hover:bg-red-700' : 'bg-brand-600 hover:bg-brand-700'"
          @click="store.respond(true)"
        >
          {{ store.options.confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>
