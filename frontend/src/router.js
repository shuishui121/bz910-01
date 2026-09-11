import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  { path: '/login', component: () => import('./pages/LoginPage.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('./layouts/AppLayout.vue'),
    children: [
      { path: '', redirect: '/players' },
      { path: 'players', component: () => import('./pages/PlayerListPage.vue') },
      {
        path: 'players/:id',
        component: () => import('./pages/PlayerDetailPage.vue'),
        props: true,
      },
      {
        path: 'promotions',
        component: () => import('./pages/PromotionPage.vue'),
        meta: { roles: ['coach', 'admin'] },
      },
    ],
  },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const user = JSON.parse(localStorage.getItem('user') || 'null')
  if (!to.meta.public && !token) return '/login'
  if (to.meta.roles && (!user || !to.meta.roles.includes(user.role))) return '/players'
  return true
})

export default router
