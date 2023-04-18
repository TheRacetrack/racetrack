<script setup lang="ts">
import { useRouter } from 'vue-router'
import { deleteUserData } from '@/services/UserDataStore'
import { ToastService } from '@/services/ToastService'

const router = useRouter()

function logout() {
  deleteUserData()
  router.push({ name: 'login' })
  ToastService.toastSuccess(`You're logged out.`)
}

logout()
</script>

<template>
</template>
