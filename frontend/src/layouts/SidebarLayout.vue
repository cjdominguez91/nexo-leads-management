<script setup lang="ts">
import {
  Bell,
  Building2,
  ClipboardList,
  Handshake,
  LayoutDashboard,
  Layers,
  LogOut,
  Megaphone,
  Menu,
  Moon,
  ShieldCheck,
  Sun,
  Tags,
  UserSearch,
  Users,
  Waypoints,
} from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import type { AppNotification } from '@/api/notifications'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import UserSearchModal from '@/components/UserSearchModal.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { useThemeStore } from '@/stores/theme'

interface NavItem {
  label: string
  to: string
  icon: typeof Megaphone
  roles?: string[]
}

interface NavSection {
  label: string
  items: NavItem[]
}

const authStore = useAuthStore()
const notifStore = useNotificationsStore()
const themeStore = useThemeStore()
const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const showNotifications = ref(false)

const navSections: NavSection[] = [
  {
    label: 'Principal',
    items: [
      { label: 'Dashboard', to: '/', icon: LayoutDashboard },
      { label: 'Campañas', to: '/campanas', icon: Megaphone },
      { label: 'Prospección', to: '/prospecciones', icon: UserSearch },
      { label: 'Oportunidades', to: '/oportunidades', icon: Handshake },
    ],
  },
  {
    label: 'Administración',
    items: [
      { label: 'Usuarios', to: '/admin/usuarios', icon: Users, roles: ['ADMIN', 'ADMIN_DIVISION'] },
      { label: 'Agencias', to: '/admin/agencias', icon: Building2, roles: ['ADMIN', 'ADMIN_DIVISION'] },
      { label: 'Divisiones', to: '/admin/divisiones', icon: Layers, roles: ['ADMIN'] },
      { label: 'Tipos de campaña', to: '/admin/tipos-campana', icon: ClipboardList, roles: ['ADMIN', 'ADMIN_DIVISION'] },
      { label: 'Catálogos', to: '/admin/catalogos', icon: Tags, roles: ['ADMIN', 'ADMIN_DIVISION'] },
    ],
  },
]

const ROLE_LABEL: Record<string, string> = {
  ADMIN: 'Administrador',
  ADMIN_DIVISION: 'Admin de división',
  GERENTE: 'Gerente',
  SUPERVISOR: 'Supervisor',
  JEFE: 'Jefe de agencia',
  SUBJEFE: 'Subjefe de agencia',
  EJECUTIVO: 'Ejecutivo',
}
const roleLabel = computed(() =>
  authStore.user?.is_superuser && !authStore.roleName ? 'Superusuario' : ROLE_LABEL[authStore.roleName ?? ''] ?? '',
)

// La etiqueta de división no aplica a quien cruza divisiones (ADMIN global/superusuario).
const divisionLabel = computed(() => (authStore.isGlobalAdmin ? null : authStore.user?.division_nombre ?? null))

const visibleSections = computed(() =>
  navSections
    .map((section) => ({
      ...section,
      items: section.items.filter(
        (item) => !item.roles || authStore.user?.is_superuser || (authStore.roleName && item.roles.includes(authStore.roleName)),
      ),
    }))
    .filter((section) => section.items.length > 0),
)

function isActive(to: string) {
  if (to === '/') return route.path === '/'
  if (to === '/campanas') return route.path === '/campanas' || route.path.startsWith('/campanas/') || route.path.startsWith('/leads/')
  return route.path.startsWith(to)
}

async function handleLogout() {
  notifStore.disconnect()
  await authStore.logout()
  await router.push({ name: 'login' })
}

