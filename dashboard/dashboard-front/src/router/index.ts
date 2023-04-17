import { createRouter, createWebHistory } from 'vue-router'

import JobsListView from '../views/JobsListView.vue'
import GraphView from '../views/GraphView.vue'
import PortfolioView from '../views/PortfolioView.vue'
import ActivityView from '../views/ActivityView.vue'
import DocsView from '../views/DocsView.vue'
import ProfileView from '../views/ProfileView.vue'
import AdministrationView from '../views/AdministrationView.vue'
import LoginView from '../views/LoginView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: JobsListView,
    },
    {
      path: '/graph',
      name: 'graph',
      component: GraphView,
    },
    {
      path: '/portfolio',
      name: 'portfolio',
      component: PortfolioView,
    },
    {
      path: '/activity',
      name: 'activity',
      component: ActivityView,
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
    },
    {
      path: '/administration',
      name: 'administration',
      component: AdministrationView,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
  ]
})

export default router
