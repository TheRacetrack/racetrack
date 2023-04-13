<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

const leftDrawerOpen = ref(false)

function toggleLeftDrawer () {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

const links1 = [
  { icon: 'web', text: 'Top stories' },
  { icon: 'person', text: 'For you' },
  { icon: 'star_border', text: 'Favourites' },
  { icon: 'search', text: 'Saved searches' }
]

const links3 = [
  { icon: '', text: 'Settings' },
  { icon: '', text: 'Send feedback' },
  { icon: 'open_in_new', text: 'Help' }
]
</script>

<template>
  <q-layout view="hHh lpR fff">

    <q-header reveal elevated class="bg-black text-white" height-hint="64">
      <q-toolbar>
        <q-btn dense flat round icon="menu" @click="toggleLeftDrawer" />

        <q-toolbar-title>
          Racetrack Dashboard
        </q-toolbar-title>

        <q-space />

        <div class="q-gutter-sm row items-center no-wrap">
          <q-btn round dense flat color="grey-8" icon="notifications">
            <q-badge color="red" text-color="white" floating>
              2
            </q-badge>
            <q-tooltip>Notifications</q-tooltip>
          </q-btn>
          <q-btn round flat icon="apps">
            <q-tooltip>Account</q-tooltip>
          </q-btn>
        </div>
      </q-toolbar>
    </q-header>

    <q-drawer show-if-above v-model="leftDrawerOpen" side="left" bordered>
      <q-scroll-area class="fit">
        <q-list padding class="text-grey-8">

          <q-item v-ripple clickable to="/">
            <q-item-section avatar>
              <q-icon name="list" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Jobs</q-item-label>
            </q-item-section>
          </q-item>

          <q-item v-ripple clickable to="/graph">
            <q-item-section avatar>
              <q-icon name="mdi-graph-outline" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Graph</q-item-label>
            </q-item-section>
          </q-item>

          <q-item v-ripple clickable to="/portfolio">
            <q-item-section avatar>
              <q-icon name="" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Portfolio</q-item-label>
            </q-item-section>
          </q-item>

          <q-item v-ripple clickable to="/activity">
            <q-item-section avatar>
              <q-icon name="" />
            </q-item-section>
            <q-item-section>
              <q-item-label>Audit Log</q-item-label>
            </q-item-section>
          </q-item>

          <q-separator inset class="q-my-sm" />

          <q-item v-ripple clickable>
            <q-item-section>
              <q-item-label>Docs <q-icon name="open_in_new"/></q-item-label>
            </q-item-section>
          </q-item>

          <q-item v-ripple clickable>
            <q-item-section>
              <q-item-label>Profile</q-item-label>
            </q-item-section>
          </q-item>

          <q-item v-ripple clickable>
            <q-item-section>
              <q-item-label>Administration</q-item-label>
            </q-item-section>
          </q-item>

          <q-item v-ripple clickable>
            <q-item-section>
              <q-item-label>Logout</q-item-label>
            </q-item-section>
          </q-item>

        </q-list>
      </q-scroll-area>
    </q-drawer>

    <q-page-container>
      <div id="app-container">
        <RouterView />
      </div>
    </q-page-container>

    <q-footer elevated class="bg-grey-9 text-white">
      <div class="text-center q-my-sm">Racetrack version</div>
    </q-footer>

  </q-layout>
</template>
