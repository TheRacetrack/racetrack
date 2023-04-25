<script setup lang="ts">
import { computed, type Ref } from 'vue'
import { mdiAccountCircle, mdiLogout } from '@quasar/extras/mdi-v7'
import { isAuthenticated } from '@/services/UserDataStore'
import { envInfo } from '@/services/EnvironmentInfo'
import { isNotEmpty } from '@/services/StringUtils'

const emit = defineEmits(['toggleDrawer'])

function toggleDrawer () {
    emit('toggleDrawer', null)
}

const siteNamePrefix: Ref<string> = computed(() => {
    if (isNotEmpty(envInfo.site_name)) {
        return `[${envInfo.site_name}]`
    } else {
        return ''
    }
})

function getToolbarColor(siteName: string): string {
    if (siteName == 'test') {
        return '#1B5E20'
    } else if (siteName == 'preprod') {
        return '#EE6B00'
    } else if (siteName == 'prod') {
        return '#B71C1C'
    } else {
        return '#000000'
    }
}

const toolbarStyle: Ref<string> = computed(() => {
    const siteName = (envInfo.site_name || '').toLowerCase()
    const toolbarColor = getToolbarColor(siteName)
    return 'background-color: ' + toolbarColor + ';'
})
</script>

<template>
  <q-header reveal elevated class="bg-black text-white" height-hint="64">
    <q-toolbar :style="toolbarStyle">
      <q-btn dense flat round icon="menu"
        @click="toggleDrawer" v-if="isAuthenticated" />

      <q-toolbar-title>
        <router-link :to="{name: 'home'}" style="text-decoration: none; color: inherit;">
          <span class="text-grey-3 text-bold text-uppercase">{{siteNamePrefix}}</span>
          Racetrack Dashboard
        </router-link>
      </q-toolbar-title>

      <q-space />

      <div class="q-gutter-sm row items-center no-wrap">
        <q-btn round flat :icon="mdiAccountCircle"
          :to="{name: 'profile'}" v-if="isAuthenticated">
          <q-tooltip>Profile</q-tooltip>
        </q-btn>
        <q-btn round dense flat color="grey-5" :icon="mdiLogout"
          :to="{name: 'logout'}" v-if="isAuthenticated">
          <q-tooltip>Logout</q-tooltip>
        </q-btn>
      </div>
    </q-toolbar>
  </q-header>
</template>
