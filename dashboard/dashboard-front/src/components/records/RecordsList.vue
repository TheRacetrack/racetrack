<script setup lang="ts">
import {useRoute} from "vue-router"
import { ref, onMounted } from 'vue'
import { apiClient } from '@/services/ApiClient'
import {type TableMetadataPayload, type FetchManyRecordsRequest, type FetchManyRecordsResponse, type RecordFieldsPayload, type CountRecordsRequest} from '@/utils/api-schema'
import {toastService} from "@/services/ToastService";
import { mdiDatabase, mdiTable } from '@quasar/extras/mdi-v7'

const route = useRoute()
const tableName: string = route.params.table as string
const tableMetadata = ref<TableMetadataPayload | null>(null)
const recordCount = ref<number | null>(null)
const loading = ref(true)

async function fetchTableMetadata(): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.get<TableMetadataPayload>(`/api/v1/records/table/${tableName}/metadata`)
        tableMetadata.value = response.data
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table data`, err)
    } finally {
        loading.value = false
    }
}

async function fetchRecords(): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.post<number>(`/api/v1/records/table/${tableName}/count`, {
            filters: null,
        })
        recordCount.value = response.data
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table data`, err)
    } finally {
        loading.value = false
    }
}

onMounted(async () => {
    await fetchTableMetadata()
    await fetchRecords()
})
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <q-breadcrumbs>
              <q-breadcrumbs-el label="Tables Index" :icon="mdiDatabase" :to="{name: 'records-tables-index'}" />
              <q-breadcrumbs-el :label="tableMetadata?.plural_name ?? ''" :icon="mdiTable" :to="{name: 'records-table', params: {table: tableName}}" />
            </q-breadcrumbs>
        </q-card-section>

        <q-card-section>
            <div>
                Number of records: {{recordCount}}
            </div>

            <q-inner-loading :showing="loading">
                <q-spinner-gears size="50px" color="primary" />
            </q-inner-loading>
        </q-card-section>
    </q-card>
</template>