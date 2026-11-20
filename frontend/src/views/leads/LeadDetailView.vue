<script setup lang="ts">
import { UserSearch } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import * as campaignsApi from '@/api/campaigns'
import type { Campaign, CampaignType } from '@/api/campaigns'
import * as leadsApi from '@/api/leads'
import type { AsignableUser, Assignment, CaptureEntry, Category, Lead, ManagementLog, SubCategory } from '@/api/leads'
import type { AppNotification } from '@/api/notifications'
import * as opportunitiesApi from '@/api/opportunities'
import type { Opportunity, OpportunityPrioridad } from '@/api/opportunities'
import DynamicCaptureForm from '@/components/dynamic/DynamicCaptureForm.vue'
import DynamicDetail from '@/components/dynamic/DynamicDetail.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useUserPicker } from '@/composables/useUserPicker'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const confirm = useConfirm()
const pickUser = useUserPicker()
const leadId = computed(() => Number(route.params.id))
const canAssign = computed(() => authStore.roleName !== 'EJECUTIVO')

const lead = ref<Lead | null>(null)
const campaign = ref<Campaign | null>(null)
const campaignType = ref<CampaignType | null>(null)
const custodia = ref<Assignment[]>([])
const evolucion = ref<ManagementLog[]>([])
const capturas = ref<CaptureEntry[]>([])
const opportunity = ref<Opportunity | null>(null)
const asignables = ref<AsignableUser[]>([])
const categories = ref<Category[]>([])
const subcategories = ref<SubCategory[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)
const reassignError = ref<string | null>(null)

const gestionForm = ref({
  category: null as number | null,
  subcategory: null as number | null,
  comentario: '',
  fecha_proximo_contacto: '',
})
const capturaForm = ref<Record<string, any>>({})
const gestionError = ref<string | null>(null)
const gestionMessage = ref<string | null>(null)
const gestionSubmitting = ref(false)
const prioridadError = ref<string | null>(null)

const subcategoriasDisponibles = computed(() =>
  subcategories.value.filter((s) => s.category === gestionForm.value.category && s.activo),
)
const subcategoriaSeleccionada = computed(() =>
  subcategories.value.find((s) => s.id === gestionForm.value.subcategory),
)
const tieneCamposCaptura = computed(() =>
  (campaignType.value?.field_definitions ?? []).some((f) => f.origen === 'CAPTURA_GESTION'),
)

async function loadAll() {
  loading.value = true
  loadError.value = null
  reassignError.value = null
  try {
    lead.value = await leadsApi.fetchLead(leadId.value)
    campaign.value = await campaignsApi.fetchCampaign(lead.value.campaign)
    const [typeRes, custodiaRes, evolucionRes, capturasRes, oportunidadRes, asignablesRes, categoriesRes, subcategoriesRes] =
      await Promise.all([
        campaignsApi.fetchCampaignType(campaign.value.campaign_type),
        leadsApi.fetchCustodia(leadId.value),
        leadsApi.fetchEvolucion(leadId.value),
        leadsApi.fetchCapturas(leadId.value),
        leadsApi.fetchLeadOportunidad(leadId.value),
        leadsApi.fetchUsuariosAsignables(),
        leadsApi.fetchCategories(),
        leadsApi.fetchSubCategories(),
      ])
    campaignType.value = typeRes
    custodia.value = custodiaRes
    evolucion.value = evolucionRes
    capturas.value = capturasRes
    opportunity.value = oportunidadRes
    asignables.value = asignablesRes.results
    categories.value = categoriesRes.results.filter((c) => c.activo)
    subcategories.value = subcategoriesRes.results
    capturaForm.value = { ...lead.value.atributos_captura }
  } catch (err: any) {
    loadError.value = err?.response?.data?.detail ?? 'No se pudo cargar el lead.'
  } finally {
    loading.value = false
  }
}

async function handleReassign() {
  const destino = await pickUser(asignables.value, 'Reasignar a…')
  if (!destino) return
  const ok = await confirm({
    title: '¿Reasignar este registro?',
    message: `Se le va a asignar a ${destino.email}.`,
  })
  if (!ok) return
  reassignError.value = null
  try {
    await leadsApi.asignarLead(leadId.value, destino.id)
    await loadAll()
  } catch (err: any) {
    reassignError.value = err?.response?.data?.detail ?? 'No se pudo reasignar.'
  }
}

