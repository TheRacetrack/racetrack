import { createRouter, createWebHistory } from 'vue-router'

import { hasAuthCookie, isAuthenticated } from '@/services/UserDataStore'
import { toastService } from '@/services/ToastService'
import LoginView from '@/components/account/LoginView.vue'
import LogoutView from '@/components/account/LogoutView.vue'
import RegisterView from '@/components/account/RegisterView.vue'
import ResetPasswordView from '@/components/account/ResetPasswordView.vue'
import ChangePasswordView from '@/components/account/ChangePasswordView.vue'
import DocsIndex from '@/components/docs/DocsIndex.vue'
import DocsPage from '@/components/docs/DocsPage.vue'
import DocsPlugin from '@/components/docs/DocsPlugin.vue'
import JobsListView from '@/components/jobs/JobsListView.vue'
import DeployForm from '@/components/jobs/deployment/DeployForm.vue'
import DeploymentsList from '@/components/jobs/deployment/DeploymentsList.vue'
import DeploymentDetails from '@/components/jobs/deployment/DeploymentDetails.vue'
import GraphView from '@/components/jobs/graph/GraphView.vue'
import PortfolioView from '@/components/jobs/portfolio/PortfolioView.vue'
import AuditLogView from '@/components/jobs/audit/AuditLogView.vue'
import ProfileView from '@/components/account/ProfileView.vue'
import AdministrationView from '@/components/admin/AdministrationView.vue'
import PluginConfigView from '@/components/admin/PluginConfigView.vue'
import PageNotFound from '@/components/PageNotFound.vue'

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
      path: '/jobs/deploy',
      name: 'deploy-job',
      component: DeployForm,
      meta: { requiresAuth: true },
    },
    {
      path: '/deployments',
      name: 'deployments',
      component: DeploymentsList,
      meta: { requiresAuth: true },
    },
    {
      path: '/deployments/:deploymentId',
      name: 'deployment-details',
      component: DeploymentDetails,
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
      component: AuditLogView,
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
    {
      path: '/docs/plugin/:pageName',
      name: 'docs-plugin',
      component: DocsPlugin,
    },
    { path: '/:catchAll(.*)', component: PageNotFound },
  ]
})

router.beforeEach((to, from, next) => {
    if (to.matched.some(record => record.meta.requiresAuth)) {
        if (!isAuthenticated.value || !hasAuthCookie()) {
            const nextPath = to.path
            next({ // redirect to login page
                name: 'login',
                query: {next: nextPath},
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
