<script setup lang="ts">
import { useRouter } from 'vue-router'
import { apiClient } from '@/services/ApiClient'
import { deleteUserData } from '@/services/UserDataStore'
import { toastService } from '@/services/ToastService'

const router = useRouter()

function logout() {
    deleteUserData()
    router.push({ name: 'login' })
    
    apiClient.get(`/api/v1/users/logout`, false).then(response => {
        toastService.success(`You're logged out.`)
    }).catch(err => {
        toastService.showErrorDetails(`Failed to log out`, err)
    })
}

logout()
</script>

<template>
</template>
