<script setup lang="ts">
/**
 * Botón de acción para filas de tabla (Editar, Alcance, Desactivar…).
 * El color comunica la intención y el ícono la refuerza, para que las
 * acciones no se lean como una fila de links grises iguales:
 *   edit    → azul     (modificar datos)
 *   scope   → violeta  (permisos / alcance territorial)
 *   danger  → rojo     (desactivar / quitar)
 *   success → verde    (activar / confirmar)
 *   neutral → gris     (acciones secundarias)
 */
import { Check, MapPin, Pencil, Power, Settings2, Trash2, UserCheck, UserX, X } from '@lucide/vue'
import { computed } from 'vue'

type Variant = 'edit' | 'scope' | 'danger' | 'success' | 'neutral'
type IconName = 'edit' | 'scope' | 'deactivate' | 'activate' | 'power' | 'delete' | 'settings' | 'save' | 'cancel'

const props = withDefaults(
  defineProps<{
    variant?: Variant
    icon?: IconName
    label: string
    disabled?: boolean
    /** Solo ícono (el label queda como tooltip/aria-label). */
    iconOnly?: boolean
  }>(),
  { variant: 'neutral', icon: undefined, disabled: false, iconOnly: false },
)

const ICONS = {
  edit: Pencil,
  scope: MapPin,
  deactivate: UserX,
  activate: UserCheck,
  power: Power,
  delete: Trash2,
  settings: Settings2,
  save: Check,
  cancel: X,
}

const VARIANT_CLASSES: Record<Variant, string> = {
  edit: 'text-primary-600 bg-primary-50 hover:bg-primary-100 dark:text-primary-500 dark:bg-primary-600/15 dark:hover:bg-primary-600/25',
  scope: 'text-violet-600 bg-violet-50 hover:bg-violet-100 dark:text-violet-300 dark:bg-violet-500/15 dark:hover:bg-violet-500/25',
  danger: 'text-red-600 bg-red-50 hover:bg-red-100 dark:text-red-400 dark:bg-red-500/15 dark:hover:bg-red-500/25',
  success: 'text-emerald-700 bg-emerald-50 hover:bg-emerald-100 dark:text-emerald-400 dark:bg-emerald-500/15 dark:hover:bg-emerald-500/25',
  neutral: 'text-slate-600 bg-slate-100 hover:bg-slate-200 dark:text-slate-300 dark:bg-slate-700/50 dark:hover:bg-slate-700',
}

const iconComponent = computed(() => (props.icon ? ICONS[props.icon] : null))
</script>

<template>
  <button
    type="button"
    class="inline-flex items-center gap-1 rounded-md text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50"
    :class="[VARIANT_CLASSES[variant], iconOnly ? 'p-1.5' : 'px-2 py-1']"
    :disabled="disabled"
    :title="label"
    :aria-label="label"
  >
    <component :is="iconComponent" v-if="iconComponent" :size="13" class="shrink-0" />
    <span v-if="!iconOnly">{{ label }}</span>
  </button>
</template>
