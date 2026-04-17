import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'
import MainLayout from '../layouts/MainLayout.vue'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { requiresAuth: false } },
  { path: '/register', component: () => import('../views/Register.vue'), meta: { requiresAuth: false } },
  { path: '/forgot-password', component: () => import('../views/ForgotPassword.vue'), meta: { requiresAuth: false } },
  {
    path: '/',
    component: MainLayout,
    meta: { requiresAuth: false },// ← 改为 false，允许未登录访问
    children: [
      { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '工作台' } },
      { path: 'training/new', component: () => import('../views/TrainingNew.vue'), meta: { title: '新建训练' } },
      { path: 'training/history', component: () => import('../views/TrainingHistory.vue'), meta: { title: '训练历史' } },
      { path: 'training/detail/:id', component: () => import('../views/TrainingDetail.vue'), meta: { title: '训练详情' } },
      { path: 'profile', component: () => import('../views/Profile.vue'), meta: { title: '个人中心' } },
      { path: 'forum', component: () => import('../views/Forum.vue'), meta: { title: '社区' } },
      { path: '', redirect: 'dashboard' }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    return '/login'
  }
  return true
})

export default router