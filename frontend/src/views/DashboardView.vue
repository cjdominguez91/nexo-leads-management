<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import * as campaignsApi from '@/api/campaigns'
import type { Campaign } from '@/api/campaigns'
import * as dashboardsApi from '@/api/dashboards'
import type { AgruparPor, EfectividadRow, ResumenDashboard } from '@/api/dashboards'
import * as geoApi from '@/api/geo'
import type { Agencia, Territorio } from '@/api/geo'
import * as leadsApi from '@/api/leads'
import type { AsignableUser } from '@/api/leads'
import BarChart from '@/components/dashboards/BarChart.vue'
import EfectividadTable from '@/components/dashboards/EfectividadTable.vue'
import RankingList from '@/components/dashboards/RankingList.vue'
import StatTile from '@/components/dashboards/StatTile.vue'
import TrendChart from '@/components/dashboards/TrendChart.vue'
import type { BarChartItem } from '@/components/dashboards/BarChart.vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

type Tab = 'general' | 'distrito' | 'agencia' | 'ejecutivo'
type FiltroCampo = 'campaign' | 'distrito' | 'agencia' | 'usuario_asignado'

const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const rol = computed(() => authStore.roleName)
const esEjecutivo = computed(() => rol.value === 'EJECUTIVO')
const esAdminOGerente = computed(() => rol.value === 'ADMIN' || rol.value === 'GERENTE')

// Qué tabs puede ver cada rol (ver sección 6 del pedido: Admin/Gerente sin
// restricción; Supervisor no necesita "por Distrito" porque ya está
// confinado a los suyos; Jefe/Subjefe tampoco necesitan "por Agencia" por
// el mismo motivo — comparar contra sí mismos no aporta.
const TAB_ACCESS: Record<string, Tab[]> = {
  ADMIN: ['general', 'distrito', 'agencia', 'ejecutivo'],
  GERENTE: ['general', 'distrito', 'agencia', 'ejecutivo'],
  SUPERVISOR: ['general', 'agencia', 'ejecutivo'],
  JEFE: ['general', 'ejecutivo'],
  SUBJEFE: ['general', 'ejecutivo'],
  EJECUTIVO: ['general', 'ejecutivo'],
}
const TAB_LABEL: Record<Tab, string> = { general: 'General', distrito: 'Distrito', agencia: 'Agencia', ejecutivo: 'Ejecutivo' }
const FILTERS_BY_TAB: Record<Tab, FiltroCampo[]> = {
  general: ['campaign', 'distrito', 'agencia', 'usuario_asignado'],
  distrito: ['campaign', 'distrito'],
  agencia: ['campaign', 'distrito', 'agencia'],
  ejecutivo: ['campaign', 'distrito', 'agencia', 'usuario_asignado'],
}
const AGRUPAR_POR_TAB: Record<Tab, AgruparPor> = {
  general: 'campaign',
  distrito: 'distrito',
  agencia: 'agencia',
  ejecutivo: 'usuario_asignado',
}

const visibleTabs = computed(() => TAB_ACCESS[rol.value ?? ''] ?? ['general'])
const activeTab = ref<Tab>('general')
const filtrosVisibles = computed(() => (esEjecutivo.value ? [] : FILTERS_BY_TAB[activeTab.value]))

const campanas_ref = ref<Campaign[]>([])
const agencias = ref<Agencia[]>([])
const territorios = ref<Territorio[]>([])
const asignables = ref<AsignableUser[]>([])

const filtros = ref({
  campaign: null as number | null,
  agencia: null as number | null,
  distrito: null as number | null,
  usuario_asignado: null as number | null,
})
const rangoPreset = ref<'7' | '30' | '90' | 'todo'>('30')

const RANGO_OPTIONS = [
  { value: '7', label: 'Últimos 7 días' },
  { value: '30', label: 'Últimos 30 días' },
  { value: '90', label: 'Últimos 90 días' },
  { value: 'todo', label: 'Todo el histórico' },
]

const agenciasSeleccionables = computed(() => {
  if (rol.value === 'JEFE' || rol.value === 'SUBJEFE') {
    const misAgenciaIds = new Set((authStore.user?.agencias ?? []).filter((a) => a.activo).map((a) => a.agencia))
    return agencias.value.filter((a) => misAgenciaIds.has(a.id))
  }
  if (rol.value === 'SUPERVISOR') {
    return filtros.value.distrito ? agencias.value.filter((a) => a.territorio === filtros.value.distrito) : []
  }
  return filtros.value.distrito ? agencias.value.filter((a) => a.territorio === filtros.value.distrito) : agencias.value
})
const territoriosSeleccionables = computed(() => {
  if (rol.value === 'SUPERVISOR') {
    const misTerritorioIds = new Set((authStore.user?.territorios ?? []).filter((t) => t.activo).map((t) => t.territorio))
    return territorios.value.filter((t) => misTerritorioIds.has(t.id))
  }
  return territorios.value
})