async function handleGestionar() {
  if (!gestionForm.value.category || !gestionForm.value.comentario.trim()) return
  const ok = await confirm({ title: '¿Guardar esta gestión?', message: 'Quedará registrada en el historial del lead.' })
  if (!ok) return
  gestionError.value = null
  gestionMessage.value = null
  gestionSubmitting.value = true
  try {
    const result = await leadsApi.gestionarLead(leadId.value, {
      category: gestionForm.value.category,
      subcategory: gestionForm.value.subcategory,
      comentario: gestionForm.value.comentario,
      fecha_proximo_contacto: gestionForm.value.fecha_proximo_contacto
        ? new Date(gestionForm.value.fecha_proximo_contacto).toISOString()
        : null,
      datos_captura: capturaForm.value,
    })
    gestionForm.value = { category: null, subcategory: null, comentario: '', fecha_proximo_contacto: '' }
    gestionMessage.value = result.opportunity ? 'Gestión guardada — la oportunidad se actualizó.' : 'Gestión guardada.'
    await loadAll()
  } catch (err: any) {
    if (err?.response?.status === 409) {
      gestionError.value = `${err.response.data.detail} Ahora es de: ${err.response.data.usuario_asignado_email ?? '—'}.`
      await loadAll()
    } else if (err?.response?.data?.datos_captura) {
      gestionError.value = 'Datos de captura inválidos: ' + JSON.stringify(err.response.data.datos_captura)
    } else {
      gestionError.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar la gestión.')
    }
  } finally {
    gestionSubmitting.value = false
  }
}

async function handlePrioridadChange(prioridad: OpportunityPrioridad) {
  if (!opportunity.value) return
  prioridadError.value = null
  try {
    opportunity.value = await opportunitiesApi.setOpportunityPrioridad(opportunity.value.id, prioridad)
  } catch (err: any) {
    prioridadError.value = err?.response?.data?.detail ?? 'No se pudo actualizar la prioridad.'
  }
}

function estadoClasses(estado: string) {
  if (estado === 'GANADA') return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
  if (estado === 'PERDIDA') return 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300'
  return 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
}

function onLiveNotification(event: Event) {
  const notification = (event as CustomEvent<AppNotification>).detail
  if (
    (notification.tipo === 'OPORTUNIDAD_CREADA' || notification.tipo === 'OPORTUNIDAD_CERRADA') &&
    notification.payload.lead_id === leadId.value
  ) {
    loadAll()
  }
}

onMounted(() => {
  loadAll()
  window.addEventListener('nexo:notification', onLiveNotification)
})
onUnmounted(() => {
  window.removeEventListener('nexo:notification', onLiveNotification)
})
</script>

