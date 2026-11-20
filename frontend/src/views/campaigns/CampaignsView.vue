<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import * as accountsApi from '@/api/accounts'
import type { Division } from '@/api/accounts'
import * as campaignsApi from '@/api/campaigns'
import type { Campaign, CampaignType } from '@/api/campaigns'
import * as geoApi from '@/api/geo'
import type { Agencia, Territorio } from '@/api/geo'
import MultiSelectPicker from '@/components/MultiSelectPicker.vue'
import TablePagination from '@/components/TablePagination.vue'
import TableSearchInput from '@/components/TableSearchInput.vue'
import { usePagedResource } from '@/composables/usePagedResource'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const campaignsTable = usePagedResource<Campaign>(
  ({ search, ordering, page }) =>
    campaignsApi.fetchCampaigns({ campaign_type__modo_carga: 'MASIVA', search, ordering, page }),
  '-fecha_inicio',
)
const campaignTypes = ref<CampaignType[]>([])
const agencias = ref<Agencia[]>([])
const territorios = ref<Territorio[]>([])
const divisions = ref<Division[]>([])
const loading = ref(false)
const loadError = ref<string | null>(null)
const error = ref<string | null>(null)

const SORT_OPTIONS = [
  { value: '-fecha_inicio', label: 'Más recientes' },
  { value: 'fecha_inicio', label: 'Más antiguas' },
  { value: 'nombre', label: 'Nombre (A-Z)' },
  { value: '-nombre', label: 'Nombre (Z-A)' },
  { value: 'estado', label: 'Estado' },
]

const isAdmin = computed(() => authStore.roleName === 'ADMIN')
const agenciaOptions = computed(() => agencias.value.map((a) => ({ id: a.id, label: a.nombre })))
const territorioOptions = computed(() => territorios.value.map((t) => ({ id: t.id, label: t.nombre })))

const form = ref({
  nombre: '',
  campaign_type: null as number | null,
  division: authStore.user?.division ?? null,
  fecha_inicio: new Date().toISOString().slice(0, 10),
  fecha_fin: '',
  agencias_habilitadas: [] as number[],
  distritos_habilitados: [] as number[],
})

async function loadData() {
  loading.value = true
  loadError.value = null
  try {
    const [typesRes, agenciasRes, territoriosRes, divisionsRes] = await Promise.all([
      campaignsApi.fetchCampaignTypes({ modo_carga: 'MASIVA' }),
      geoApi.fetchAgencias(),
      geoApi.fetchTerritorios(),
      isAdmin.value ? accountsApi.fetchDivisions() : Promise.resolve(null),
      campaignsTable.load(),
    ])
    campaignTypes.value = typesRes.results
    agencias.value = agenciasRes.results
    territorios.value = territoriosRes.results
    if (divisionsRes) {
      divisions.value = divisionsRes.results
      if (!form.value.division && divisions.value.length === 1) {
        form.value.division = divisions.value[0].id
      }
    }
  } catch (err: any) {
    loadError.value = err?.response?.data?.detail ?? 'No se pudieron cargar las campañas.'
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!form.value.campaign_type || !form.value.division) return
  error.value = null
  try {
    await campaignsApi.createCampaign({
      nombre: form.value.nombre,
      campaign_type: form.value.campaign_type,
      division: form.value.division,
      fecha_inicio: form.value.fecha_inicio,
      fecha_fin: form.value.fecha_fin || null,
      agencias_habilitadas: form.value.agencias_habilitadas,
      distritos_habilitados: form.value.distritos_habilitados,
    })
    form.value.nombre = ''
    form.value.agencias_habilitadas = []
    form.value.distritos_habilitados = []
    await campaignsTable.load()
  } catch (err: any) {
    error.value = JSON.stringify(err?.response?.data ?? 'No se pudo crear la campaña.')
  }
}

function goToCampaign(campaign: Campaign) {
  router.push({ name: 'campaign-detail', params: { id: campaign.id } })
}

onMounted(loadData)
</script>

