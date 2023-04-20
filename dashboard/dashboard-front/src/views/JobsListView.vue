<script setup lang="ts">
import { reactive } from 'vue'
import axios from "axios"
import { AUTH_HEADER } from '@/services/RequestUtils'
import { userData } from '@/services/UserDataStore'
import { ToastService } from '@/services/ToastService';

const jobsData = reactive({
  jobs: [],
})

function fetchJobs() {
    axios.get(`/api/job/list`, {
        headers: {
            [AUTH_HEADER]: userData.authToken,
        },
    }).then(response => {

        jobsData.jobs = response.data.jobs

    }).catch(err => {
        ToastService.showRequestError(`Failed to fetch the jobs`, err)
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
