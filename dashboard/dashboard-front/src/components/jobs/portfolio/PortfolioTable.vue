<script setup lang="ts">
import { onMounted, ref, type Ref } from 'vue'
import { type QTableProps } from 'quasar'
import { toastService } from '@/services/ToastService'
import { formatTimestampIso8601 } from '@/utils/time'
import { formatDecimalNumber } from '@/utils/string'
import { apiClient } from '@/services/ApiClient'
import DeleteJobButton from '@/components/jobs/DeleteJobButton.vue'

const portfolioJobs: Ref<PortfolioJob[]> = ref([])
const visibleColumns = ref([
    'family-name', 'version', 'status', 'job-type-version', 'deployed-by', 'last-updated-ago', 'last-called-ago',
])
const pagination = ref({
    sortBy: 'family-name',
    descending: false,
    page: 1,
    rowsPerPage: 25,
})
const filter = ref('')

interface PortfolioJob {
    name: string
    version: string
    status: string
    create_time: number
    update_time: number
    id: string
    manifest?: string
    internal_name?: string
    pub_url?: string
    error?: string
    image_tag?: string
    deployed_by?: string
    last_call_time?: number
    infrastructure_target?: string
    replica_internal_names?: string[]
    job_type_version: string
    purge_score: number
    purge_reasons: string
    purge_newer_versions: number
    update_time_days_ago: number
    last_call_time_days_ago: number
}

function fetchJobs() {
    apiClient.get(`/api/v1/job/portfolio`).then(response => {
        portfolioJobs.value = response.data as PortfolioJob[]
    }).catch(err => {
        toastService.showErrorDetails(`Fetching jobs portfolio failed`, err)
    })
}

onMounted(() => {
    fetchJobs()
})

const columns: QTableProps['columns'] = [
    {
        name: 'family-name',
        label: 'Family name',
        align: 'left',
        field: (row: PortfolioJob) => row.name,
        sortable: true,
    },
    {
        name: 'version',
        label: 'Job version',
        align: 'left',
        field: (row: PortfolioJob) => row.version,
        sortable: true,
    },
    {
        name: 'status',
        label: 'Status',
        align: 'left',
        field: (row: PortfolioJob) => row.status.toUpperCase(),
        sortable: true,
    },
    {
        name: 'job-type-version',
        label: 'Job type version',
        align: 'left',
        field: (row: PortfolioJob) => row.job_type_version,
        sortable: true,
    },
    {
        name: 'deployed-by',
        label: 'Deployed by',
        align: 'left',
        field: (row: PortfolioJob) => row.deployed_by || '',
        sortable: true,
    },
    {
        name: 'last-updated-ago',
        label: 'Last updated ago [days]',
        align: 'right',
        field: (row: PortfolioJob) => formatDecimalNumber(row.update_time_days_ago),
        sortable: true,
    },
    {
        name: 'last-called-ago',
        label: 'Last called ago [days]',
        align: 'right',
        field: (row: PortfolioJob) => formatDecimalNumber(row.last_call_time_days_ago),
        sortable: true,
    },
    {
        name: 'purge-reasons',
        label: 'Purge reasons',
        align: 'left',
        field: (row: PortfolioJob) => row.purge_reasons,
        sortable: true,
    },
    {
        name: 'purge-score',
        label: 'Purge score',
        align: 'right',
        field: (row: PortfolioJob) => formatDecimalNumber(row.purge_score),
        sortable: true,
    },
    {
        name: 'newer-versions',
        label: 'Newer versions',
        align: 'right',
        field: (row: PortfolioJob) => row.purge_newer_versions,
        sortable: true,
    },
    {
        name: 'last-call-time',
        label: 'Last calll time',
        align: 'left',
        field: (row: PortfolioJob) => formatTimestampIso8601(row.last_call_time),
        sortable: true,
    },
    {
        name: 'udpate-time',
        label: 'Update time',
        align: 'left',
        field: (row: PortfolioJob) => formatTimestampIso8601(row.update_time),
        sortable: true,
    },
    {
        name: 'creation-time',
        label: 'Creation time',
        align: 'left',
        field: (row: PortfolioJob) => formatTimestampIso8601(row.create_time),
        sortable: true,
    },
    {
        name: 'infrastructure-target',
        label: 'Infrastructure target',
        align: 'left',
        field: (row: PortfolioJob) => row.infrastructure_target,
        sortable: true,
    },
    {
        name: 'actions',
        label: 'Actions',
        align: 'left',
        field: (row: PortfolioJob) => "",
        sortable: true,
    },
]

const headerTooltips: Record<string, string> = {
    'version': 'Revision of the source code of the service',
    'job-type-version': 'Revision of the language wrapper standard',
    'purge-reasons': 'Suggestions explaining why job is a candidate for removal',
    'purge-score': 'Assessed penalty points representing usability of a job. A higher value means a better candidate for removal',
}
</script>

<template>
    <q-table
      flat bordered
      :rows="portfolioJobs"
      :columns="columns"
      row-key="id"
      :visible-columns="visibleColumns"
      :pagination="pagination"
      :filter="filter"
      no-data-label="No jobs"
    >
        <template v-slot:top-left>
            <q-select
                v-model="visibleColumns"
                multiple
                outlined dense options-dense
                :display-value="$q.lang.table.columns"
                emit-value
                map-options
                :options="columns"
                option-value="name"
                options-cover
                style="min-width: 150px"
            />
            <q-input outlined dense debounce="300" v-model="filter" placeholder="Filter">
                <template v-slot:append>
                    <q-icon name="search" />
                </template>
            </q-input>
        </template>
        <template v-slot:header="props">
            <q-tr :props="props">
                <q-th
                    v-for="col in props.cols"
                    :key="col.name"
                    :props="props"
                    >
                    <span class="text-bold">
                        {{ col.label }}
                        <q-tooltip v-if="headerTooltips[col.name]">{{ headerTooltips[col.name] }}</q-tooltip>
                    </span>
                </q-th>
            </q-tr>
        </template>
        <template v-slot:body-cell-actions="props">
            <q-td :props="props">
                <DeleteJobButton :jobName="props.row.name" :jobVersion="props.row.version" @jobDeleted="fetchJobs()" />
            </q-td>
        </template>
    </q-table>
</template>
