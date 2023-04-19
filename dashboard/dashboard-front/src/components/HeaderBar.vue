<script setup lang="ts">
import { mdiAccountCircle, mdiLogout } from '@quasar/extras/mdi-v7'

import { userData } from '@/services/UserDataStore'

const emit = defineEmits(['toggleDrawer'])

function toggleDrawer () {
  emit('toggleDrawer', null)
}
</script>

<template>
  <q-header reveal elevated class="bg-black text-white" height-hint="64">
    <q-toolbar>
      <q-btn dense flat round icon="menu"
        @click="toggleDrawer" v-if="userData.isAuthenticated" />

      <q-toolbar-title>
        <router-link :to="{name: 'home'}" style="text-decoration: none; color: inherit;">
          Racetrack Dashboard
        </router-link>
      </q-toolbar-title>

      <q-space />

      <div class="q-gutter-sm row items-center no-wrap">
        <q-btn round flat :icon="mdiAccountCircle"
          :to="{name: 'profile'}" v-if="userData.isAuthenticated">
          <q-tooltip>Profile</q-tooltip>
        </q-btn>
        <q-btn round dense flat color="grey-5" :icon="mdiLogout"
          :to="{name: 'logout'}" v-if="userData.isAuthenticated">
          <q-tooltip>Logout</q-tooltip>
        </q-btn>
      </div>
    </q-toolbar>
  </q-header>
</template>
