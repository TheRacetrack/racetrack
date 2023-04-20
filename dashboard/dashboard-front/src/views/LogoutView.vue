<script setup lang="ts">
import { useRouter } from 'vue-router'
import { apiClient } from '@/services/ApiClient'
import { deleteUserData } from '@/services/UserDataStore'
import { ToastService } from '@/services/ToastService'

const router = useRouter()

function logout() {
    deleteUserData()
    router.push({ name: 'login' })
    
    apiClient.get(`/api/accounts/logout`, false).then(response => {
        ToastService.success(`You're logged out.`)
    }).catch(err => {
        ToastService.showRequestError(`Failed to log out`, err)
    })
}

logout()
</script>

<template>
</template>
