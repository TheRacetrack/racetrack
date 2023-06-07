<script setup lang="ts">
import { computed, onMounted, onUpdated, ref, type Ref } from 'vue'
import { toastService } from '@/services/ToastService'
import { formatTimestampIso8601 } from '@/utils/time'
import { formatDecimalNumber } from '@/utils/string'
import { apiClient } from '@/services/ApiClient'
import DeleteJobButton from '@/components/jobs/DeleteJobButton.vue'

const portfolioJobs: Ref<PortfolioJob[]> = ref([])

const portfolioRows: Ref<PortfolioRow[]> = computed(() => {
    return portfolioJobs.value.map(job => (
        job as PortfolioRow
    ))
})

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

interface PortfolioRow {
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

// see https://github.com/koalyptus/TableFilter/wiki/1.0-Configuration
const tfConfig = {
    base_path: '/dashboard/ui/assets/tablefilter/',
    paging: {
        results_per_page: ['Rows: ', [10, 25, 50, 100]]
    },
    auto_filter: { delay: 500 }, // Delay for automatic filtering (milliseconds)
    state: { // Enable state persistence
        types: ['local_storage'], // Possible values: 'local_storage' 'hash' or 'cookie'  
        filters: true, // Persist filters values, enabled by default  
        columns_visibility: true, // Persist columns visibility  
        filters_visibility: true, // Persist filters row visibility  
    },
    alternate_rows: true,
    rows_counter: true,
    toolbar: true,
    btn_reset: {
        text: 'Clear'
    },
    status_bar: true,
    col_types: [
        'string', // 0. family name
        'string', // 1. version
        'string', // 2. status
        'string', // 3. job type version
        'string', // 4. deployed by
        'number', // 5. last updated ago
        'number', // 6. last called ago
        'string', // 7. purge reasons
        'number', // 8. purge score
        'number', // 9. newer versions
        { type: 'date' }, // 10. last call time
        { type: 'date' }, // 11. update time
        { type: 'date' }, // 12. creation time
        'string', // 13. infrastructure target
        'none', // 14. actions
    ],
    col_12: 'none',
    no_results_message: {
        content: 'No results',
    },
    extensions: [{
        name: 'colsVisibility',
        at_start: [6, 7, 8, 9, 10, 11, 12, 13, 14],
        text: 'Columns: ',
        enable_tick_all: true,
        tick_to_hide: false,
    }, {
        name: 'sort'
    }],
}

const tableRef: Ref<HTMLElement | null> = ref(null)
let tf: any = null

onMounted(() => {
    fetchJobs()
    // @ts-ignore
    tf = new TableFilter(tableRef.value, tfConfig)
})

onUpdated(() => {
    tf.init()
})


const columns = [
    {
        name: 'family-name',
        label: 'Family name',
        align: 'left',
        field: (row: PortfolioRow) => row.name,
        sortable: true,
    },
    {
        name: 'version',
        label: 'Job version',
        align: 'left',
        field: (row: PortfolioRow) => row.version,
        sortable: true,
    },
    {
        name: 'status',
        label: 'Status',
        align: 'left',
        field: (row: PortfolioRow) => row.status.toUpperCase(),
        sortable: true,
    },
    {
        name: 'job-type-version',
        label: 'Job type version',
        align: 'left',
        field: (row: PortfolioRow) => row.job_type_version,
        sortable: true,
    },
    {
        name: 'deployed-by',
        label: 'Deployed by',
        align: 'left',
        field: (row: PortfolioRow) => row.deployed_by || '',
        sortable: true,
    },
    {
        name: 'last-updated-ago',
        label: 'Last updated ago [days]',
        align: 'left',
        field: (row: PortfolioRow) => formatDecimalNumber(row.update_time_days_ago),
        sortable: true,
    },
    {
        name: 'last-called-ago',
        label: 'Last called ago [days]',
        align: 'left',
        field: (row: PortfolioRow) => formatDecimalNumber(row.last_call_time_days_ago),
        sortable: true,
    },
    {
        name: 'purge-reasons',
        label: 'Purge reasons',
        align: 'left',
        field: (row: PortfolioRow) => row.purge_reasons,
        sortable: true,
    },
    {
        name: 'purge-score',
        label: 'Purge score',
        align: 'left',
        field: (row: PortfolioRow) => formatDecimalNumber(row.purge_score),
        sortable: true,
    },
    {
        name: 'newer-versions',
        label: 'Newer versions',
        align: 'left',
        field: (row: PortfolioRow) => row.purge_newer_versions,
        sortable: true,
    },
    {
        name: 'last-call-time',
        label: 'Last calll time',
        align: 'left',
        field: (row: PortfolioRow) => formatTimestampIso8601(row.last_call_time),
        sortable: true,
    },
    {
        name: 'udpate-time',
        label: 'Update time',
        align: 'left',
        field: (row: PortfolioRow) => formatTimestampIso8601(row.update_time),
        sortable: true,
    },
    {
        name: 'creation-time',
        label: 'Creation time',
        align: 'left',
        field: (row: PortfolioRow) => formatTimestampIso8601(row.create_time),
        sortable: true,
    },
    {
        name: 'infrastructure-target',
        label: 'Infrastructure target',
        align: 'left',
        field: (row: PortfolioRow) => row.infrastructure_target,
        sortable: true,
    },
    {
        name: 'actions',
        label: 'Actions',
        align: 'left',
        field: (row: PortfolioRow) => "",
        sortable: true,
    },
]

</script>

<template>
    <q-table
      flat bordered
      :rows="portfolioRows"
      :columns="columns"
      row-key="id"
      :visible-columns="visibleColumns"
      :pagination="pagination"
      no-data-label="No jobs"
    >
        <template v-slot:top-right>
            <q-input borderless dense debounce="300" v-model="filter" placeholder="Filter">
                <template v-slot:append>
                    <q-icon name="search" />
                </template>
            </q-input>
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
        </template>
        <template v-slot:header="props">
            <q-tr :props="props">
                <q-th
                    v-for="col in props.cols"
                    :key="col.name"
                    :props="props"
                    >
                    <span class="text-bold">{{ col.label }}</span>
                </q-th>
            </q-tr>
        </template>
        <template v-slot:body-cell-actions="props">
            <q-td :props="props">
                <DeleteJobButton :jobName="props.row.name" :jobVersion="props.row.version" @jobDeleted="fetchJobs()" />
            </q-td>
        </template>
    </q-table>