function notificationMessage(n: AppNotification): string {
  if (n.tipo === 'ASIGNACION_RECIBIDA') {
    const { cantidad, campaign_nombre } = n.payload
    const plural = cantidad !== 1
    return `${cantidad} registro${plural ? 's' : ''} de la campaña "${campaign_nombre}" te ${plural ? 'han' : 'ha'} sido asignado${plural ? 's' : ''}.`
  }
  const { cliente_nombre, campaign_nombre, estado } = n.payload
  if (n.tipo === 'OPORTUNIDAD_CREADA') {
    return `Se abrió una oportunidad para ${cliente_nombre} (${campaign_nombre}).`
  }
  const resultado = estado === 'GANADA' ? 'ganada' : 'perdida'
  return `Tu oportunidad de ${cliente_nombre} (${campaign_nombre}) quedó ${resultado}.`
}

function formatFecha(value: string) {
  return new Date(value).toLocaleString('es-PE')
}

async function goToNotification(n: AppNotification) {
  await notifStore.marcarLeida(n.id)
  showNotifications.value = false
  if (n.tipo === 'ASIGNACION_RECIBIDA') {
    const routeName = n.payload.campaign_modo_carga === 'INDIVIDUAL' ? 'prospeccion-detail' : 'campaign-detail'
    router.push({ name: routeName, params: { id: n.payload.campaign_id } })
    return
  }
  router.push({ name: 'lead-detail', params: { id: n.payload.lead_id } })
}

function toggleNotifications() {
  showNotifications.value = !showNotifications.value
}

onMounted(() => {
  if (authStore.accessToken) {
    notifStore.connect(authStore.accessToken)
    notifStore.loadHistory()
  }
})

onUnmounted(() => {
  notifStore.disconnect()
})
</script>

