<script setup lang="ts">
import { computed } from 'vue'

import type { CampaignFieldDefinition, CampaignSection } from '@/api/campaigns'
import type { Lead } from '@/api/leads'
import { formatFieldValue } from '@/composables/useFieldFormatter'

const props = defineProps<{
  fieldDefinitions: CampaignFieldDefinition[]
  sections: CampaignSection[]
  lead: Lead
}>()

const nombreField = computed(() => props.fieldDefinitions.find((f) => f.es_nombre_cliente))
const telefonoField = computed(() => props.fieldDefinitions.find((f) => f.es_telefono_contacto))
const documentoField = computed(() => props.fieldDefinitions.find((f) => f.es_documento_identidad))

const sections = computed(() => {
  const visibles = [...props.fieldDefinitions].filter(
    (f) =>
      f.origen === 'CARGA' &&
      f.mostrar_en_detalle &&
      !f.es_nombre_cliente &&
      !f.es_telefono_contacto &&
      !f.es_documento_identidad,
  )
  const sectionsById = new Map(props.sections.map((s) => [s.id, s]))
  const grouped = new Map<number, CampaignFieldDefinition[]>()
  for (const field of visibles) {
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
</script>

<template>
  <div class="card space-y-6 p-4">
    <section>
      <h3 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Datos del cliente</h3>
      <dl class="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <div>
          <dt class="text-slate-400">{{ documentoField?.label ?? 'Documento' }}</dt>
          <dd class="font-medium text-slate-800 dark:text-slate-200">{{ lead.documento_identidad }}</dd>
        </div>
        <div>
          <dt class="text-slate-400">{{ nombreField?.label ?? 'Nombre' }}</dt>
          <dd class="text-slate-800 dark:text-slate-200">{{ lead.cliente_nombre || lead.documento_identidad }}</dd>
        </div>
        <div>
          <dt class="text-slate-400">{{ telefonoField?.label ?? 'Teléfono' }}</dt>
          <dd class="text-slate-800 dark:text-slate-200">{{ lead.telefono || '—' }}</dd>
        </div>
        <div><dt class="text-slate-400">Agencia</dt><dd class="text-slate-800 dark:text-slate-200">{{ lead.agencia_nombre }}</dd></div>
        <div><dt class="text-slate-400">Estado</dt><dd class="text-slate-800 dark:text-slate-200">{{ lead.estado }}</dd></div>
        <div><dt class="text-slate-400">Asignado a</dt><dd class="text-slate-800 dark:text-slate-200">{{ lead.usuario_asignado_email ?? '—' }}</dd></div>
      </dl>
    </section>

    <section v-for="group in sections" :key="group.nombre">
      <h3 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">{{ group.nombre }}</h3>
      <dl class="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <div v-for="field in group.fields" :key="field.field_key">
          <dt class="text-slate-400">{{ field.label }}</dt>
          <dd class="text-slate-800 dark:text-slate-200">
            {{ formatFieldValue(lead.atributos[field.field_key], field.data_type) }}
          </dd>
        </div>
      </dl>
    </section>
  </div>
</template>