    <table id="table-filter-1" ref="tableRef">
        <thead>
            <tr>
                <th>Family name</th>
                <th data-bs-toggle="tooltip" data-bs-placement="bottom" title="Revision of the source code of the service">
                    Job version</th>
                <th>Status</th>
                <th data-bs-toggle="tooltip" data-bs-placement="bottom" title="Revision of the language wrapper standard">
                    Job type version</th>
                <th>Deployed by</th>
                <th>Last updated ago [days]</th>
                <th>Last called ago [days]</th>
                <th data-bs-toggle="tooltip" data-bs-placement="bottom"
                    title="Suggestions explaining why job is a candidate for removal">Purge reasons</th>
                <th data-bs-toggle="tooltip" data-bs-placement="bottom"
                    title="Assessed penalty points representing usability of a job. A higher value means a better candidate for removal">
                    Purge score</th>
                <th>Newer versions</th>
                <th>Last calll time</th>
                <th>Update time</th>
                <th>Creation time</th>
                <th>Infrastructure target</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>

            <tr v-for="job in portfolioJobs">
                <td>{{ job.name }}</td>
                <td>{{ job.version }}</td>
                <td>{{ job.status.toUpperCase() }}</td>
                <td>{{ job.job_type_version }}</td>
                <td>{{ job.deployed_by || '' }}</td>
                <td>{{ formatDecimalNumber(job.update_time_days_ago) }}</td>
                <td>{{ formatDecimalNumber(job.last_call_time_days_ago) }}</td>
                <td>{{ job.purge_reasons }}</td>
                <td>{{ formatDecimalNumber(job.purge_score) }}</td>
                <td>{{ job.purge_newer_versions }}</td>
                <td>{{ formatTimestampIso8601(job.last_call_time) }}</td>
                <td>{{ formatTimestampIso8601(job.update_time) }}</td>
                <td>{{ formatTimestampIso8601(job.create_time) }}</td>
                <td>{{ job.infrastructure_target }}</td>
                <td>
                    <DeleteJobButton :jobName="job.name" :jobVersion="job.version" @jobDeleted="fetchJobs()" />
                </td>
            </tr>

        </tbody>
    </table>
</template>
