<script setup lang="ts">
import { UserSearch } from '@lucide/vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import * as campaignsApi from '@/api/campaigns'
import type { Campaign, CampaignType, LoteCarga } from '@/api/campaigns'
import * as geoApi from '@/api/geo'
import type { Agencia, Territorio } from '@/api/geo'
import * as leadsApi from '@/api/leads'
import type { AsignableUser, Lead } from '@/api/leads'
import type { AppNotification } from '@/api/notifications'
import DynamicCaptureForm from '@/components/dynamic/DynamicCaptureForm.vue'
import DynamicTable from '@/components/dynamic/DynamicTable.vue'
import MultiSelectPicker from '@/components/MultiSelectPicker.vue'
import TablePagination from '@/components/TablePagination.vue'
import { useConfirm } from '@/composables/useConfirm'
import { useUserPicker } from '@/composables/useUserPicker'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const confirm = useConfirm()
const pickUser = useUserPicker()
const campaignId = computed(() => Number(route.params.id))
const rol = computed(() => authStore.roleName)
const canUpload = computed(
  () => authStore.isAdminRole && !campaign.value?.esta_cerrada && campaignType.value?.modo_carga !== 'INDIVIDUAL',
)
const canAssign = computed(() => authStore.roleName !== 'EJECUTIVO')
const isAdmin = computed(() => authStore.isAdminRole)
const esProspeccion = computed(() => campaignType.value?.modo_carga === 'INDIVIDUAL')
const esEjecutivo = computed(() => rol.value === 'EJECUTIVO')
const canCreateProspecto = computed(() => esProspeccion.value && !campaign.value?.esta_cerrada)
const agenciaOptions = computed(() => agencias.value.map((a) => ({ id: a.id, label: a.nombre })))
const territorioOptions = computed(() => territorios.value.map((t) => ({ id: t.id, label: t.nombre })))

// agencia_codigo es una columna reservada del parser (apps.leads.tasks),
// no un CampaignFieldDefinition — solo aplica si el lote no fija una sola
// agencia para todo el archivo (ver texto de ayuda en la sección de carga).
const columnasArchivo = computed(() => {
  if (!campaignType.value) return []
  const campos = [...campaignType.value.field_definitions]
    .filter((f) => f.origen === 'CARGA')
    .sort((a, b) => a.orden - b.orden)
    .map((f) => ({ key: f.field_key, label: f.label, required: f.required }))
  if (!restrictionForm.value.agencia_restriccion) {
    campos.push({ key: 'agencia_codigo', label: 'Código de agencia', required: true })
  }
  return campos
})

