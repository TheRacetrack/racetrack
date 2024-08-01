<script setup lang="ts">
import { ref, type Ref } from 'vue'
import { progressService } from '@/services/ProgressService'
import { apiClient } from '@/services/ApiClient'

const dialogOpen = ref(false)
const loading = ref(false)
const escId: Ref<string> = ref('')
const expiryDate: Ref<string | null> = ref(null)

function openDialog(_escId: string) {
    escId.value = _escId
    dialogOpen.value = true
}

function confirmGeneratingToken() {
    progressService.runLoading({
        task: apiClient.post(`/api/v1/escs/${escId.value}/auth_token`, {
            'expiry_time': getExpiryTimestamp(),
        }),
        loadingState: loading,
        progressMsg: `Generating new auth token…`,
        successMsg: `Auth token generated.`,
        errorMsg: `Failed to generate Auth Token`,
        onSuccess: () => {
            dialogOpen.value = false
            emit('onTokenGenerated', null)
        },
    })
}

function clearExpiryDate() {
    expiryDate.value = null
}

function getExpiryTimestamp(): number | null {
    if (expiryDate.value == null) return null
    const date = new Date(expiryDate.value)
    return date.getTime() / 1000
}

const emit = defineEmits(['onTokenGenerated'])

defineExpose({
    openDialog,
})
</script>

<template>
    <q-dialog v-model="dialogOpen">
        <q-card style="min-width: 25vw;">
            <q-card-section>
                <div class="text-h6">Generate a new Auth Token</div>
            </q-card-section>
            <q-card-section>
                <div>
                    <q-input outlined label="Expiration date (optional)" v-model="expiryDate">
                      <template v-slot:append>
                        <q-icon name="cancel" @click.stop.prevent="clearExpiryDate" class="cursor-pointer" />
                        <q-icon name="event" class="cursor-pointer">
                          <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                            <q-date v-model="expiryDate" mask="YYYY-MM-DD" first-day-of-week="1" minimal>
                              <div class="row items-center justify-end">
                                <q-btn v-close-popup label="Close" color="primary" flat />
                              </div>
                            </q-date>
                          </q-popup-proxy>
                        </q-icon>
                      </template>
                    </q-input>
                </div>
                <div class="row q-pt-sm">
                    <q-space />
                    <q-btn flat color="white" text-color="black" label="Cancel" v-close-popup />
                    <q-btn color="primary" push label="Generate" icon="add"
                        @click="confirmGeneratingToken" :loading="loading" />
                </div>
            </q-card-section>
        </q-card>
    </q-dialog>
</template>