const loading = ref(false)
const resumen = ref<ResumenDashboard | null>(null)
const tendencia = ref<{ gestiones: { date: string; value: number }[]; ganadas: { date: string; value: number }[] } | null>(null)
const efectividad = ref<EfectividadRow[]>([])

const ESTADO_ORDER: { key: keyof ResumenDashboard['por_estado']; label: string }[] = [
  { key: 'NUEVO', label: 'Nuevo' },
  { key: 'ASIGNADO', label: 'Asignado' },
  { key: 'GESTIONADO', label: 'Gestionado' },
  { key: 'GANADO', label: 'Ganado' },
  { key: 'PERDIDO', label: 'Perdido' },
]

const estadoColors = computed(() => {
  const dark = themeStore.isDark
  return {
    NUEVO: dark ? '#9ec5f4' : '#6da7ec',
    ASIGNADO: dark ? '#5598e7' : '#2a78d6',
    GESTIONADO: dark ? '#256abf' : '#184f95',
    GANADO: '#0ca30c',
    PERDIDO: '#d03b3b',
  }
})
const CATEGORICAL_LIGHT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
const CATEGORICAL_DARK = ['#3987e5', '#d95926', '#199e70', '#c98500', '#d55181', '#008300', '#9085e9', '#e66767']
const categoricalColors = computed(() => (themeStore.isDark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT))

function fmtPct(value: number) {
  return `${Math.round(value * 100)}%`
}

const estadoItems = computed<BarChartItem[]>(() =>
  ESTADO_ORDER.map((e) => ({
    label: e.label,
    value: resumen.value?.por_estado[e.key] ?? 0,
    color: estadoColors.value[e.key],
  })),
)
function estadoValueLabel(value: number) {
  const total = resumen.value?.total ?? 0
  return `${value} (${total ? Math.round((value / total) * 100) : 0}%)`
}

function topConOtros(items: { label: string; cantidad: number }[]): BarChartItem[] {
  const top = items.slice(0, 7)
  const resto = items.slice(7)
  const out = top.map((c, i) => ({ label: c.label, value: c.cantidad, color: categoricalColors.value[i] }))
  if (resto.length) {
    out.push({ label: 'Otros', value: resto.reduce((sum, c) => sum + c.cantidad, 0), color: categoricalColors.value[7] })
  }
  return out
}
const categoriaItems = computed(() =>
  topConOtros((resumen.value?.por_categoria ?? []).map((c) => ({ label: c.categoria, cantidad: c.cantidad }))),
)
const subcategoriaItems = computed(() =>
  topConOtros((resumen.value?.por_subcategoria ?? []).map((c) => ({ label: c.subcategoria, cantidad: c.cantidad }))),
)
const distribucionCampanaItems = computed<BarChartItem[]>(() =>
  [...efectividad.value]
    .sort((a, b) => b.total - a.total)
    .slice(0, 8)
    .map((row, i) => ({ label: row.nombre, value: row.total, color: categoricalColors.value[i % categoricalColors.value.length] })),
)

const trendSeries = computed(() => {
  if (!tendencia.value) return []
  return [
    { name: 'Gestiones', color: categoricalColors.value[0], points: tendencia.value.gestiones },
    { name: 'Ganadas', color: categoricalColors.value[2], points: tendencia.value.ganadas },
  ]
})

function diasDelRango(): number {
  return rangoPreset.value === 'todo' ? 0 : Number(rangoPreset.value)
}
function fechaDesde(): string | undefined {
  const dias = diasDelRango()
  if (!dias) return undefined
  const d = new Date()
  d.setDate(d.getDate() - dias)
  return d.toISOString().slice(0, 10)
}
function buildContinuousSeries(raw: { fecha: string; cantidad: number }[], dias: number) {
  const map = new Map(raw.map((r) => [r.fecha, r.cantidad]))
  const points: { date: string; value: number }[] = []
  const hoy = new Date()
  for (let i = dias - 1; i >= 0; i--) {
    const d = new Date(hoy)
    d.setDate(d.getDate() - i)
    const iso = d.toISOString().slice(0, 10)
    points.push({ date: iso, value: map.get(iso) ?? 0 })
  }
  return points
}

