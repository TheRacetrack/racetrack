<script setup lang="ts">
import {useRoute, useRouter} from "vue-router"
import {ref, onMounted} from 'vue'
import {apiClient} from '@/services/ApiClient'
import {type TableMetadataPayload, type RecordFieldsPayload} from '@/utils/api-schema'
import {toastService} from "@/services/ToastService"
import {mdiDatabase, mdiTable, mdiFileDocumentOutline} from '@quasar/extras/mdi-v7'
import {progressService} from "@/services/ProgressService"
import FieldsForm from "@/components/records/FieldsForm.vue"
import {emptyTableMetadata, fetchTableMetadata, encodeInputValues, decodeInputValues, type FormFields} from "@/components/records/records"

const route = useRoute()
const router = useRouter()
const tableName: string = route.params.table as string
const recordId: string = route.params.recordId as string
const tableMetadata = ref<TableMetadataPayload>(emptyTableMetadata)
const loading = ref(true)
const submitting = ref(false)
const formFields = ref<FormFields>({
    names: [],
    values: {},
    types: {},
})

async function fetchRecord(): Promise<void> {
    loading.value = true
    try {
        let response = await apiClient.get<RecordFieldsPayload>(`/api/v1/records/table/${tableName}/id/${recordId}`)
        const formValues = decodeInputValues(response.data.fields, tableMetadata.value)
        formFields.value = {
            names: tableMetadata.value.all_columns,
            values: formValues,
            types: tableMetadata.value.column_types,
        }
    } catch (err) {
        toastService.showErrorDetails(`Failed to fetch table records`, err)
    } finally {
        loading.value = false
    }
}

function saveRecord() {
    const fields = encodeInputValues(formFields.value)
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

onMounted(async () => {
    await fetchTableMetadata(loading, tableMetadata, tableName)
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
            <FieldsForm :formFields="formFields" />
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
