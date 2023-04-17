<script setup lang="ts">
import { mdiAccountCircle, mdiLogout } from '@quasar/extras/mdi-v7'

const emit = defineEmits(['toggleDrawer'])

function toggleDrawer () {
  emit('toggleDrawer', null)
}
</script>

<template>
  <q-header reveal elevated class="bg-black text-white" height-hint="64">
    <q-toolbar>
      <q-btn dense flat round icon="menu" @click="toggleDrawer" />

      <q-toolbar-title>
        Racetrack Dashboard
      </q-toolbar-title>

      <q-space />

      <div class="q-gutter-sm row items-center no-wrap">
        <q-btn round flat :icon="mdiAccountCircle" to="/profile">
          <q-tooltip>Profile</q-tooltip>
        </q-btn>
        <q-btn round dense flat color="grey-5" :icon="mdiLogout" to="/logout">
          <q-tooltip>Logout</q-tooltip>
        </q-btn>
      </div>
    </q-toolbar>
  </q-header>
</template>