<template>
  <div class="flex h-full bg-surface-bg">
    <aside
      class="flex flex-col bg-surface-sidebar transition-all duration-200"
      :class="collapsed ? 'w-16' : 'w-64'"
    >
      <div class="flex h-14 shrink-0 items-center justify-between px-3">
        <div v-if="!collapsed" class="flex items-center gap-2">
          <Waypoints :size="22" class="shrink-0 text-accent-400" />
          <span class="text-base font-bold tracking-wide text-white">NEXO</span>
        </div>
        <Waypoints v-else :size="22" class="mx-auto text-accent-400" />
        <button
          v-if="!collapsed"
          class="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
          @click="collapsed = !collapsed"
        >
          <Menu :size="18" />
        </button>
      </div>
      <button
        v-if="collapsed"
        class="mx-auto mb-1 rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
        @click="collapsed = !collapsed"
      >
        <Menu :size="18" />
      </button>

      <div v-if="divisionLabel" class="px-3 pb-1">
        <div
          v-if="!collapsed"
          class="flex items-center gap-2 rounded-md border border-accent-500/30 bg-accent-500/10 px-2.5 py-1.5"
          :title="`División: ${divisionLabel}`"
        >
          <Layers :size="14" class="shrink-0 text-accent-400" />
          <div class="min-w-0">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-accent-300/80">División</p>
            <p class="truncate text-xs font-medium text-accent-100">{{ divisionLabel }}</p>
          </div>
        </div>
        <div v-else class="flex justify-center" :title="`División: ${divisionLabel}`">
          <span class="flex h-8 w-8 items-center justify-center rounded-md bg-accent-500/15 text-xs font-bold text-accent-300">
            {{ divisionLabel.slice(0, 2).toUpperCase() }}
          </span>
        </div>
      </div>

      <nav class="flex-1 space-y-5 overflow-y-auto px-2 py-3">
        <div v-for="section in visibleSections" :key="section.label">
          <p v-if="!collapsed" class="mb-1.5 px-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            {{ section.label }}
          </p>
          <div class="space-y-0.5">
            <router-link
              v-for="item in section.items"
              :key="item.to"
              :to="item.to"
              :title="collapsed ? item.label : undefined"
              class="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
              :class="[isActive(item.to) ? '!bg-brand-600 !text-white' : '', collapsed ? 'justify-center' : '']"
            >
              <component :is="item.icon" :size="18" class="shrink-0" />
              <span v-if="!collapsed">{{ item.label }}</span>
            </router-link>
          </div>
        </div>
      </nav>
    </aside>

    <div class="flex flex-1 flex-col overflow-hidden">
      <header class="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-surface-navbar px-4 dark:border-slate-800">
        <span class="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700 dark:bg-brand-950 dark:text-brand-300">
          <ShieldCheck :size="13" />
          {{ roleLabel }}
        </span>
        <div class="flex items-center gap-2">
          <button
            class="rounded-md p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
            :title="themeStore.isDark ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'"
            @click="themeStore.toggle"
          >
            <Sun v-if="themeStore.isDark" :size="18" />
            <Moon v-else :size="18" />
          </button>

          <div class="relative">
            <button
              class="relative rounded-md p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              @click="toggleNotifications"
            >
              <Bell :size="18" />
              <span
                v-if="notifStore.unreadCount > 0"
                class="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-medium text-white"
              >
                {{ notifStore.unreadCount }}
              </span>
            </button>

            <div
              v-if="showNotifications"
              class="card absolute right-0 z-20 mt-2 w-80 shadow-lg"
            >
              <div class="flex items-center justify-between border-b border-slate-100 px-3 py-2 dark:border-slate-800">
                <span class="text-xs font-semibold text-slate-500">Notificaciones</span>
                <button
                  v-if="notifStore.unreadCount > 0"
                  class="text-xs text-brand-600 underline hover:text-brand-800 dark:text-brand-400 dark:hover:text-brand-300"
                  @click="notifStore.marcarTodasLeidas"
                >
                  Marcar todas como leídas
                </button>
              </div>
              <div class="max-h-96 overflow-y-auto">
                <button
                  v-for="n in notifStore.items"
                  :key="n.id"
                  class="block w-full border-b border-slate-100 px-3 py-2 text-left text-xs last:border-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800"
                  :class="!n.leido ? 'bg-brand-50/60 dark:bg-slate-800/60' : ''"
                  @click="goToNotification(n)"
                >
                  <p class="text-slate-700 dark:text-slate-300">{{ notificationMessage(n) }}</p>
                  <p class="mt-1 text-slate-400">{{ formatFecha(n.created_at) }}</p>
                </button>
                <p v-if="notifStore.items.length === 0" class="px-3 py-4 text-center text-xs text-slate-400">
                  Sin notificaciones todavía.
                </p>
              </div>
            </div>
          </div>

          <div class="mx-1 h-6 w-px bg-slate-200 dark:bg-slate-800" />

          <div class="flex items-center gap-2">
            <div class="flex h-8 w-8 items-center justify-center rounded-full bg-brand-600 text-sm font-semibold text-white">
              {{ authStore.user?.email?.slice(0, 1).toUpperCase() }}
            </div>
            <span class="hidden text-sm text-slate-700 dark:text-slate-300 sm:inline">{{ authStore.user?.email }}</span>
          </div>
          <button
            class="flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
            @click="handleLogout"
          >
            <LogOut :size="15" />
            Salir
          </button>
        </div>
      </header>

      <main class="flex-1 overflow-auto p-6">
        <router-view />
      </main>
    </div>

    <div class="fixed bottom-4 right-4 z-30 flex w-80 flex-col gap-2">
      <div
        v-for="toast in notifStore.toasts"
        :key="toast.id"
        class="card cursor-pointer p-3 text-sm shadow-lg"
        @click="goToNotification(toast)"
      >
        <div class="flex items-start justify-between gap-2">
          <p class="text-slate-700 dark:text-slate-300">{{ notificationMessage(toast) }}</p>
          <button class="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200" @click.stop="notifStore.dismissToast(toast.id)">
            ×
          </button>
        </div>
      </div>
    </div>

    <ConfirmDialog />
    <UserSearchModal />
  </div>
</template>
