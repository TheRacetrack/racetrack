import { createRouter, createWebHistory } from 'vue-router'

import JobsListView from '@/views/JobsListView.vue'
import GraphView from '@/views/GraphView.vue'
import PortfolioView from '@/views/PortfolioView.vue'
import ActivityView from '@/views/ActivityView.vue'
import ProfileView from '@/views/ProfileView.vue'
import AdministrationView from '@/views/AdministrationView.vue'
import LoginView from '@/views/LoginView.vue'
import LogoutView from '@/views/LogoutView.vue'
import RegisterView from '@/views/RegisterView.vue'
import ResetPasswordView from '@/views/ResetPasswordView.vue'
import ChangePasswordView from '@/views/ChangePasswordView.vue'
import PluginConfigView from '@/views/PluginConfigView.vue'
import PageNotFound from '@/views/PageNotFound.vue'
import DocsIndex from '@/views/docs/DocsIndex.vue'
import DocsPage from '@/views/docs/DocsPage.vue'
import { isAuthenticated } from '@/services/UserDataStore'
import { toastService } from '@/services/ToastService'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '',
      name: 'home',
      redirect: { name: 'jobs' },
    },
    {
      path: '/jobs',
      name: 'jobs',
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
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: { requiresAuth: true },
    },
    {
      path: '/change-password',
      name: 'change-password',
      component: ChangePasswordView,
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
    {
      path: '/plugin/config-editor/:pluginName/:pluginVersion',
      name: 'plugin-config',
      component: PluginConfigView,
    },
    {
      path: '/docs',
      name: 'docs-index',
      component: DocsIndex,
    },
    {
      path: '/docs/page/:pageName',
      name: 'docs-page',
      component: DocsPage,
    },
    { path: '/:catchAll(.*)', component: PageNotFound },
  ]
})

router.beforeEach((to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!isAuthenticated.value) {
      const nextPath = to.path
      next({ // redirect to login page
        name: 'login',
        query: {
          next: nextPath,
        },
      })
      toastService.info(`Please log in to see this page.`)
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
