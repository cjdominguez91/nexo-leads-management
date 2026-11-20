<script setup lang="ts">
import { Waypoints } from '@lucide/vue'
import { onMounted, ref, useTemplateRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { renderGoogleButton } from '@/composables/useGoogleIdentity'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const googleButtonEl = useTemplateRef<HTMLDivElement>('googleButton')
const configLoaded = ref(false)
const configError = ref<string | null>(null)

async function redirectAfterLogin() {
  const redirect = (route.query.redirect as string) || '/'
  await router.push(redirect)
}

async function handleLocalSubmit() {
  try {
    await authStore.loginLocal(email.value, password.value)
    await redirectAfterLogin()
  } catch {
    // authStore.error ya tiene el mensaje para mostrar en el template
  }
}

async function handleGoogleCredential(idToken: string) {
  try {
    await authStore.loginGoogle(idToken)
    await redirectAfterLogin()
  } catch {
    // authStore.error ya tiene el mensaje para mostrar en el template
  }
}

onMounted(async () => {
  try {
    const config = await authStore.loadConfig()
    configLoaded.value = true

    if (config.google_enabled && config.google_client_id && googleButtonEl.value) {
      renderGoogleButton(googleButtonEl.value, config.google_client_id, handleGoogleCredential)
    }
  } catch (err: any) {
    configError.value = `No se pudo conectar con el backend (${err?.message ?? 'error desconocido'}). Revisa que la URL de la API sea correcta — actualmente apunta a: ${err?.config?.baseURL ?? 'desconocida'}.`
  }
})
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-surface-bg px-4">
    <div class="w-full max-w-sm overflow-hidden rounded-xl bg-surface-card shadow-lg">
      <div class="bg-gradient-to-br from-brand-500 to-brand-600 px-8 pb-14 pt-8 text-center">
        <h1 class="text-xl font-bold text-white">Bienvenido</h1>
        <p class="mt-1 text-sm text-brand-100">Ingresa para continuar en Nexo</p>
      </div>

      <div class="px-8 pb-8">
        <div class="-mt-10 mb-4 flex justify-center">
          <div class="flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-md ring-4 ring-white dark:bg-slate-800 dark:ring-slate-900">
            <Waypoints :size="28" class="text-accent-500" />
          </div>
        </div>

        <p v-if="authStore.error" class="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {{ authStore.error }}
        </p>
        <p v-if="configError" class="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {{ configError }}
        </p>

        <template v-if="configLoaded">
          <div v-if="authStore.config?.google_enabled" ref="googleButton" class="mb-4 flex justify-center" />

          <div v-if="authStore.config?.google_enabled && authStore.config?.local_enabled" class="mb-4 flex items-center gap-3 text-xs text-slate-400">
            <div class="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
            o
            <div class="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
          </div>

          <form v-if="authStore.config?.local_enabled" class="space-y-4" @submit.prevent="handleLocalSubmit">
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300" for="email">Correo</label>
              <input
                id="email"
                v-model="email"
                type="email"
                required
                class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              />
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300" for="password">Contraseña</label>
              <input
                id="password"
                v-model="password"
                type="password"
                required
                class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              />
            </div>
            <button
              type="submit"
              :disabled="authStore.loading"
              class="w-full rounded-md bg-brand-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
            >
              {{ authStore.loading ? 'Ingresando…' : 'Ingresar' }}
            </button>
          </form>

          <p v-if="!authStore.config?.google_enabled && !authStore.config?.local_enabled" class="text-sm text-red-600">
            No hay ningún proveedor de autenticación habilitado. Revisa AUTH_GOOGLE_ENABLED / AUTH_LOCAL_ENABLED.
          </p>
        </template>
      </div>
    </div>
  </div>
</template>
