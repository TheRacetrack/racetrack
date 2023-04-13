<script setup lang="ts">
import { ref, type Ref } from 'vue'
import { RouterView } from 'vue-router'

import Footer from './components/Footer.vue'
import NavDrawer from './components/NavDrawer.vue'
import HeaderBar from './components/HeaderBar.vue'

const navDrawer: Ref<typeof NavDrawer | null> = ref(null)

function toggleLeftDrawer() {
  navDrawer.value?.toggleLeftDrawer()
}
</script>

<template>
  <q-layout view="hHh lpR lff">

    <HeaderBar @toggleDrawer="(msg) => toggleLeftDrawer()"/>
    <NavDrawer ref="navDrawer"/>

    <q-page-container>
      <div id="app-container">
        <RouterView />
      </div>
    </q-page-container>

    <Footer/>

  </q-layout>
</template>
