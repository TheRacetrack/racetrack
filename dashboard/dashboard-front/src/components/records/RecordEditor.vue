<script setup lang="ts">
import {useRoute, useRouter} from "vue-router"
import { ref, onMounted } from 'vue'
import { apiClient } from '@/services/ApiClient'
import {type TableMetadataPayload, type RecordFieldsPayload} from '@/utils/api-schema'
import {toastService} from "@/services/ToastService"
import { mdiDatabase, mdiTable, mdiFileDocumentOutline } from '@quasar/extras/mdi-v7'
import {progressService} from "@/services/ProgressService"
import {leftZeroPad} from "@/utils/time";

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
        inputValues.value = Object.fromEntries(
            Object.entries(response.data.fields)
                .map(([key, value]) => [key, decodeInputValue(value, key)])
        ) as Record<string, any>
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table records`, err)
    } finally {
        loading.value = false
    }
}

function saveRecord() {
    const allowedTypes = ['str', 'str | None', 'int', 'int | None', 'float', 'float | None', 'datetime', 'datetime | None', 'bool']
    const fields = Object.fromEntries(
        Object.entries(inputValues.value)
            .filter(([key, _]) => allowedTypes.includes(tableMetadata.value.column_types[key]))
            .map(([key, value]) => [key, encodeInputValue(value, key)])
    ) as Record<string, any>
    progressService.runLoading({
        task: apiClient.put(`/api/v1/records/table/${tableName}/id/${recordId}`, {
            fields: fields,
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
        confirmQuestion: `Are you sure you want to delete this record ${tableName} / ${recordId}?`,
        onConfirm: () => {
            return apiClient.delete(`/api/v1/records/table/${tableName}/id/${recordId}`)
        },
        progressMsg: `Deleting record ${tableName} / ${recordId}…`,
        successMsg: `Record ${tableName} / ${recordId} has been deleted.`,
        errorMsg: `Failed to delete record ${tableName} / ${recordId}`,
        onSuccess: () => {
            router.push({name: 'records-table', params: {table: tableName}})
        },
    })
}

function decodeInputValue(value: any, fieldName: string): any {
    const colType = tableMetadata.value.column_types[fieldName]
    if (colType.endsWith(' | None') && (value == null || value === '')) {
        return value
    }
    if (['datetime', 'datetime | None'].includes(colType)) {
        const date = new Date(value)
        const day = leftZeroPad(date.getDate(), 2)
        const month = leftZeroPad(date.getMonth() + 1, 2)
        const year = leftZeroPad(date.getFullYear(), 4)
        const hour = leftZeroPad(date.getHours(), 2)
        const minute = leftZeroPad(date.getMinutes(), 2)
        const second = leftZeroPad(date.getSeconds(), 2)
        const millisecond = leftZeroPad(date.getMilliseconds(), 3)
        const timezoneOffset = -date.getTimezoneOffset() ?? 0
        const timezoneHours = leftZeroPad(Math.floor(Math.abs(timezoneOffset) / 60), 2)
        const timezoneMinutes = leftZeroPad(Math.abs(timezoneOffset) % 60, 2)
        const timezonePart = timezoneOffset >= 0 ? `+${timezoneHours}:${timezoneMinutes}` : `-${timezoneHours}:${timezoneMinutes}`
        return `${year}-${month}-${day}, ${hour}:${minute}:${second}.${millisecond} ${timezonePart}`
    }
    return value
}

function encodeInputValue(value: any, fieldName: string): any {
    const colType = tableMetadata.value.column_types[fieldName]
    if (colType.endsWith(' | None') && (value == null || value === '')) {
        return null
    }
    if (colType === 'str' && value == null) {
        return ''
    }
    if (['datetime', 'datetime | None'].includes(colType)) {
        const date = new Date(value)
        const day = leftZeroPad(date.getUTCDate(), 2)
        const month = leftZeroPad(date.getUTCMonth() + 1, 2)
        const year = leftZeroPad(date.getUTCFullYear(), 4)
        const hour = leftZeroPad(date.getUTCHours(), 2)
        const minute = leftZeroPad(date.getUTCMinutes(), 2)
        const second = leftZeroPad(date.getUTCSeconds(), 2)
        const millisecond = leftZeroPad(date.getUTCMilliseconds(), 3)
        return `${year}-${month}-${day}T${hour}:${minute}:${second}.${millisecond}+00:00`
    }
    return value
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
            <div v-for="fieldName in tableMetadata.all_columns" :key="fieldName">
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
                            <q-date v-model="inputValues[fieldName]" mask="YYYY-MM-DD, HH:mm:ss.SSS Z" first-day-of-week="1" today-btn />
                            <q-time v-model="inputValues[fieldName]" mask="YYYY-MM-DD, HH:mm:ss.SSS Z" color="primary" format24h with-seconds now-btn />
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
