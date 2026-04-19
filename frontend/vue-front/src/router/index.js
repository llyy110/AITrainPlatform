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
    meta: { requiresAuth: false },
    children: [
      { path: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '工作台', requiresAuth: false } },
      { path: 'training/new', component: () => import('../views/TrainingNew.vue'), meta: { title: '新建训练', requiresAuth: true } },
      { path: 'training/history', component: () => import('../views/TrainingHistory.vue'), meta: { title: '训练历史', requiresAuth: true } },
      { path: 'training/detail/:id', component: () => import('../views/TrainingDetail.vue'), meta: { title: '训练详情', requiresAuth: true } },
      { path: 'profile', component: () => import('../views/Profile.vue'), meta: { title: '个人中心', requiresAuth: true } },
      { path: 'forum', component: () => import('../views/Forum.vue'), meta: { title: '社区', requiresAuth: false } },
      { path: 'forum/post/:id', component: () => import('../views/ForumDetail.vue'), meta: { title: '帖子详情', requiresAuth: false } },
      { path: '', redirect: 'dashboard' }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    sessionStorage.setItem('redirectAfterLogin', to.fullPath)
    next('/login')
  } else {
    next()
  }
})

export default router