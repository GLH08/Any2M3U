import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', component: () => import('@/views/Login.vue'), meta: { public: true } },
  { path: '/', component: () => import('@/views/Dashboard.vue') },
  { path: '/sources', component: () => import('@/views/Sources.vue') },
  { path: '/sources/:id', component: () => import('@/views/SourceDetail.vue'), props: true },
  { path: '/rules', component: () => import('@/views/Rules.vue') },
  { path: '/tokens', component: () => import('@/views/Tokens.vue') },
  { path: '/settings', component: () => import('@/views/Settings.vue') }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) await auth.fetchMe()
  if (!to.meta.public && !auth.user) return { path: '/login', query: { next: to.fullPath } }
  if (to.path === '/login' && auth.user) return { path: '/' }
})
