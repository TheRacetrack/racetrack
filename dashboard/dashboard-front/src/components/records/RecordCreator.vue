<script setup lang="ts">
import {useRoute, useRouter} from "vue-router"
import {ref, onMounted} from 'vue'
import {apiClient} from '@/services/ApiClient'
import {type RecordFieldsPayload, type TableMetadataPayload} from '@/utils/api-schema'
import {mdiDatabase, mdiTable, mdiFileDocumentOutline} from '@quasar/extras/mdi-v7'
import {progressService} from "@/services/ProgressService"
import {emptyTableMetadata, encodeInputValues, fetchTableMetadata, type FormFields} from "@/components/records/records"
import FieldsForm from "@/components/records/FieldsForm.vue";
import {toastService} from "@/services/ToastService";

const route = useRoute()
const router = useRouter()
const tableName: string = route.params.table as string
const tableMetadata = ref<TableMetadataPayload>(emptyTableMetadata)
const loading = ref(true)
const submitting = ref(false)
const formFields = ref<FormFields>({
    names: [],
    values: {},
    types: {},
})

function createRecord() {
    const fields = encodeInputValues(formFields.value)
    progressService.runLoading({
        task: apiClient.post(`/api/v1/records/table/${tableName}`, {
            fields: fields,
        }),
        loadingState: submitting,
        progressMsg: `Creating record…`,
        errorMsg: `Failed to create a record`,
        onSuccess: (response: any) => {
            const responsePayload = response.data as RecordFieldsPayload
            const recordId = responsePayload.fields[tableMetadata.value.primary_key_column]
            toastService.success(`Record ${recordId} created.`)
            router.push({name: 'records-table', params: {table: tableName}})
        },
    })
}

onMounted(async () => {
    await fetchTableMetadata(loading, tableMetadata, tableName)
    formFields.value = {
        names: tableMetadata.value.all_columns,
        values: {},
        types: tableMetadata.value.column_types,
    }
})
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-md">
            <q-breadcrumbs>
              <q-breadcrumbs-el label="Tables Index" :icon="mdiDatabase" :to="{name: 'records-tables-index'}" />
              <q-breadcrumbs-el :label="tableMetadata.plural_name" :icon="mdiTable" :to="{name: 'records-table', params: {table: tableName}}" />
              <q-breadcrumbs-el label="New record" :icon="mdiFileDocumentOutline" />
            </q-breadcrumbs>
        </q-card-section>

        <q-card-section class="q-pa-md">
            <FieldsForm :formFields="formFields" />
        </q-card-section>
        <q-card-actions>
            <q-btn color="primary" push label="Save" icon="save" :loading="submitting" @click="createRecord()" />
        </q-card-actions>

        <q-inner-loading :showing="loading">
            <q-spinner-gears size="50px" color="primary" />
        </q-inner-loading>
    </q-card>
</template>
