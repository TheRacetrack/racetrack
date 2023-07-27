<script setup lang="ts">
import type { JobData } from '@/utils/api-schema'
import { ref, type Ref } from 'vue'
import { progressService } from '@/services/ProgressService'
import { apiClient } from '@/services/ApiClient'

const dialogOpen = ref(false)
const loading = ref(false)
const job: Ref<JobData | null> = ref(null)
const manifestYaml: Ref<string> = ref('')

function openDialog(jobData: JobData, yamlText: string) {
    job.value = jobData
    manifestYaml.value = yamlText
    dialogOpen.value = true
}

function saveManifest() {
    progressService.runLoading({
        task: apiClient.put(`/api/v1/job/${job.value?.name}/${job.value?.version}/manifest`, {
            'manifest_yaml': manifestYaml.value,
        }),
        loadingState: loading,
        progressMsg: `Saving manifest...`,
        successMsg: `Manifest saved.`,
        errorMsg: `Failed to save manifest`,
        onSuccess: () => {
            dialogOpen.value = false
            emit('jobUpdated', null)
        },
    })
}

const emit = defineEmits(['jobUpdated'])

defineExpose({
    openDialog,
})
</script>

<template>
    <q-dialog v-model="dialogOpen">
        <q-card style="width: 800px; max-width: 80vw;">
            <q-card-section>
                <div class="text-h6">Manifest of a job {{job?.name}} {{job?.version}}</div>
            </q-card-section>
            <q-card-section>
                <div>
                    <q-input
                        outlined
                        v-model="manifestYaml"
                        label="YAML Manifest"
                        type="textarea"
                        class="x-monospace"
                        input-style="min-height: 20em !important;"
                        autogrow
                        />
                </div>
                <div class="row q-pt-sm">
                    <q-space />
                    <q-btn flat color="white" text-color="black" label="Cancel" v-close-popup />
                    <q-btn color="primary" push label="Save" icon="save"
                        @click="saveManifest" :loading="loading" />
                </div>
            </q-card-section>
        </q-card>
    </q-dialog>
</template>