<template>
  <div class="space-y-8">
    <div>
      <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">Campañas</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400">Bases de leads por campaña de producto.</p>
    </div>

    <form v-if="isAdmin" class="card grid max-w-2xl grid-cols-2 gap-3 p-4" @submit.prevent="handleCreate">
      <input v-model="form.nombre" placeholder="Nombre de la campaña" required class="col-span-2 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      <select v-model="form.campaign_type" required class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option :value="null" disabled>Tipo de campaña…</option>
        <option v-for="ct in campaignTypes" :key="ct.id" :value="ct.id">{{ ct.nombre }}</option>
      </select>
      <select v-model="form.division" required class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option :value="null" disabled>División…</option>
        <option v-for="d in divisions" :key="d.id" :value="d.id">{{ d.nombre }}</option>
      </select>
      <div>
        <label class="mb-1 block text-xs text-slate-400">Fecha inicio</label>
        <input v-model="form.fecha_inicio" type="date" required class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      </div>
      <div>
        <label class="mb-1 block text-xs text-slate-400">Fecha vencimiento (opcional)</label>
        <input v-model="form.fecha_fin" type="date" class="w-full rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900" />
      </div>

      <div class="col-span-2">
        <label class="mb-1 block text-xs text-slate-400">
          Agencias con acceso (opcional — vacío = todas dentro del alcance normal del rol)
        </label>
        <MultiSelectPicker
          v-model="form.agencias_habilitadas"
          :options="agenciaOptions"
          placeholder="Buscar agencia…"
        />
      </div>

      <div class="col-span-2">
        <label class="mb-1 block text-xs text-slate-400">
          Distritos con acceso (opcional — vacío = todos dentro del alcance normal del rol)
        </label>
        <MultiSelectPicker
          v-model="form.distritos_habilitados"
          :options="territorioOptions"
          placeholder="Buscar distrito…"
        />
      </div>

      <button type="submit" class="col-span-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900">
        Crear campaña
      </button>
      <p v-if="error" class="col-span-2 text-xs text-red-600">{{ error }}</p>
      <p class="col-span-2 text-xs text-slate-400">
        ¿No hay tipos de campaña? Créalos primero en <router-link to="/admin/tipos-campana" class="underline">Administración → Tipos de campaña</router-link>.
      </p>
    </form>

    <p v-if="loadError" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
      {{ loadError }}
    </p>

    <section>
      <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
        <TableSearchInput placeholder="Buscar por nombre o producto…" @search="campaignsTable.setSearch" />
        <select
          :value="campaignsTable.ordering.value"
          class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900"
          @change="campaignsTable.setOrdering(($event.target as HTMLSelectElement).value)"
        >
          <option v-for="opt in SORT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <button
          v-for="campaign in campaignsTable.items.value"
          :key="campaign.id"
          class="card p-4 text-left hover:border-slate-400 dark:hover:border-slate-600"
          @click="goToCampaign(campaign)"
        >
          <p class="font-medium text-slate-900 dark:text-slate-100">{{ campaign.nombre }}</p>
          <p class="text-xs text-slate-500 dark:text-slate-400">{{ campaign.campaign_type_nombre }}</p>
          <p class="mt-1 text-xs text-slate-400">
            {{ campaign.fecha_inicio }}<span v-if="campaign.fecha_fin"> — {{ campaign.fecha_fin }}</span>
          </p>
          <span
            class="mt-2 inline-block rounded-full px-2 py-0.5 text-xs"
            :class="!campaign.esta_cerrada ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800'"
          >
            {{ campaign.esta_cerrada ? 'CERRADA' : 'ACTIVA' }}
          </span>
        </button>
        <p v-if="!campaignsTable.loading.value && campaignsTable.items.value.length === 0" class="text-sm text-slate-400">
          No hay campañas todavía.
        </p>
      </div>
      <TablePagination
        :page="campaignsTable.page.value"
        :page-size="campaignsTable.pageSize.value"
        :count="campaignsTable.count.value"
        @update:page="campaignsTable.setPage"
      />
      <p v-if="campaignsTable.error.value" class="mt-2 text-xs text-red-600">{{ campaignsTable.error.value }}</p>
    </section>
    <p v-if="loading" class="text-sm text-slate-400">Cargando…</p>
  </div>
</template>
