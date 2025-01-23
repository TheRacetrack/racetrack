<script setup lang="ts">
import {useRoute, useRouter} from "vue-router"
import { ref, onMounted, type Ref } from 'vue'
import { apiClient } from '@/services/ApiClient'
import {type TableMetadataPayload, type FetchManyRecordsRequest, type FetchManyRecordsResponse, type RecordFieldsPayload, type CountRecordsRequest} from '@/utils/api-schema'
import {toastService} from "@/services/ToastService"
import { mdiDatabase, mdiTable } from '@quasar/extras/mdi-v7'
import type {QTableProps} from "quasar"

const route = useRoute()
const router = useRouter()
const tableName: string = route.params.table as string
const tableMetadata = ref<TableMetadataPayload | null>(null)
const recordCount = ref<number | null>(null)
const filters = ref<Record<string, any>>({})
const pageRows = ref<RecordFieldsPayload[]>([])
const loading = ref(true)

interface QTablePagination {
    sortBy?: string | null
    descending?: boolean
    page?: number
    rowsPerPage?: number
    rowsNumber?: number
}

const pagination: Ref<QTablePagination> = ref({
    sortBy: null,
    descending: false,
    page: 1,
    rowsPerPage: 50,
    rowsNumber: undefined,
})
const tableFilter = ref('')
const visibleColumns = ref<string[]>([])
const columnProps = ref<QTableProps['columns']>([])
const selectedItems = ref<RecordFieldsPayload[]>([])

async function fetchTableMetadata(): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.get<TableMetadataPayload>(`/api/v1/records/table/${tableName}/metadata`)
        tableMetadata.value = response.data
        visibleColumns.value = response.data.main_columns
        columnProps.value = response.data.all_columns.map(col => ({
            name: col,
            label: col,
            align: 'left',
            field: (row: RecordFieldsPayload) => row.fields[col],
            sortable: true,
        }))
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table data`, err)
    } finally {
        loading.value = false
    }
}

async function fetchRecordsCount(): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.post<number>(`/api/v1/records/table/${tableName}/count`, {
            filters: filters.value,
        } as CountRecordsRequest)
        recordCount.value = response.data
        pagination.value.rowsNumber = recordCount.value
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch records count`, err)
    } finally {
        loading.value = false
    }
}

async function fetchRecords(): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.post<FetchManyRecordsResponse>(`/api/v1/records/table/${tableName}/list`, {
            offset: 0,
            limit: 30,
            order_by: null,
            filters: filters.value,
            columns: tableMetadata.value?.all_columns ?? [],
        } as FetchManyRecordsRequest)
        pageRows.value = response.data.records
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table records`, err)
    } finally {
        loading.value = false
    }
}

function onRowClick(event: Event, row: RecordFieldsPayload, index: number) {
    if (!tableMetadata.value) return
    const rowId = row.fields[tableMetadata.value.primary_key_column]
    router.push({name: 'records-table-record', params: {table: tableName, recordId: rowId}})
}

function createRecord() {
    router.push({name: 'records-table-creator', params: {table: tableName}})
}

async function onPageFetch(_: any) {
    await fetchRecordsCount()
    await fetchRecords()
}

onMounted(async () => {
    await fetchTableMetadata()
    await fetchRecordsCount()
    await fetchRecords()
})
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-md">
            <q-breadcrumbs>
              <q-breadcrumbs-el label="Tables Index" :icon="mdiDatabase" :to="{name: 'records-tables-index'}" />
              <q-breadcrumbs-el :label="tableMetadata?.plural_name ?? ''" :icon="mdiTable" :to="{name: 'records-table', params: {table: tableName}}" />
            </q-breadcrumbs>
        </q-card-section>

        <q-table
          flat bordered
          separator="cell"
          :rows="pageRows"
          :row-key="tableMetadata?.primary_key_column"
          :columns="columnProps"
          :visible-columns="visibleColumns"
          :pagination="pagination"
          :rows-per-page-options="[2, 5, 10, 20, 50, 100, 200, 500, 0]"
          :filter="tableFilter"
          :loading="loading"
          no-data-label="No records"
          @row-click="onRowClick"
          selection="multiple"
          v-model:selected="selectedItems"
          @request="onPageFetch"
        >
            <template v-slot:header-selection="scope">
                <q-checkbox v-model="scope.selected" />
            </template>
            <template v-slot:top-left>
                <q-select
                    v-model="visibleColumns"
                    multiple
                    outlined dense options-dense
                    :display-value="$q.lang.table.columns"
                    emit-value
                    map-options
                    :options="columnProps"
                    option-value="name"
                    options-cover
                    style="min-width: 150px"
                />
                <q-input outlined dense debounce="300" v-model="tableFilter" placeholder="Filter">
                    <template v-slot:append>
                        <q-icon name="search" />
                    </template>
                </q-input>
                <q-btn color="primary" push label="Create" icon="add" @click="createRecord()" />
            </template>
            <template v-slot:header-cell="props">
                <q-th :props="props" :key="props.col.label">
                    <span class="text-bold">{{ props.col.label }}</span>
                </q-th>
            </template>
        </q-table>

        <q-card-section>
            <div>
                Number of all records: {{recordCount}}
            </div>
        </q-card-section>
    </q-card>
</template>