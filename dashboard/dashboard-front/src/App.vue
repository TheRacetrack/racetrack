<script setup lang="ts">
import { ref, type Ref } from 'vue'
import { RouterView } from 'vue-router'

import Footer from './components/Footer.vue'
import NavDrawer from './components/NavDrawer.vue'
import HeaderBar from './components/HeaderBar.vue'
import ConfirmationDialog from './components/ConfirmationDialog.vue'
import { loadUserData } from '@/services/UserDataStore'
import { DialogService } from '@/services/DialogService'
import { loadEnvironmentInfo } from '@/services/EnvironmentInfo'

const navDrawer: Ref<typeof NavDrawer | null> = ref(null)
const confirmDialog: Ref<typeof ConfirmationDialog | null> = ref(null)

function toggleLeftDrawer() {
  navDrawer.value?.toggleLeftDrawer()
}

loadUserData()
loadEnvironmentInfo()
DialogService.init(confirmDialog)
</script>

<template>
  <q-layout view="hHh lpR lff">

    <HeaderBar @toggleDrawer="(msg) => toggleLeftDrawer()"/>
    <NavDrawer ref="navDrawer"/>
    <ConfirmationDialog ref="confirmDialog"/>

    <q-page-container>
      <div id="app-container">
        <RouterView />
      </div>
    </q-page-container>

    <Footer/>

  </q-layout>
</template>
