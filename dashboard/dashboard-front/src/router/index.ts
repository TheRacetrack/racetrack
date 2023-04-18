import { createRouter, createWebHistory } from 'vue-router'

import JobsListView from '@/views/JobsListView.vue'
import GraphView from '@/views/GraphView.vue'
import PortfolioView from '@/views/PortfolioView.vue'
import ActivityView from '@/views/ActivityView.vue'
import DocsView from '@/views/DocsView.vue'
import ProfileView from '@/views/ProfileView.vue'
import AdministrationView from '@/views/AdministrationView.vue'
import LoginView from '@/views/LoginView.vue'
import LogoutView from '@/views/LogoutView.vue'
import RegisterView from '@/views/RegisterView.vue'
import ResetPasswordView from '@/views/ResetPasswordView.vue'
import PageNotFound from '@/views/PageNotFound.vue'
import { userData } from '@/services/UserDataStore'
import { ToastService } from '@/services/ToastService'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '',
      redirect: { path: '/list' },
    },
    {
      path: '/list',
      name: 'home',
      component: JobsListView,
      meta: { requiresAuth: true },
    },
    {
      path: '/graph',
      name: 'graph',
      component: GraphView,
      meta: { requiresAuth: true },
    },
    {
      path: '/portfolio',
      name: 'portfolio',
      component: PortfolioView,
      meta: { requiresAuth: true },
    },
    {
      path: '/activity',
      name: 'activity',
      component: ActivityView,
      meta: { requiresAuth: true },
    },
    {
      path: '/docs',
      name: 'docs',
      component: DocsView,
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true },
    },
    {
      path: '/administration',
      name: 'administration',
      component: AdministrationView,
      meta: { requiresAuth: true },
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/logout',
      name: 'logout',
      component: LogoutView,
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
    },
    {
      path: '/reset-password',
      name: 'reset-password',
      component: ResetPasswordView,
    },
    { path: '/:catchAll(.*)', component: PageNotFound },
  ]
})

router.beforeEach((to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!userData.isAuthenticated) {
      const nextPath = to.path
      next({ // redirect to login page
        name: 'login',
        query: {
          next: nextPath,
        },
      })
      ToastService.toastInfo(`Please log in to see this page.`)
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
