<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { apiClient } from '@/services/ApiClient'
import {type TableMetadataPayload} from '@/utils/api-schema'
import {toastService} from "@/services/ToastService"
import { mdiDatabase, mdiTable } from '@quasar/extras/mdi-v7'

const tablesMetadata = ref<TableMetadataPayload[]>([])
const loading = ref(true)

function fetchTables() {
    loading.value = true
    apiClient.get<TableMetadataPayload[]>(`/api/v1/records/tables`)
        .then(response => {
            tablesMetadata.value = response.data.sort((a, b) => a.plural_name.localeCompare(b.plural_name))
        }).catch(err => {
            toastService.showErrorDetails(`Failed to fetch tables metadata`, err)
        }).finally(() => {
            loading.value = false
        })
}

onMounted(() => {
    fetchTables()
})
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <q-breadcrumbs>
              <q-breadcrumbs-el label="Tables Index" :icon="mdiDatabase" :to="{name: 'records-tables-index'}" />
            </q-breadcrumbs>
        </q-card-section>

        <q-card-section>
            <q-list bordered separator class="rounded-borders">

                <q-item clickable v-ripple
                        v-for="tableMetadata in tablesMetadata"
                        :to="{name: 'records-table', params: {table: tableMetadata.table_name}}">

                    <q-item-section avatar>
                        <q-icon :name="mdiTable" />
                    </q-item-section>

                    <q-item-section>
                        <q-item-label>{{tableMetadata.plural_name}}</q-item-label>
                        <q-item-label caption>{{tableMetadata.table_name}}</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
            <q-inner-loading :showing="loading">
                <q-spinner-gears size="50px" color="primary" />
            </q-inner-loading>
        </q-card-section>
    </q-card>
</template>