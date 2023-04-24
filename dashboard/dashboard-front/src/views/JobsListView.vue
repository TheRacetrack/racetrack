<script setup lang="ts">
import { ref } from 'vue'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'

const jobsData = ref([])

function fetchJobs() {
    apiClient.get(`/api/v1/job`).then(response => {
        jobsData.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch the jobs`, err)
    })
}

fetchJobs()
</script>

<template>
    <q-card>
        <q-card-section>
            <div class="text-h6">
                Jobs
            </div>
        </q-card-section>
        
        <q-card-section class="q-pt-none">
            {{ jobsData }}
        </q-card-section>
    </q-card>
</template>
