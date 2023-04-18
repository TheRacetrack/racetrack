<script setup lang="ts">
import router from '@/router'
import { deleteUserData } from '@/services/UserDataStore'
import { ToastService } from '@/services/ToastService'


function logout() {
  deleteUserData()
  router.push({ name: 'login' })
  ToastService.toastSuccess(`You're logged out.`)
}

logout()
</script>

<template>
</template>