function handleDescargarPlantilla() {
  const headers = columnasArchivo.value.map((c) => c.key)
  const csv = headers.join(',') + '\n'
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `plantilla_${(campaign.value?.nombre ?? 'campana').replace(/\s+/g, '_')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

const agenciasSeleccionables = computed(() => {
  if (rol.value === 'JEFE' || rol.value === 'SUBJEFE') {
    const misAgenciaIds = new Set(
      (authStore.user?.agencias ?? []).filter((a) => a.activo).map((a) => a.agencia),
    )
    return agencias.value.filter((a) => misAgenciaIds.has(a.id))
  }
  if (rol.value === 'SUPERVISOR') {
    return prospectoDistrito.value ? agencias.value.filter((a) => a.territorio === prospectoDistrito.value) : []
  }
  return prospectoDistrito.value ? agencias.value.filter((a) => a.territorio === prospectoDistrito.value) : agencias.value
})

const territoriosSeleccionables = computed(() => {
  if (rol.value === 'SUPERVISOR') {
    const misTerritorioIds = new Set(
      (authStore.user?.territorios ?? []).filter((t) => t.activo).map((t) => t.territorio),
    )
    return territorios.value.filter((t) => misTerritorioIds.has(t.id))
  }
  return territorios.value
})

const campaign = ref<Campaign | null>(null)
const campaignType = ref<CampaignType | null>(null)
const lotes = ref<LoteCarga[]>([])
const leads = ref<Lead[]>([])
const leadsCount = ref(0)
const leadsColumnFilters = ref<Record<string, string>>({})
const leadsOrdering = ref('')
const leadsPage = ref(1)
const leadsPageSize = 25
const asignables = ref<AsignableUser[]>([])
const agencias = ref<Agencia[]>([])
const territorios = ref<Territorio[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)
const uploading = ref(false)
const uploadError = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const restrictionForm = ref({ agencia_restriccion: null as number | null, distrito_restriccion: null as number | null })

const editingCampaign = ref(false)
const campaignEdit = ref({
  nombre: '',
  fecha_inicio: '',
  fecha_fin: '' as string | null,
  estado: 'ACTIVA' as 'ACTIVA' | 'CERRADA',
  producto_default: '',
  agencias_habilitadas: [] as number[],
  distritos_habilitados: [] as number[],
})
const campaignEditError = ref<string | null>(null)
const deleteError = ref<string | null>(null)

const selectedLeadIds = ref<number[]>([])
const bulkMessage = ref<string | null>(null)

const prospectoDistrito = ref<number | null>(null)
const prospectoAgencia = ref<number | null>(null)
const prospectoForm = ref<Record<string, any>>({})
const prospectoSubmitting = ref(false)
const prospectoError = ref<string | null>(null)
const prospectoMessage = ref<string | null>(null)

let pollHandle: ReturnType<typeof setInterval> | null = null

function leadsParams() {
  return {
    ordering: leadsOrdering.value || undefined,
    page: leadsPage.value,
    ...leadsColumnFilters.value,
  }
}

async function loadLeads() {
  const res = await leadsApi.fetchLeads(campaignId.value, leadsParams())
  leads.value = res.results
  leadsCount.value = res.count
}

function handleLeadsFilterChange(filters: Record<string, string>) {
  leadsColumnFilters.value = filters
  leadsPage.value = 1
  loadLeads()
}

function handleLeadsSort(ordering: string) {
  leadsOrdering.value = ordering
  leadsPage.value = 1
  loadLeads()
}

function handleLeadsPage(page: number) {
  leadsPage.value = page
  loadLeads()
}

async function loadAll() {
  loading.value = true
  loadError.value = null
  try {
    campaign.value = await campaignsApi.fetchCampaign(campaignId.value)
    const [typeRes, lotesRes, leadsRes, asignablesRes, agenciasRes, territoriosRes] = await Promise.all([
      campaignsApi.fetchCampaignType(campaign.value.campaign_type),
      campaignsApi.fetchLotesCarga(campaignId.value),
      leadsApi.fetchLeads(campaignId.value, leadsParams()),
      leadsApi.fetchUsuariosAsignables(),
      geoApi.fetchAgencias(),
      geoApi.fetchTerritorios(),
    ])
    campaignType.value = typeRes
    lotes.value = lotesRes.results
    leads.value = leadsRes.results
    leadsCount.value = leadsRes.count
    // Solo la división de la campaña (un ADMIN global recibe todas).
    const divisionCampana = campaign.value?.division
    asignables.value = asignablesRes.results.filter((u) => u.division === divisionCampana || u.division === null)
    agencias.value = agenciasRes.results.filter((a) => a.division === divisionCampana)
    territorios.value = territoriosRes.results.filter((t) => t.division === divisionCampana)
  } catch (err: any) {
    loadError.value = err?.response?.data?.detail ?? 'No se pudo cargar la campaña.'
  } finally {
    loading.value = false
  }
}

async function handleUpload() {
  const file = fileInput.value?.files?.[0]
  if (!file) return
  uploadError.value = null
  uploading.value = true
  try {
    await campaignsApi.uploadLoteCarga(campaignId.value, file, restrictionForm.value)
    if (fileInput.value) fileInput.value.value = ''
    await refreshLotesAndLeads()
    startPolling()
  } catch (err: any) {
    uploadError.value = JSON.stringify(err?.response?.data ?? 'No se pudo subir el archivo.')
  } finally {
    uploading.value = false
  }
}

async function refreshLotesAndLeads() {
  const [lotesRes, leadsRes] = await Promise.all([
    campaignsApi.fetchLotesCarga(campaignId.value),
    leadsApi.fetchLeads(campaignId.value, leadsParams()),
  ])
  lotes.value = lotesRes.results
  leads.value = leadsRes.results
  leadsCount.value = leadsRes.count
}

function startPolling() {
  if (pollHandle) return
  let ticks = 0
  pollHandle = setInterval(async () => {
    ticks += 1
    await refreshLotesAndLeads()
    const stillProcessing = lotes.value.some((l) => l.estado === 'PROCESANDO')
    if (!stillProcessing || ticks > 15) {
      clearInterval(pollHandle!)
      pollHandle = null
    }
  }, 2000)
}

async function handleBulkAssign() {
  if (selectedLeadIds.value.length === 0) return
  const destino = await pickUser(asignables.value, `Asignar ${selectedLeadIds.value.length} registro(s) a…`)
  if (!destino) return
  const confirmed = await confirm({
    title: `¿Asignar ${selectedLeadIds.value.length} registro(s)?`,
    message: `Se le van a asignar a ${destino.email}.`,
  })
  if (!confirmed) return
  bulkMessage.value = null
  const result: any = await leadsApi.asignarMasivo(selectedLeadIds.value, destino.id)
  const ok = result.resultados.filter((r: any) => r.ok).length
  const fail = result.resultados.length - ok
  bulkMessage.value = `${ok} asignados. ${fail > 0 ? `${fail} fallaron.` : ''}`
  selectedLeadIds.value = []
  await refreshLotesAndLeads()
}

function goToLead(lead: Lead) {
  router.push({ name: 'lead-detail', params: { id: lead.id } })
}

async function handleCrearProspecto() {
  if (!esEjecutivo.value && !prospectoAgencia.value) return
  prospectoError.value = null
  prospectoMessage.value = null
  prospectoSubmitting.value = true
  try {
    const result = await leadsApi.crearProspecto({
      campaign: campaignId.value,
      agencia: esEjecutivo.value ? undefined : prospectoAgencia.value,
      atributos: prospectoForm.value,
    })
    prospectoForm.value = {}
    prospectoMessage.value = result.reclamado
      ? 'Este cliente ya estaba prospectado hace más de un mes — se reasignó a ti.'
      : 'Prospecto registrado.'
    await refreshLotesAndLeads()
  } catch (err: any) {
    if (err?.response?.status === 409) {
      prospectoError.value = `${err.response.data.detail} Actualmente es de: ${err.response.data.usuario_asignado_email ?? '—'}.`
    } else {
      prospectoError.value = JSON.stringify(err?.response?.data ?? 'No se pudo registrar el prospecto.')
    }
  } finally {
    prospectoSubmitting.value = false
  }
}

function startEditCampaign() {
  if (!campaign.value) return
  campaignEdit.value = {
    nombre: campaign.value.nombre,
    fecha_inicio: campaign.value.fecha_inicio,
    fecha_fin: campaign.value.fecha_fin,
    estado: campaign.value.estado,
    producto_default: campaign.value.producto_default,
    agencias_habilitadas: [...campaign.value.agencias_habilitadas],
    distritos_habilitados: [...campaign.value.distritos_habilitados],
  }
  campaignEditError.value = null
  editingCampaign.value = true
}

function cancelEditCampaign() {
  editingCampaign.value = false
}

async function saveCampaign() {
  campaignEditError.value = null
  try {
    campaign.value = await campaignsApi.updateCampaign(campaignId.value, {
      ...campaignEdit.value,
      fecha_fin: campaignEdit.value.fecha_fin || null,
    })
    editingCampaign.value = false
  } catch (err: any) {
    campaignEditError.value = JSON.stringify(err?.response?.data ?? 'No se pudo guardar la campaña.')
  }
}

async function handleDeleteCampaign() {
  const confirmed = await confirm({
    title: '¿Eliminar esta campaña?',
    message: 'Esta acción no se puede deshacer. Si tiene leads o lotes cargados, se va a rechazar.',
    confirmText: 'Eliminar',
    danger: true,
  })
  if (!confirmed) return
  deleteError.value = null
  try {
    await campaignsApi.deleteCampaign(campaignId.value)
    router.push({ name: 'campaigns' })
  } catch (err: any) {
    deleteError.value = err?.response?.data?.detail ?? 'No se pudo eliminar la campaña.'
  }
}

function onLiveNotification(event: Event) {
  const notification = (event as CustomEvent<AppNotification>).detail
  if (notification.payload.campaign_id === campaignId.value) {
    refreshLotesAndLeads()
  }
}

onMounted(() => {
  loadAll()
  window.addEventListener('nexo:notification', onLiveNotification)
})
onUnmounted(() => {
  if (pollHandle) clearInterval(pollHandle)
  window.removeEventListener('nexo:notification', onLiveNotification)
})
</script>

<template>
  <div v-if="campaign" class="space-y-8">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-xl font-semibold text-slate-700 dark:text-slate-200">{{ campaign.nombre }}</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ campaign.campaign_type_nombre }} · {{ campaign.division_nombre }}</p>
      </div>
      <div v-if="isAdmin && !editingCampaign" class="flex shrink-0 gap-3 text-xs">
        <button class="text-slate-500 underline hover:text-slate-800 dark:hover:text-slate-200" @click="startEditCampaign">Editar campaña</button>
        <button class="text-slate-500 underline hover:text-red-600" @click="handleDeleteCampaign">Eliminar campaña</button>
      </div>
    </div>
    <p v-if="deleteError" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
      {{ deleteError }}
    </p>

    <section v-if="editingCampaign" class="card grid max-w-2xl grid-cols-2 gap-3 p-4">
      <input v-model="campaignEdit.nombre" placeholder="Nombre" required class="col-span-2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <div>
        <label class="mb-1 block text-xs text-slate-400">Fecha inicio</label>
        <input v-model="campaignEdit.fecha_inicio" type="date" class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      </div>
      <div>
        <label class="mb-1 block text-xs text-slate-400">Fecha vencimiento</label>
        <input v-model="campaignEdit.fecha_fin" type="date" class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      </div>
      <select v-model="campaignEdit.estado" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option value="ACTIVA">Activa</option>
        <option value="CERRADA">Cerrada</option>
      </select>
      <input v-model="campaignEdit.producto_default" placeholder="Producto por defecto (opcional)" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />

      <div class="col-span-2">
        <label class="mb-1 block text-xs text-slate-400">Agencias con acceso (vacío = todas dentro del alcance normal del rol)</label>
        <MultiSelectPicker
          v-model="campaignEdit.agencias_habilitadas"
          :options="agenciaOptions"
          placeholder="Buscar agencia…"
        />
      </div>
      <div class="col-span-2">
        <label class="mb-1 block text-xs text-slate-400">Distritos con acceso (vacío = todos dentro del alcance normal del rol)</label>
        <MultiSelectPicker
          v-model="campaignEdit.distritos_habilitados"
          :options="territorioOptions"
          placeholder="Buscar distrito…"
        />
      </div>

      <div class="col-span-2 flex gap-3">
        <button class="rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-sm font-medium text-white" @click="saveCampaign">Guardar</button>
        <button class="text-sm text-slate-400 underline" @click="cancelEditCampaign">Cancelar</button>
      </div>
      <p v-if="campaignEditError" class="col-span-2 text-xs text-red-600">{{ campaignEditError }}</p>
    </section>

    <p v-if="loadError" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
      {{ loadError }}
    </p>
    <p v-if="campaign.esta_cerrada" class="rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-600 dark:bg-slate-800 dark:text-slate-300">
      Esta campaña está cerrada{{ campaign.fecha_fin ? ` (venció el ${campaign.fecha_fin})` : '' }} — no se pueden cargar leads ni registrar gestiones nuevas. Sigue permitida la reasignación.
    </p>

    <section v-if="canUpload" class="card p-4">
      <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Cargar base de leads (CSV/XLSX)</h2>
      <form class="space-y-3" @submit.prevent="handleUpload">
        <div class="flex flex-wrap items-center gap-3">
          <input ref="fileInput" type="file" accept=".csv,.xlsx" class="text-sm" />
          <button type="submit" :disabled="uploading" class="rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-sm font-medium text-white disabled:opacity-50">
            {{ uploading ? 'Subiendo…' : 'Subir' }}
          </button>
        </div>
        <div class="flex flex-wrap items-center gap-3 text-xs text-slate-500">
          <span>Restringir el lote (opcional):</span>
          <select v-model="restrictionForm.agencia_restriccion" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
            <option :value="null">Sin restricción de agencia</option>
            <option v-for="a in agencias" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
          <select v-model="restrictionForm.distrito_restriccion" class="rounded-md border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-900">
            <option :value="null">Sin restricción de distrito</option>
            <option v-for="t in territorios" :key="t.id" :value="t.id">{{ t.nombre }}</option>
          </select>
        </div>
        <p class="text-xs text-slate-400">
          Si eliges una agencia, todos los leads del archivo se cargan bajo esa agencia (ignora la columna "agencia_codigo").
          Si eliges un distrito sin agencia, cada fila debe traer una agencia que pertenezca a ese distrito.
        </p>

        <div v-if="columnasArchivo.length" class="rounded-md bg-slate-50 p-3 text-xs dark:bg-slate-800/60">
          <p class="mb-1.5 font-medium text-slate-600 dark:text-slate-300">Columnas que debe traer el archivo:</p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="col in columnasArchivo"
              :key="col.key"
              class="rounded-full bg-slate-200 px-2 py-0.5 font-mono dark:bg-slate-700"
              :title="col.label"
            >
              {{ col.key }}<span v-if="col.required" class="text-red-500"> *</span>
            </span>
          </div>
          <p class="mt-1.5 text-slate-400">* obligatorio.</p>
          <button
            type="button"
            class="mt-2 text-brand-600 underline hover:text-brand-800 dark:text-brand-400 dark:hover:text-brand-300"
            @click="handleDescargarPlantilla"
          >
            Descargar plantilla CSV
          </button>
        </div>
      </form>
      <p v-if="uploadError" class="mt-2 text-xs text-red-600">{{ uploadError }}</p>

      <table v-if="lotes.length" class="mt-4 w-full text-left text-xs">
        <thead class="text-slate-400">
          <tr><th class="pb-1">Archivo</th><th class="pb-1">Estado</th><th class="pb-1">Registros</th><th class="pb-1">Errores</th></tr>
        </thead>
        <tbody>
          <tr v-for="lote in lotes" :key="lote.id" class="text-slate-700 dark:text-slate-300">
            <td class="py-1 pr-2">{{ lote.nombre_archivo }}</td>
            <td class="py-1 pr-2">
              <span
                :class="{
                  'text-emerald-600': lote.estado === 'COMPLETADO',
                  'text-amber-600': lote.estado === 'PROCESANDO',
                  'text-red-600': lote.estado === 'ERROR',
                }"
              >{{ lote.estado }}</span>
            </td>
            <td class="py-1 pr-2">{{ lote.cantidad_registros }}</td>
            <td class="py-1 pr-2">
              <span v-if="lote.errores?.length" :title="lote.errores.map((e) => `Fila ${e.fila}: ${e.error}`).join('\n')">
                {{ lote.errores.length }} fila(s) con error (pasa el mouse)
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="canCreateProspecto" class="card p-4">
      <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">+ Nuevo prospecto</h2>
      <form class="space-y-3" @submit.prevent="handleCrearProspecto">
        <div v-if="!esEjecutivo" class="flex flex-wrap gap-3">
          <select
            v-if="rol !== 'JEFE' && rol !== 'SUBJEFE'"
            v-model="prospectoDistrito"
            class="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option :value="null">{{ rol === 'SUPERVISOR' ? 'Distrito…' : 'Todos los distritos' }}</option>
            <option v-for="t in territoriosSeleccionables" :key="t.id" :value="t.id">{{ t.nombre }}</option>
          </select>
          <select
            v-model="prospectoAgencia"
            required
            class="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
          >
            <option :value="null" disabled>Agencia…</option>
            <option v-for="a in agenciasSeleccionables" :key="a.id" :value="a.id">{{ a.nombre }}</option>
          </select>
        </div>

        <DynamicCaptureForm
          v-if="campaignType"
          v-model="prospectoForm"
          :field-definitions="campaignType.field_definitions"
          :sections="campaignType.secciones"
          origen="CARGA"
          hint="Al menos el documento de identidad es obligatorio."
        />

        <button
          type="submit"
          :disabled="prospectoSubmitting"
          class="rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {{ prospectoSubmitting ? 'Registrando…' : 'Registrar prospecto' }}
        </button>
        <p v-if="prospectoMessage" class="text-xs text-emerald-600">{{ prospectoMessage }}</p>
        <p v-if="prospectoError" class="rounded-md bg-red-50 px-3 py-2 text-xs text-red-700 dark:bg-red-950 dark:text-red-300">
          {{ prospectoError }}
        </p>
      </form>
    </section>

    <section class="card p-4">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-300">
          {{ esProspeccion ? 'Prospectos' : 'Leads' }} ({{ leadsCount }})
        </h2>
        <div v-if="canAssign && selectedLeadIds.length" class="flex items-center gap-2 text-sm">
          <span class="text-slate-500">{{ selectedLeadIds.length }} seleccionados</span>
          <button
            class="flex items-center gap-1.5 rounded-md bg-primary-600 hover:bg-primary-700 transition-colors px-3 py-1.5 text-sm text-white"
            @click="handleBulkAssign"
          >
            <UserSearch :size="16" /> Asignar a…
          </button>
        </div>
      </div>
      <p v-if="bulkMessage" class="mb-2 text-xs text-slate-500">{{ bulkMessage }}</p>
      <DynamicTable
        v-if="campaignType"
        :field-definitions="campaignType.field_definitions"
        :leads="leads"
        :selectable="canAssign"
        @row-click="goToLead"
        @selection-change="(ids) => (selectedLeadIds = ids)"
        @sort-change="handleLeadsSort"
        @filter-change="handleLeadsFilterChange"
      />
      <TablePagination :page="leadsPage" :page-size="leadsPageSize" :count="leadsCount" @update:page="handleLeadsPage" />
    </section>
  </div>
  <p v-else-if="loading" class="text-sm text-slate-400">Cargando…</p>
  <p v-else-if="loadError" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
    {{ loadError }}
  </p>
</template>
