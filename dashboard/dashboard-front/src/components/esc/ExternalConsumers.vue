<script setup lang="ts">
import {onMounted, ref} from 'vue'
import {toastService} from '@/services/ToastService'
import {apiClient} from '@/services/ApiClient'
import {type EscDto} from '@/utils/api-schema'
import {mdiAccountNetwork} from "@quasar/extras/mdi-v7";

const consumersData = ref<EscDto[]>([])
const loading = ref(true)

function fetchConsumersData() {
    loading.value = true
    apiClient.get<EscDto[]>(`/api/v1/escs`)
        .then(response => {
            consumersData.value = response.data
        }).catch(err => {
            toastService.showErrorDetails(`Failed to fetch external service consumers`, err)
        }).finally(() => {
            loading.value = false
        })
}

onMounted(() => {
    fetchConsumersData()
})
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <span class="text-h6">
                External Service Consumers
            </span>
        </q-card-section>

        <q-card-section class="q-pb-none">
            <div class="full-width row wrap justify-end">
                <q-btn color="primary" push label="Create a new ESC" icon="add" :to="{name: 'deploy-job'}" />
            </div>
        </q-card-section>

        <q-card-section>
            <q-list bordered separator class="rounded-borders">

                <q-item v-if="!consumersData.length" class="text-grey-6">(empty)</q-item>

                <q-item clickable v-ripple
                        v-for="item in consumersData"
                        :to="{name: 'esc-details', params: {escId: item.id}}">

                    <q-item-section avatar>
                        <q-icon :name="mdiAccountNetwork" />
                    </q-item-section>

                    <q-item-section>
                        <q-item-label>{{item.name}}</q-item-label>
                        <q-item-label caption>{{item.id}}</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
            <q-inner-loading :showing="loading">
                <q-spinner-gears size="50px" color="primary" />
            </q-inner-loading>
        </q-card-section>

    </q-card>
</template>