<template>
  <div v-if="lead" class="space-y-8">
    <div class="flex items-center justify-between">
      <div>
        <button class="mb-1 text-xs text-slate-400 hover:underline" @click="router.back()">← Volver</button>
        <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">{{ lead.cliente_nombre || lead.documento_identidad }}</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ lead.campaign_nombre }}</p>
      </div>
      <div v-if="canAssign" class="flex items-center gap-2">
        <button
          class="flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-sm text-white dark:bg-slate-100 dark:text-slate-900"
          @click="handleReassign"
        >
          <UserSearch :size="16" /> Reasignar
        </button>
      </div>
    </div>
    <p v-if="reassignError" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
      {{ reassignError }}
    </p>

    <div class="grid gap-8 lg:grid-cols-3">
      <div class="space-y-8 lg:col-span-2">
        <DynamicDetail
          v-if="campaignType"
          :field-definitions="campaignType.field_definitions"
          :sections="campaignType.secciones"
          :lead="lead"
        />

        <section class="card p-4">
          <h3 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Gestionar</h3>
          <p v-if="campaign?.esta_cerrada" class="mb-3 rounded-md bg-slate-100 px-3 py-2 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            Esta campaña está cerrada — ya no se pueden registrar gestiones nuevas.
          </p>
          <fieldset v-else class="space-y-3" :disabled="gestionSubmitting">
          <form class="space-y-3" @submit.prevent="handleGestionar">
            <div class="flex flex-wrap gap-3">
              <select
                v-model="gestionForm.category"
                required
                class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                @change="gestionForm.subcategory = null"
              >
                <option :value="null" disabled>Categoría…</option>
                <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.nombre }}</option>
              </select>
              <select
                v-if="subcategoriasDisponibles.length"
                v-model="gestionForm.subcategory"
                class="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
              >
                <option :value="null">Sin subcategoría</option>
                <option v-for="s in subcategoriasDisponibles" :key="s.id" :value="s.id">{{ s.nombre }}</option>
              </select>
              <div v-if="subcategoriaSeleccionada?.requiere_proximo_contacto" class="flex-1">
                <input
                  v-model="gestionForm.fecha_proximo_contacto"
                  type="datetime-local"
                  required
                  class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
                />
              </div>
            </div>

            <div v-if="tieneCamposCaptura && campaignType" class="rounded-md border border-slate-200 p-3 dark:border-slate-800">
              <DynamicCaptureForm
                v-model="capturaForm"
                :field-definitions="campaignType.field_definitions"
                :sections="campaignType.secciones"
              />
            </div>

            <textarea
              v-model="gestionForm.comentario"
              required
              rows="3"
              placeholder="Comentario de gestión…"
              class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
            />
            <button
              type="submit"
              :disabled="gestionSubmitting"
              class="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900"
            >
              {{ gestionSubmitting ? 'Guardando…' : 'Guardar gestión' }}
            </button>
            <p v-if="gestionMessage" class="text-xs text-emerald-600">{{ gestionMessage }}</p>
            <p v-if="gestionError" class="rounded-md bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-300">
              {{ gestionError }}
            </p>
          </form>
          </fieldset>
        </section>

        <section class="card p-4">
          <h3 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Evolución del lead</h3>
          <ol class="space-y-3 border-l border-slate-200 pl-4 text-xs dark:border-slate-800">
            <li v-for="item in evolucion" :key="item.id">
              <p class="text-slate-700 dark:text-slate-300">
                <span class="font-medium">{{ item.category_nombre }}</span>
                <span v-if="item.subcategory_nombre"> · {{ item.subcategory_nombre }}</span>
              </p>
              <p class="text-slate-600 dark:text-slate-400">{{ item.comentario }}</p>
              <p v-if="item.fecha_proximo_contacto" class="text-slate-500">
                Próximo contacto: {{ new Date(item.fecha_proximo_contacto).toLocaleString('es-PE') }}
              </p>
              <p class="text-slate-400">{{ item.usuario_email }} · {{ new Date(item.timestamp).toLocaleString('es-PE') }}</p>
            </li>
            <li v-if="evolucion.length === 0" class="text-slate-400">Sin gestiones todavía.</li>
          </ol>
        </section>

        <section v-if="capturas.length" class="card p-4">
          <h3 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Historial de captura</h3>
          <ol class="space-y-3 border-l border-slate-200 pl-4 text-xs dark:border-slate-800">
            <li v-for="item in capturas" :key="item.id">
              <p class="text-slate-700 dark:text-slate-300">
                <span v-for="(value, key) in item.datos" :key="key">{{ key }}: {{ value }} · </span>
              </p>
              <p class="text-slate-400">{{ item.usuario_email }} · {{ new Date(item.timestamp).toLocaleString('es-PE') }}</p>
            </li>
          </ol>
        </section>
      </div>

      <aside class="space-y-8">
        <section v-if="opportunity">
          <h3 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Oportunidad</h3>
          <div class="card p-3 text-xs">
            <span class="rounded-full px-2 py-0.5" :class="estadoClasses(opportunity.estado)">{{ opportunity.estado }}</span>
            <p class="mt-2 text-slate-500">Responsable: {{ opportunity.usuario_responsable_email }}</p>
            <p v-if="opportunity.fecha_proximo_contacto" class="text-slate-500">
              Próximo contacto: {{ new Date(opportunity.fecha_proximo_contacto).toLocaleString('es-PE') }}
            </p>
            <div class="mt-2 flex items-center gap-2">
              <span class="text-slate-500">Prioridad:</span>
              <select
                :value="opportunity.prioridad"
                class="rounded-md border border-slate-300 px-2 py-1 text-xs dark:border-slate-700 dark:bg-slate-900"
                @change="handlePrioridadChange(($event.target as HTMLSelectElement).value as any)"
              >
                <option value="ALTA">Alta</option>
                <option value="MEDIA">Media</option>
                <option value="BAJA">Baja</option>
              </select>
            </div>
            <p v-if="prioridadError" class="mt-1 text-red-600">{{ prioridadError }}</p>
          </div>
        </section>

        <section class="card p-4">
          <h3 class="mb-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Cadena de custodia</h3>
          <ol class="space-y-3 border-l border-slate-200 pl-4 text-xs dark:border-slate-800">
            <li v-for="item in custodia" :key="item.id">
              <p class="text-slate-700 dark:text-slate-300">
                <span class="font-medium">{{ item.usuario_origen_email ?? 'Sin asignar' }}</span>
                →
                <span class="font-medium">{{ item.usuario_destino_email }}</span>
              </p>
              <p v-if="item.agencia_destino_nombre" class="text-slate-400">
                Cambió de agencia: {{ item.agencia_origen_nombre }} → {{ item.agencia_destino_nombre }}
              </p>
              <p class="text-slate-400">por {{ item.asignado_por_email }} · {{ new Date(item.timestamp).toLocaleString('es-PE') }}</p>
            </li>
            <li v-if="custodia.length === 0" class="text-slate-400">Sin historial de asignaciones.</li>
          </ol>
        </section>
      </aside>
    </div>
  </div>
  <p v-else-if="loading" class="text-sm text-slate-400">Cargando…</p>
  <p v-else-if="loadError" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
    {{ loadError }}
  </p>
</template>
