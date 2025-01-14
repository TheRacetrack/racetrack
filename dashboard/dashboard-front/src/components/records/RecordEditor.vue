<script setup lang="ts">
import {useRoute} from "vue-router"
import { ref, onMounted } from 'vue'
import { apiClient } from '@/services/ApiClient'
import {type TableMetadataPayload, type RecordFieldsPayload} from '@/utils/api-schema'
import {toastService} from "@/services/ToastService"
import { mdiDatabase, mdiTable, mdiFileDocumentOutline } from '@quasar/extras/mdi-v7'

const route = useRoute()
const tableName: string = route.params.table as string
const recordId: string = route.params.recordId as string
const tableMetadata = ref<TableMetadataPayload | null>(null)
const recordData = ref<RecordFieldsPayload | null>(null)
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

async function fetchRecord(): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.get<RecordFieldsPayload>(`/api/v1/records/table/${tableName}/id/${recordId}`)
        recordData.value = response.data
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table records`, err)
    } finally {
        loading.value = false
    }
}

onMounted(async () => {
    await fetchTableMetadata()
    await fetchRecord()
})
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-md">
            <q-breadcrumbs>
              <q-breadcrumbs-el label="Tables Index" :icon="mdiDatabase" :to="{name: 'records-tables-index'}" />
              <q-breadcrumbs-el :label="tableMetadata?.plural_name ?? ''" :icon="mdiTable" :to="{name: 'records-table', params: {table: tableName}}" />
              <q-breadcrumbs-el :label="recordId" :icon="mdiFileDocumentOutline" :to="{name: 'records-table-record', params: {table: tableName, recordId: recordId}}" />
            </q-breadcrumbs>
        </q-card-section>

        <div>
            {{recordData}}
        </div>

        <q-inner-loading :showing="loading">
            <q-spinner-gears size="50px" color="primary" />
        </q-inner-loading>
    </q-card>
</template>