function filtrosParams() {
  return {
    campaign: filtros.value.campaign ?? undefined,
    agencia: filtros.value.agencia ?? undefined,
    distrito: filtros.value.distrito ?? undefined,
    usuario_asignado: esEjecutivo.value ? undefined : (filtros.value.usuario_asignado ?? undefined),
    fecha_desde: fechaDesde(),
  }
}

async function loadDashboard() {
  loading.value = true
  try {
    const diasTendencia = diasDelRango() || 90
    const agruparPor = AGRUPAR_POR_TAB[activeTab.value]
    const [resumenRes, tendenciaRes, efectividadRes] = await Promise.all([
      dashboardsApi.fetchResumen(filtrosParams()),
      dashboardsApi.fetchTendencia({ ...filtrosParams(), dias: diasTendencia }),
      dashboardsApi.fetchEfectividad(agruparPor, filtrosParams()),
    ])
    resumen.value = resumenRes
    tendencia.value = {
      gestiones: buildContinuousSeries(tendenciaRes.gestiones_por_dia, diasTendencia),
      ganadas: buildContinuousSeries(tendenciaRes.ganadas_por_dia, diasTendencia),
    }
    efectividad.value = efectividadRes
  } finally {
    loading.value = false
  }
}

async function loadFiltrosData() {
  const [campanasRes, agenciasRes, territoriosRes] = await Promise.all([
    campaignsApi.fetchCampaigns(),
    geoApi.fetchAgencias(),
    geoApi.fetchTerritorios(),
  ])
  campanas_ref.value = campanasRes.results
  agencias.value = agenciasRes.results
  territorios.value = territoriosRes.results
  if (!esEjecutivo.value) {
    const asignablesRes = await leadsApi.fetchUsuariosAsignables()
    asignables.value = asignablesRes.results
  }
}

function goToCampaign(campaignId: number) {
  const original = campanas_ref.value.find((c) => c.id === campaignId)
  const routeName = original?.campaign_type_modo_carga === 'INDIVIDUAL' ? 'prospeccion-detail' : 'campaign-detail'
  router.push({ name: routeName, params: { id: campaignId } })
}

watch(activeTab, (tab) => {
  const allowed = FILTERS_BY_TAB[tab]
  if (!allowed.includes('agencia')) filtros.value.agencia = null
  if (!allowed.includes('usuario_asignado')) filtros.value.usuario_asignado = null
  if (!allowed.includes('distrito')) filtros.value.distrito = null
})

watch([activeTab, filtros, rangoPreset], loadDashboard, { deep: true })

