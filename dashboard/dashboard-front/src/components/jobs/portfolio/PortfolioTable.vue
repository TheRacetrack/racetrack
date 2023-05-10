<script setup lang="ts">
import { onMounted, onUpdated, ref, type Ref } from 'vue'
import { toastService } from '@/services/ToastService'
import { formatTimestampIso8601 } from '@/utils/time'
import { formatDecimalNumber } from '@/utils/string'
import { apiClient } from '@/services/ApiClient'
import DeleteJobButton from '@/components/jobs/DeleteJobButton.vue'

const portfolioJobs: Ref<PortfolioJob[]> = ref([])

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
</script>

<template>
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
