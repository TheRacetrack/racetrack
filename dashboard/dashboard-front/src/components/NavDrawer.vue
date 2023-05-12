<script setup lang="ts">
import { ref } from 'vue'
import { mdiGraphOutline, mdiTable, mdiAccountCircle, mdiTools, mdiLogout, mdiBookOpenVariant, mdiTextBoxOutline } from '@quasar/extras/mdi-v7'
import { outlinedMemory } from '@quasar/extras/material-icons-outlined'
import { isAuthenticated, isAdmin } from '@/services/UserDataStore'

const drawerOpen = ref(false)

function toggleLeftDrawer () {
  drawerOpen.value = !drawerOpen.value
}

defineExpose({
  toggleLeftDrawer
})
</script>

<template>
  <q-drawer
    show-if-above
    v-model="drawerOpen"
    side="left"
    bordered
    v-if="isAuthenticated"
    :width="220"
  >
    <q-scroll-area class="fit">
      <q-list padding class="text-grey-8">

        <q-item v-ripple clickable :to="{name: 'jobs'}">
          <q-item-section avatar>
            <q-icon :name="outlinedMemory" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Jobs</q-item-label>
          </q-item-section>
        </q-item>

        <q-item v-ripple clickable :to="{name: 'graph'}">
          <q-item-section avatar>
            <q-icon :name="mdiGraphOutline" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Graph</q-item-label>
          </q-item-section>
        </q-item>

        <q-item v-ripple clickable :to="{name: 'portfolio'}">
          <q-item-section avatar>
            <q-icon :name="mdiTable" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Portfolio</q-item-label>
          </q-item-section>
        </q-item>

        <q-item v-ripple clickable :to="{name: 'activity'}">
          <q-item-section avatar>
            <q-icon :name="mdiTextBoxOutline" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Audit Log</q-item-label>
          </q-item-section>
        </q-item>

        <q-separator inset class="q-my-sm" />

        <q-item v-ripple clickable :to="{name: 'profile'}">
          <q-item-section avatar>
            <q-icon :name="mdiAccountCircle" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Profile</q-item-label>
          </q-item-section>
        </q-item>

        <q-item v-ripple clickable :to="{name: 'administration'}"
          v-if="isAdmin">
          <q-item-section avatar>
            <q-icon :name="mdiTools" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Administration</q-item-label>
          </q-item-section>
        </q-item>

        <q-item v-ripple clickable :to="{name: 'docs-index'}">
          <q-item-section avatar>
            <q-icon :name="mdiBookOpenVariant" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Docs</q-item-label>
          </q-item-section>
        </q-item>
        
        <q-item v-ripple clickable :to="{name: 'logout'}">
          <q-item-section avatar>
            <q-icon :name="mdiLogout" />
          </q-item-section>
          <q-item-section>
            <q-item-label>Logout</q-item-label>
          </q-item-section>
        </q-item>

      </q-list>
    </q-scroll-area>
  </q-drawer>
</template>
