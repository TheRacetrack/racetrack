<script setup lang="ts">
import { reactive } from 'vue'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'

const jobsData = reactive({
    jobs: [],
})

function fetchJobs() {
    apiClient.get(`/api/job/list`).then(response => {
        jobsData.jobs = response.data.jobs
    }).catch(err => {
        toastService.showRequestError(`Failed to fetch the jobs`, err)
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
            {{ jobsData.jobs }}
        </q-card-section>
    </q-card>
</template>
