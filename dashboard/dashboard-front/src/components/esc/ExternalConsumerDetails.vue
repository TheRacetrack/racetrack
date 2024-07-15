<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import {type EscDetails} from '@/utils/api-schema'
import {copyToClipboard} from "quasar";

const route = useRoute()
const escId = route.params.escId
const escDetails = ref<EscDetails | null>(null)

function fetchConsumerData() {
    apiClient.get<EscDetails>(`/api/v1/escs/${escId}/auth_data`)
        .then(response => {
            escDetails.value = response.data
        }).catch(err => {
            toastService.showErrorDetails(`Failed to fetch ESC details`, err)
        })
}

function copyAuthToken() {
    copyToClipboard(escDetails.value?.token || '')
        .then(() => {
            toastService.success(`Auth Token copied to clipboard.`)
        }).catch((error) => {
            toastService.error(`Failed to copy to clipboard.`)
        })
}

onMounted(() => {
    fetchConsumerData()
})
</script>

<template>
    <q-card>
        <q-card-section>
            <div class="text-h6">External Service Consumer Details</div>
        </q-card-section>

        <q-card-section>
            <q-field outlined label="ID" stack-label>
                <template v-slot:control>
                    {{ escDetails?.id }}
                </template>
            </q-field>

            <q-field outlined label="Name" stack-label>
                <template v-slot:control>
                    <div>{{ escDetails?.name }}</div>
                </template>
            </q-field>

            <q-field outlined label="Auth Token (X-Racetrack-Auth)" stack-label>
                <template v-slot:control>
                    <span class="x-monospace x-overflow-any">
                        {{ escDetails?.token }}
                    </span>
                </template>
                <template v-slot:append>
                    <q-btn round dense flat icon="content_copy" @click="copyAuthToken" />
                </template>
            </q-field>
        </q-card-section>
    </q-card>
</template>