<script setup lang="ts">
import { ref } from 'vue'
import { progressService } from '@/services/ProgressService'
import { apiClient } from '@/services/ApiClient'

const props = defineProps({
    jobName: { type: String, required: true },
    jobVersion: { type: String, required: true },
})

const emit = defineEmits(['jobDeleted'])

const loading = ref(false)

function deleteJob() {
    const name = props.jobName
    const version = props.jobVersion
    progressService.confirmWithLoading({
        confirmQuestion: `Are you sure you want to delete the job "${name} ${version}"?`,
        onConfirm: () => {
            loading.value = true
            return apiClient.delete(`/api/v1/job/${name}/${version}`)
        },
        progressMsg: `Deleting job ${name} ${version}...`,
        successMsg: `Job ${name} ${version} has been deleted.`,
        errorMsg: `Failed to delete a job ${name} ${version}`,
        onSuccess: () => {
            emit('jobDeleted', null)
        },
        onFinally: () => {
            loading.value = false
        },
    })
}
</script>

<template>
    <q-btn color="negative" push label="Delete" icon="delete" :loading="loading" @click="deleteJob()" />
</template>
