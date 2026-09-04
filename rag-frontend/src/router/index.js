import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue')
      },
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('@/views/Upload.vue')
      },
      {
        path: 'tasks',
        name: 'Tasks',
        component: () => import('@/views/Tasks.vue')
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/Documents.vue')
      },
      {
        path: 'apikeys',
        name: 'ApiKeys',
        component: () => import('@/views/ApiKeys.vue')
      },
      {
        path: 'feedback',
        name: 'Feedback',
        component: () => import('@/views/Feedback.vue')
      },
      {
        path: 'cache',
        name: 'Cache',
        component: () => import('@/views/Cache.vue')
      },
      {
  path: 'history',
  name: 'History',
  component: () => import('@/views/History.vue'),
  meta: { title: 'Historique' }
}
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router