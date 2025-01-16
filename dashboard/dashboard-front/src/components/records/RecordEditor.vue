<script setup lang="ts">
import {useRoute, useRouter} from "vue-router"
import { ref, onMounted } from 'vue'
import { apiClient } from '@/services/ApiClient'
import {type TableMetadataPayload, type RecordFieldsPayload} from '@/utils/api-schema'
import {toastService} from "@/services/ToastService"
import { mdiDatabase, mdiTable, mdiFileDocumentOutline } from '@quasar/extras/mdi-v7'
import {progressService} from "@/services/ProgressService"

const route = useRoute()
const router = useRouter()
const tableName: string = route.params.table as string
const recordId: string = route.params.recordId as string
const tableMetadata = ref<TableMetadataPayload>({
    class_name: '',
    table_name: '',
    plural_name: '',
    primary_key_column: '',
    main_columns: [],
    all_columns: [],
    column_types: {},
})
const recordData = ref<RecordFieldsPayload | null>(null)
const loading = ref(true)
const submitting = ref(false)
const inputValues = ref<Record<string, any>>({})

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
        inputValues.value = response.data.fields
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table records`, err)
    } finally {
        loading.value = false
    }
}

function saveRecord() {
    progressService.runLoading({
        task: apiClient.put(`/api/v1/records/table/${tableName}/id/${recordId}`, {
            fields: inputValues.value,
        }),
        loadingState: submitting,
        progressMsg: `Saving record…`,
        successMsg: `Record saved.`,
        errorMsg: `Failed to save a record`,
        onSuccess: () => {},
    })
}

function deleteRecord() {
    progressService.confirmWithLoading({
        confirmQuestion: `Are you sure you want to delete this record ${tableName}/${recordId}?`,
        onConfirm: () => {
            return apiClient.delete(`/api/v1/records/table/${tableName}/id/${recordId}`)
        },
        progressMsg: `Deleting record ${tableName}/${recordId}…`,
        successMsg: `Record ${tableName}/${recordId} has been deleted.`,
        errorMsg: `Failed to delete record ${tableName}/${recordId}`,
        onSuccess: () => {
            router.push({name: 'records-table', params: {table: tableName}})
        },
    })
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
              <q-breadcrumbs-el :label="tableMetadata.plural_name" :icon="mdiTable" :to="{name: 'records-table', params: {table: tableName}}" />
              <q-breadcrumbs-el :label="recordId" :icon="mdiFileDocumentOutline" :to="{name: 'records-table-record', params: {table: tableName, recordId: recordId}}" />
            </q-breadcrumbs>
        </q-card-section>

        <q-card-section class="q-pa-md">
            <div v-for="(fieldValue, fieldName) in recordData?.fields" :key="fieldName">
                <template v-if="['str', 'str | None'].includes(tableMetadata.column_types[fieldName])">
                    <q-input
                        outlined autogrow
                        v-model="inputValues[fieldName]"
                        :label="fieldName"
                        type="text"
                        >
                        <template v-slot:append>
                            <q-icon v-if="tableMetadata.column_types[fieldName].endsWith(' | None')"
                                name="cancel" @click.stop.prevent="inputValues[fieldName] = null" class="cursor-pointer" />
                        </template>
                    </q-input>
                </template>
                <template v-else-if="['int', 'int | None', 'float', 'float | None'].includes(tableMetadata.column_types[fieldName])">
                    <q-input
                        outlined
                        v-model="inputValues[fieldName]"
                        :label="fieldName"
                        type="number"
                        >
                        <template v-slot:append>
                            <q-icon v-if="tableMetadata.column_types[fieldName].endsWith(' | None')"
                                name="cancel" @click.stop.prevent="inputValues[fieldName] = null" class="cursor-pointer" />
                        </template>
                    </q-input>
                </template>
                <template v-else-if="['datetime', 'datetime | None'].includes(tableMetadata.column_types[fieldName])">
                    <q-input outlined :label="fieldName" v-model="inputValues[fieldName]">
                      <template v-slot:append>
                            <q-icon v-if="tableMetadata.column_types[fieldName].endsWith(' | None')"
                                name="cancel" @click.stop.prevent="inputValues[fieldName] = null" class="cursor-pointer" />
                        <q-icon name="event" class="cursor-pointer">
                          <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                            <q-date v-model="inputValues[fieldName]" mask="YYYY-MM-DD HH:mm:ss" first-day-of-week="1" today-btn />
                            <q-time v-model="inputValues[fieldName]" mask="YYYY-MM-DD HH:mm:ss" color="primary" format24h with-seconds now-btn />
                            <div class="row items-center justify-end">
                              <q-btn v-close-popup label="Close" color="primary" flat />
                            </div>
                          </q-popup-proxy>
                        </q-icon>
                      </template>
                    </q-input>
                </template>
                <template v-else-if="tableMetadata.column_types[fieldName] == 'bool'">
                    <q-checkbox v-model="inputValues[fieldName]" :label="fieldName" />
                </template>
                <template v-else>
                    <q-input
                        outlined readonly
                        :label="fieldName"
                        type="text"
                        model-value="[Unreadable data]" />
                </template>
            </div>
        </q-card-section>
        <q-card-actions>
            <q-btn color="primary" push label="Save" icon="save" :loading="submitting" @click="saveRecord()" />
            <q-btn color="negative" push label="Delete" icon="delete" :loading="submitting" @click="deleteRecord()" />
        </q-card-actions>

        <q-inner-loading :showing="loading">
            <q-spinner-gears size="50px" color="primary" />
        </q-inner-loading>
    </q-card>
</template>
