<script setup lang="ts">
import {useRoute, useRouter} from "vue-router"
import { ref, onMounted, type Ref } from 'vue'
import { apiClient } from '@/services/ApiClient'
import {type TableMetadataPayload, type FetchManyRecordsRequest, type FetchManyRecordsResponse, type RecordFieldsPayload, type CountRecordsRequest} from '@/utils/api-schema'
import {toastService} from "@/services/ToastService"
import { mdiDatabase, mdiTable } from '@quasar/extras/mdi-v7'
import type {QTableProps} from "quasar"
import {progressService} from "@/services/ProgressService"

const route = useRoute()
const router = useRouter()
const tableName: string = route.params.table as string
const tableMetadata = ref<TableMetadataPayload>({
    class_name: '',
    table_name: '',
    plural_name: '',
    primary_key_column: '',
    main_columns: [],
    all_columns: [],
    column_types: {},
})
const recordCount = ref<number | null>(null)
const filters = ref<Record<string, any>>({})
const pageRows = ref<TableRow[]>([])
const loading = ref(true)

interface TableRow {
    key: string | number
    fields: Record<string, any>
}

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
const selectedRows = ref<TableRow[]>([])

async function fetchTableMetadata(): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.get<TableMetadataPayload>(`/api/v1/records/table/${tableName}/metadata`)
        tableMetadata.value = response.data
        columnProps.value = response.data.all_columns.map(col => ({
            name: col,
            label: col,
            align: 'left',
            field: (row: TableRow) => row.fields[col],
            sortable: true,
        }))
        visibleColumns.value = response.data.main_columns
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
        pagination.value.rowsNumber = response.data
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch records count`, err)
    } finally {
        loading.value = false
    }
}

async function fetchRecords(): Promise<void> {
    loading.value = true
    try {
        const rowsPerPage = pagination.value?.rowsPerPage ?? 50
        const pageIndex = (pagination.value?.page ?? 1) - 1
        const offset = pageIndex * rowsPerPage
        let response = await apiClient.post<FetchManyRecordsResponse>(`/api/v1/records/table/${tableName}/list`, {
            offset: offset,
            limit: rowsPerPage,
            order_by: evaluateOrderBy(),
            filters: filters.value,
            columns: tableMetadata.value.all_columns ?? [],
        } as FetchManyRecordsRequest)
        pageRows.value = response.data.records.map((record: RecordFieldsPayload) => ({
            key: record.fields[tableMetadata.value.primary_key_column],
            fields: record.fields,
        }))
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table records`, err)
    } finally {
        loading.value = false
    }
}

function evaluateOrderBy(): string | null {
    if (!tableMetadata.value) return null
    if (!pagination.value.sortBy) return null
    const column = pagination.value.sortBy
    return pagination.value.descending ? `-${column}` : column
}

function onRowClick(event: Event, row: TableRow, index: number) {
    if (!tableMetadata.value) return
    const recordId = String(row.key)
    router.push({name: 'records-table-record', params: {table: tableName, recordId: recordId}})
}

function createRecord() {
    router.push({name: 'records-table-creator', params: {table: tableName}})
}

async function onPageFetch(props: any) {
    pagination.value.page = props.page
    pagination.value.rowsPerPage = props.rowsPerPage
    await fetchRecords()
}

function humanReadableColumn(column: string): string {
    return column
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
}

function deleteSelectedRecords() {
    const selectedIds: string[] = selectedRows.value.map(row => String(row.key))
    if (selectedIds.length == 0) return toastService.error('No records selected')
    progressService.confirmWithLoading({
        confirmQuestion: `Are you sure you want to delete ${selectedIds.length} selected records (${selectedIds}) from table ${tableName}?`,
        onConfirm: () => {
            return apiClient.delete(`/api/v1/records/table/${tableName}/many`, {
                record_ids: selectedIds,
            })
        },
        progressMsg: `Deleting ${selectedIds.length} selected records…`,
        successMsg: `${selectedIds.length} records have been deleted.`,
        errorMsg: `Failed to delete records`,
        onSuccess: async () => {
            await fetchRecordsCount()
            await fetchRecords()
        },
        onFinalize: () => {
            selectedRows.value = []
        },
    })
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
          flat bordered separator="cell"
          :rows="pageRows"
          row-key="key"
          :columns="columnProps"
          :visible-columns="visibleColumns"
          :pagination="pagination"
          :rows-per-page-options="[5, 10, 20, 50, 100, 200, 500, 0]"
          :filter="tableFilter"
          :loading="loading"
          no-data-label="No records"
          @row-click="onRowClick"
          selection="multiple"
          v-model:selected="selectedRows"
          @request="onPageFetch"
        >
            <template v-slot:header-selection="scope">
                <q-checkbox v-model="scope.selected" />
            </template>
            <template v-slot:body-selection="scope">
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
            </template>
            <template v-slot:top-right>
                <q-btn color="primary" push label="Create" icon="add" @click="createRecord()" />
                <q-btn color="negative" push label="Delete" icon="delete" @click="deleteSelectedRecords()" />
            </template>
            <template v-slot:header-cell="props">
                <q-th :props="props" :key="props.col.label">
                    <span class="text-bold">{{ humanReadableColumn(props.col.label) }}</span>
                </q-th>
            </template>
        </q-table>
    </q-card>
</template>
