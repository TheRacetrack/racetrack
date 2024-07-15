<script setup lang="ts">
import { ref, type Ref } from 'vue'
import { progressService } from '@/services/ProgressService'
import { apiClient } from '@/services/ApiClient'

const dialogOpen = ref(false)
const loading = ref(false)
const escName: Ref<string> = ref('')

function openDialog() {
    dialogOpen.value = true
}

function createConsumer() {
    progressService.runLoading({
        task: apiClient.post(`/api/v1/escs`, {
            'name': escName.value,
        }),
        loadingState: loading,
        progressMsg: `Creating ESC...`,
        successMsg: `ESC created.`,
        errorMsg: `Failed to create ESC`,
        onSuccess: () => {
            dialogOpen.value = false
            emit('escCreated', null)
        },
    })
}

const emit = defineEmits(['escCreated'])

defineExpose({
    openDialog,
})
</script>

<template>
    <q-dialog v-model="dialogOpen">
        <q-card>
            <q-card-section>
                <div class="text-h6">Create a new External Service Consumer</div>
            </q-card-section>
            <q-card-section>
                <div>
                    <q-input
                        outlined
                        v-model="escName"
                        label="Name"
                        />
                </div>
                <div class="row q-pt-sm">
                    <q-space />
                    <q-btn flat color="white" text-color="black" label="Cancel" v-close-popup />
                    <q-btn color="primary" push label="Create" icon="add"
                        @click="createConsumer" :loading="loading" />
                </div>
            </q-card-section>
        </q-card>
    </q-dialog>
</template>