onMounted(async () => {
  activeTab.value = visibleTabs.value[0] ?? 'general'
  await loadFiltrosData()
  await loadDashboard()
})
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">
        {{ esEjecutivo ? 'Mi dashboard' : 'Dashboard' }}
      </h1>
      <p class="text-sm text-slate-500 dark:text-slate-400">
        {{ esEjecutivo ? 'El estado y la efectividad de tus leads.' : 'Vista 360 del estado y efectividad de los leads dentro de tu alcance.' }}
      </p>
    </div>

    <div v-if="visibleTabs.length > 1" class="flex gap-1 border-b border-slate-200 dark:border-slate-800">
      <button
        v-for="tab in visibleTabs"
        :key="tab"
        type="button"
        class="-mb-px border-b-2 px-3 py-2 text-sm font-medium"
        :class="activeTab === tab ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400' : 'border-transparent text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'"
        @click="activeTab = tab"
      >
        {{ TAB_LABEL[tab] }}
      </button>
    </div>

    <div class="card flex flex-wrap items-center gap-3 p-3">
      <select v-model="rangoPreset" class="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option v-for="opt in RANGO_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
      </select>
      <select v-if="filtrosVisibles.includes('campaign')" v-model="filtros.campaign" class="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option :value="null">Todas las campañas</option>
        <option v-for="c in campanas_ref" :key="c.id" :value="c.id">{{ c.nombre }}</option>
      </select>
      <select v-if="filtrosVisibles.includes('distrito')" v-model="filtros.distrito" class="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option :value="null">Todos los distritos</option>
        <option v-for="t in territoriosSeleccionables" :key="t.id" :value="t.id">{{ t.nombre }}</option>
      </select>
      <select v-if="filtrosVisibles.includes('agencia')" v-model="filtros.agencia" class="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option :value="null">Todas las agencias</option>
        <option v-for="a in agenciasSeleccionables" :key="a.id" :value="a.id">{{ a.nombre }}</option>
      </select>
      <select v-if="filtrosVisibles.includes('usuario_asignado')" v-model="filtros.usuario_asignado" class="rounded-md border border-slate-300 px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900">
        <option :value="null">Todos los ejecutivos</option>
        <option v-for="u in asignables" :key="u.id" :value="u.id">{{ u.email }}</option>
      </select>
    </div>

    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4" :class="{ 'opacity-60': loading }">
      <StatTile label="Total de leads" :value="String(resumen?.total ?? 0)" />
      <StatTile label="Tasa de contacto" :value="fmtPct(resumen?.tasa_contacto ?? 0)" :delta-pts="resumen?.variacion ? (resumen.tasa_contacto - resumen.variacion.tasa_contacto) : null" />
      <StatTile label="Tasa de efectividad" :value="fmtPct(resumen?.tasa_efectividad ?? 0)" :delta-pts="resumen?.variacion ? (resumen.tasa_efectividad - resumen.variacion.tasa_efectividad) : null" />
      <StatTile
        label="Sin gestionar +7 días"
        :value="String(resumen?.sin_gestionar_hace_mas_de_7_dias ?? 0)"
        :alert="(resumen?.sin_gestionar_hace_mas_de_7_dias ?? 0) > 0"
      />
      <StatTile v-if="activeTab === 'general'" label="Campañas activas" :value="String(resumen?.campanas_activas ?? 0)" />
      <StatTile v-if="activeTab === 'general'" label="Leads activos" :value="String(resumen?.leads_activos ?? 0)" />
      <StatTile label="Tasa de conversión" :value="fmtPct(resumen?.tasa_conversion ?? 0)" />
      <StatTile
        label="Sin asignar"
        :value="String(resumen?.sin_asignar ?? 0)"
        :alert="(resumen?.sin_asignar ?? 0) > 0"
      />
      <StatTile
        label="Tiempo prom. a primera gestión"
        :value="resumen?.tiempo_promedio_primera_gestion_horas != null ? `${resumen.tiempo_promedio_primera_gestion_horas} h` : '—'"
      />
    </div>

    <div class="grid gap-4 lg:grid-cols-2" :class="{ 'opacity-60': loading }">
      <section class="card p-4">
        <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Estado de los leads</h2>
        <BarChart :items="estadoItems" :format-value="estadoValueLabel" />
      </section>
      <section class="card p-4">
        <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Por categoría de tipificación</h2>
        <BarChart :items="categoriaItems" />
      </section>
    </div>

    <div v-if="activeTab === 'general' && esAdminOGerente" class="grid gap-4 lg:grid-cols-2" :class="{ 'opacity-60': loading }">
      <section class="card p-4">
        <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Total de registros por subcategoría</h2>
        <BarChart :items="subcategoriaItems" />
      </section>
      <section v-if="!filtros.campaign" class="card p-4">
        <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Distribución de registros por campaña</h2>
        <BarChart :items="distribucionCampanaItems" @bar-click="() => {}" />
      </section>
    </div>

    <section class="card p-4" :class="{ 'opacity-60': loading }">
      <h2 class="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Tendencia — gestiones y oportunidades ganadas</h2>
      <TrendChart :series="trendSeries" />
    </section>

    <section class="card p-4" :class="{ 'opacity-60': loading }">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-300">
          Efectividad por {{ TAB_LABEL[activeTab].toLowerCase() === 'general' ? 'campaña' : TAB_LABEL[activeTab].toLowerCase() }}
        </h2>
      </div>
      <EfectividadTable
        :rows="efectividad"
        :columna-label="activeTab === 'general' ? 'Campaña' : TAB_LABEL[activeTab]"
        :clickable="activeTab === 'general'"
        @row-click="(row) => activeTab === 'general' && goToCampaign(row.id)"
      />
      <div v-if="activeTab !== 'general'" class="mt-6 grid gap-6 border-t border-slate-100 pt-4 dark:border-slate-900 sm:grid-cols-2">
        <div>
          <h3 class="mb-2 text-xs font-semibold uppercase text-slate-400">Top 5</h3>
          <RankingList :rows="efectividad" direccion="top" />
        </div>
        <div>
          <h3 class="mb-2 text-xs font-semibold uppercase text-slate-400">Bottom 5</h3>
          <RankingList :rows="efectividad" direccion="bottom" />
        </div>
      </div>
    </section>
  </div>
</template>
