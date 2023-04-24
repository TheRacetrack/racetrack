<script setup lang="ts">
import { ref, type Ref } from 'vue'
import { useRouter, RouterView } from 'vue-router'

import Footer from './components/Footer.vue'
import NavDrawer from './components/NavDrawer.vue'
import HeaderBar from './components/HeaderBar.vue'
import ProgressComponent from './components/ProgressComponent.vue'
import { loadUserData } from '@/services/UserDataStore'
import { progressService } from '@/services/ProgressService'
import { loadEnvironmentInfo } from '@/services/EnvironmentInfo'

const navDrawer: Ref<typeof NavDrawer | null> = ref(null)
const progressCompononent: Ref<typeof ProgressComponent | null> = ref(null)

function toggleNavDrawer() {
  navDrawer.value?.toggleLeftDrawer()
}

loadEnvironmentInfo()
loadUserData(useRouter())
progressService.init(progressCompononent)
</script>

<template>
  <q-layout view="hHh lpR lff">

    <ProgressComponent ref="progressCompononent"/>
    <HeaderBar @toggleDrawer="(msg) => toggleNavDrawer()"/>
    <NavDrawer ref="navDrawer"/>

    <q-page-container>
      <div id="app-container">
        <RouterView />
      </div>
    </q-page-container>

    <Footer/>

  </q-layout>
</template>
