import { createRouter, createWebHistory } from 'vue-router'

import { authGuard } from './guards'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    roles?: string[]
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/SidebarLayout.vue'),
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'campanas',
          name: 'campaigns',
          component: () => import('@/views/campaigns/CampaignsView.vue'),
        },
        {
          path: 'campanas/:id',
          name: 'campaign-detail',
          component: () => import('@/views/campaigns/CampaignDetailView.vue'),
        },
        {
          path: 'prospecciones',
          name: 'prospecciones',
          component: () => import('@/views/campaigns/ProspeccionesView.vue'),
        },
        {
          path: 'prospecciones/:id',
          name: 'prospeccion-detail',
          component: () => import('@/views/campaigns/CampaignDetailView.vue'),
        },
        {
          path: 'leads/:id',
          name: 'lead-detail',
          component: () => import('@/views/leads/LeadDetailView.vue'),
        },
        {
          path: 'oportunidades',
          name: 'opportunities',
          component: () => import('@/views/opportunities/OpportunitiesView.vue'),
        },
        {
          path: 'admin/usuarios',
          name: 'admin-usuarios',
          component: () => import('@/views/admin/UsersView.vue'),
          meta: { roles: ['ADMIN'] },
        },
        {
          path: 'admin/agencias',
          name: 'admin-agencias',
          component: () => import('@/views/admin/AgenciasView.vue'),
          meta: { roles: ['ADMIN'] },
        },
        {
          path: 'admin/tipos-campana',
          name: 'admin-tipos-campana',
          component: () => import('@/views/admin/CampaignTypesView.vue'),
          meta: { roles: ['ADMIN'] },
        },
        {
          path: 'admin/catalogos',
          name: 'admin-catalogos',
          component: () => import('@/views/admin/CatalogosView.vue'),
          meta: { roles: ['ADMIN'] },
        },
        {
          path: 'admin/divisiones',
          name: 'admin-divisiones',
          component: () => import('@/views/admin/DivisionesView.vue'),
          meta: { roles: ['ADMIN'] },
        },
      ],
    },
  ],
})

router.beforeEach(authGuard)

export default router
