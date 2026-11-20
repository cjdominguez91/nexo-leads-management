<script setup lang="ts">
import { computed } from 'vue'

import type { CampaignFieldDefinition, CampaignFieldOrigen, CampaignSection } from '@/api/campaigns'

const props = withDefaults(
  defineProps<{
    fieldDefinitions: CampaignFieldDefinition[]
    sections: CampaignSection[]
    modelValue: Record<string, any>
    origen?: CampaignFieldOrigen
    hint?: string | null
  }>(),
  { origen: 'CAPTURA_GESTION', hint: 'Deja todo en blanco si no lograste contactar al cliente o no había nada que actualizar.' },
)

const emit = defineEmits<{ 'update:modelValue': [Record<string, any>] }>()

const groups = computed(() => {
  const capturaFields = props.fieldDefinitions.filter((f) => f.origen === props.origen)
  const sectionsById = new Map(props.sections.map((s) => [s.id, s]))
  const grouped = new Map<number, CampaignFieldDefinition[]>()
  for (const field of capturaFields) {
    if (!grouped.has(field.seccion)) grouped.set(field.seccion, [])
    grouped.get(field.seccion)!.push(field)
  }
  return [...grouped.entries()]
    .map(([seccionId, fields]) => ({
      nombre: sectionsById.get(seccionId)?.nombre ?? 'Otros datos',
      orden: sectionsById.get(seccionId)?.orden ?? 999,
      fields: fields.sort((a, b) => a.orden - b.orden),
    }))
    .sort((a, b) => a.orden - b.orden)
})

function setValue(key: string, value: unknown) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}
</script>

<template>
  <div v-if="groups.length" class="space-y-4">
    <div v-for="group in groups" :key="group.nombre">
      <h4 class="mb-2 text-xs font-semibold uppercase text-slate-400">{{ group.nombre }}</h4>
      <div class="grid grid-cols-2 gap-3">
        <div v-for="field in group.fields" :key="field.field_key">
          <label class="mb-1 block text-xs text-slate-500">{{ field.label }}</label>

          <select
            v-if="field.data_type === 'SELECT'"
            :value="modelValue[field.field_key] ?? ''"
            class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            @change="setValue(field.field_key, ($event.target as HTMLSelectElement).value)"
          >
            <option value="">—</option>
            <option v-for="opt in field.options ?? []" :key="opt" :value="opt">{{ opt }}</option>
          </select>

          <select
            v-else-if="field.data_type === 'MULTISELECT'"
            multiple
            :value="modelValue[field.field_key] ?? []"
            class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            @change="
              setValue(
                field.field_key,
                Array.from(($event.target as HTMLSelectElement).selectedOptions).map((o) => o.value),
              )
            "
          >
            <option v-for="opt in field.options ?? []" :key="opt" :value="opt">{{ opt }}</option>
          </select>

          <select
            v-else-if="field.data_type === 'BOOLEANO'"
            :value="modelValue[field.field_key] ?? ''"
            class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            @change="setValue(field.field_key, ($event.target as HTMLSelectElement).value)"
          >
            <option value="">—</option>
            <option value="true">Sí</option>
            <option value="false">No</option>
          </select>

          <input
            v-else
            :type="field.data_type === 'FECHA' ? 'date' : field.data_type === 'NUMERO' ? 'number' : 'text'"
            :value="modelValue[field.field_key] ?? ''"
            class="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            @input="setValue(field.field_key, ($event.target as HTMLInputElement).value)"
          />
        </div>
      </div>
    </div>
    <p v-if="hint" class="text-xs text-slate-400">{{ hint }}</p>
  </div>
</template>
