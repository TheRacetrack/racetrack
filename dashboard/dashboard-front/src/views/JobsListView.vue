<script setup lang="ts">
import { nextTick, onMounted, ref, watch, type Ref } from 'vue'
import { QTree } from 'quasar'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'

const jobsData: Ref<JobData[]> = ref([])
const jobsQTreeRef: Ref<QTree | null> = ref(null)
const splitterModel: Ref<number> = ref(30)
const treeFilter: Ref<string> = ref('')
const jobFamilies: Ref<Map<string, JobData[]>> = ref(new Map())
const jobsByKey: Ref<Map<string, JobData>> = ref(new Map())
const jobsTree: Ref<any[]> = ref([])
const selectedJob: Ref<JobData | null> = ref(null)

interface JobData {
    name: string
    version: string
    status: string
    create_time: number
    update_time: number
    id?: string
    manifest?: Map<string, any>
    internal_name?: string
    pub_url?: string
    error?: string
    image_tag?: string
    deployed_by?: string
    last_call_time?: number
    infrastructure_target?: string
    replica_internal_names: string[]
    job_type_version: string
}

function fetchJobs() {
    apiClient.get(`/api/v1/job`).then(response => {
        jobsData.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch the jobs`, err)
    })
}

function populateJobsData() {
    const newJobFamilies = new Map<string, JobData[]>()
    jobsData.value?.forEach(job => {
        const family = newJobFamilies.get(job.name)
        if (family) {
            family.push(job)
        } else {
            newJobFamilies.set(job.name, [job])
        }
    })
    jobFamilies.value = newJobFamilies

    let familyLeafs = []
    for (let [familyName, jobs] of newJobFamilies) {
        familyLeafs.push({
            label: familyName,
            key: `job-family:${familyName}`,
            children: jobs.map(job => ({
                label: `${job.name} v${job.version}`,
                key: `job:${job.name}-${job.version}`,
            }))
        })
    }

    jobsTree.value = [
        {
            label: 'Job families',
            key: 'root',
            children: familyLeafs,
        },
    ]

    jobsByKey.value = new Map()
    jobsData.value?.forEach(job => {
        jobsByKey.value?.set(`job:${job.name}-${job.version}`, job)
    })
}

function selectJobNode(key: string | null) {
    if (key != null) {
        selectedJob.value = jobsByKey.value?.get(key) as JobData | null
    } else {
        selectedJob.value = null
    }
}

watch(jobsData, () => {
    populateJobsData()
})

watch(jobsTree, () => {
    nextTick(() => {
        jobsQTreeRef.value?.expandAll()
    })
})

onMounted(() => {
    fetchJobs()
})
</script>
<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <div class="text-h6">Jobs</div>
        </q-card-section>
        
        <q-card-section>
            <q-splitter v-model="splitterModel">
                <template v-slot:before>


                    <q-input filled v-model="treeFilter" label="Filter" />

                    <q-tree
                        ref="jobsQTreeRef"
                        :nodes="jobsTree"
                        node-key="key"
                        selected-color="primary"
                        default-expand-all
                        accordion
                        :filter="treeFilter"
                        >
                        <template v-slot:default-header="prop">
                            <div @click="selectJobNode(prop.node.key)">{{ prop.node.label }}</div>
                        </template>
                    </q-tree>

                </template>
                <template v-slot:after>

                    <p>Job data</p>

                    <p>Name: {{ selectedJob?.name }}</p>
                    <p>Version: {{ selectedJob?.version }}</p>
                    <p>Status: {{ selectedJob?.status }}</p>
                    <p>Created: {{ selectedJob?.create_time }}</p>
                    <p>Updated: {{ selectedJob?.update_time }}</p>
                    <p>Pub URL: {{ selectedJob?.pub_url }}</p>
                    <p>Error: {{ selectedJob?.error }}</p>
                    <p>Deployed by: {{ selectedJob?.deployed_by }}</p>
                    <p>Last call time: {{ selectedJob?.last_call_time }}</p>
                    <p>Infrastructure target: {{ selectedJob?.infrastructure_target }}</p>
                    <p>Job type version: {{ selectedJob?.job_type_version }}</p>
                    <p>Manifest: {{ selectedJob?.manifest }}</p>
                    
                </template>
            </q-splitter>
        </q-card-section>
    </q-card>
</template>
