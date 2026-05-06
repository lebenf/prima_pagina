// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/join',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/components/layout/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'frontpage',
          component: () => import('@/views/FrontPageView.vue'),
        },
        {
          path: 'reader',
          name: 'reader',
          component: () => import('@/views/ReaderView.vue'),
        },
        {
          path: 'reader/:feedId',
          name: 'reader-feed',
          component: () => import('@/views/ReaderView.vue'),
        },
        {
          path: 'article/:id',
          name: 'article',
          component: () => import('@/views/ArticleView.vue'),
        },
        {
          path: 'feeds',
          name: 'feeds',
          component: () => import('@/views/FeedsView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
        },
        {
          path: 'admin',
          name: 'admin',
          component: () => import('@/views/AdminView.vue'),
          meta: { requiresAdmin: true },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
    },
  ],
})

// Track if we have already attempted to restore the session on first navigation
let sessionChecked = false

router.beforeEach(async to => {
  const auth = useAuthStore()

  // On the very first navigation, try to restore an existing session
  if (!sessionChecked && !to.meta.public) {
    sessionChecked = true
    if (!auth.isAuthenticated) {
      await auth.fetchMe()
    }
  }

  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: 'frontpage' }
  }

  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'frontpage' }
  }
})

export default router
