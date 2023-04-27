<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, type Ref } from 'vue'
import { QTree } from 'quasar'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import JobDetails from '@/components/JobDetails.vue'
import JobStatus from '@/components/JobStatus.vue'
import { type JobData } from '@/utils/api-schema'

enum JobSorting {
    ByLatest,
    ByName,
}

const jobsData: Ref<JobData[]> = ref([])
const jobsQTreeRef: Ref<QTree | null> = ref(null)
const splitterModel: Ref<number> = ref(30)
const treeFilter: Ref<string> = ref('')
const jobFamilies: Ref<Map<string, JobData[]>> = ref(new Map())
const jobsByKey: Ref<Map<string, JobData>> = ref(new Map())
const jobsTree: Ref<any[]> = ref([])
const currentJob: Ref<JobData | null> = ref(null)
const jobsCount: Ref<number> = computed(() => jobsData.value?.length || 0)
const selectedNodeKey: Ref<string | null> = ref(null)
const jobSorting: Ref<JobSorting> = ref(JobSorting.ByLatest)

function fetchJobs() {
    apiClient.get(`/api/v1/job`).then(response => {
        jobsData.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch the jobs`, err)
    })
}

function populateJobsData() {
    const sortedJobs: JobData[] = jobsData.value
    if (jobSorting.value == JobSorting.ByLatest) {
        sortedJobs.sort((a, b) => {
            return b.update_time - a.update_time
        })
    } else if (jobSorting.value == JobSorting.ByName) {
        sortedJobs.sort((a, b) => {
            return a.name.toLowerCase().localeCompare(b.name.toLowerCase())
        })
    }

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
            type: 'job-family',
            children: jobs.map(job => ({
                label: `${job.name} v${job.version}`,
                key: `job:${job.name}-${job.version}`,
                type: 'job',
            }))
        })
    }

    jobsTree.value = familyLeafs

    jobsByKey.value = new Map()
    jobsData.value?.forEach(job => {
        jobsByKey.value?.set(`job:${job.name}-${job.version}`, job)
    })
}

function selectJobNode(key: string | null) {
    if (key != null) {
        const job = getJobByKey(key)
        if (job != null) {
            currentJob.value = job
        } else {
            const isExpanded = jobsQTreeRef.value?.isExpanded(key)
            jobsQTreeRef.value?.setExpanded(key, !isExpanded)
            selectedNodeKey.value = null
        }
    }
}

function getJobByKey(key: string): JobData | null {
    return jobsByKey.value?.get(key) || null
}

function filterJobsTree(node: any, filter: string): boolean {
    const filt = filter.toLowerCase()
    const job = getJobByKey(node.key)
    if (job != null) {
        if (job.name.toLowerCase().includes(filt))
            return true
        if (job.version.toLowerCase().includes(filt))
            return true
        if (job.deployed_by?.toLowerCase().includes(filt))
            return true
        if (job.status.toLowerCase().includes(filt))
            return true
        if (job.job_type_version?.toLowerCase().includes(filt))
            return true
        if (job.manifest?.['owner_email']?.toLowerCase().includes(filt))
            return true
    }
    return false
}

function expandAll() {
    jobsQTreeRef.value?.expandAll()
}

function collapseAll() {
    jobsQTreeRef.value?.collapseAll()
}

function sortByLatest() {
    jobSorting.value = JobSorting.ByLatest
    populateJobsData()
}

function sortByName() {
    jobSorting.value = JobSorting.ByName
    populateJobsData()
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
            <div class="text-h6">Jobs ({{jobsCount}})</div>
        </q-card-section>
        
        <q-card-section>
            <q-splitter v-model="splitterModel">
                <template v-slot:before>

                    <div class="q-mr-sm">
                        <q-input filled v-model="treeFilter" label="Filter" />

                        <q-btn round flat color="grey-7" icon="unfold_less" @click="collapseAll">
                            <q-tooltip>Collapse all</q-tooltip>
                        </q-btn>
                        <q-btn round flat color="grey-7" icon="unfold_more" @click="expandAll">
                            <q-tooltip>Expand all</q-tooltip>
                        </q-btn>

                        <span>
                        <q-tooltip anchor="top middle">Sort by</q-tooltip>
                        <q-btn-dropdown round flat color="grey-7" icon="sort" dropdown-icon="none">
                            <q-list>
                                <q-item clickable v-close-popup @click="sortByLatest()">
                                    <q-item-section>
                                        <q-item-label>Sort by latest</q-item-label>
                                    </q-item-section>
                                </q-item>
                                <q-item clickable v-close-popup @click="sortByName()">
                                    <q-item-section>
                                        <q-item-label>Sort by name</q-item-label>
                                    </q-item-section>
                                </q-item>
                            </q-list>
                        </q-btn-dropdown>
                        </span>

                        <q-tree
                            ref="jobsQTreeRef"
                            :nodes="jobsTree"
                            node-key="key"
                            v-model:selected="selectedNodeKey"
                            selected-color="primary"
                            default-expand-all
                            :filter="treeFilter"
                            :filter-method="filterJobsTree"
                            @update:selected="(key) => selectJobNode(key)"
                            >
                            <template v-slot:default-header="prop">
                                <template v-if="prop.node.type == 'job'">
                                    <div>
                                        {{ prop.node.label }}
                                        <JobStatus :status="getJobByKey(prop.node.key)?.status" />
                                    </div>
                                </template>
                                <template v-else>
                                    {{ prop.node.label }}
                                </template>
                            </template>
                        </q-tree>
                    </div>

                </template>
                <template v-slot:after>

                    <div class="q-ml-sm">
                        <JobDetails :currentJob="currentJob" v-if="currentJob != null"
                            @refreshJobs="fetchJobs()"/>
                    </div>
                    
                </template>
            </q-splitter>
        </q-card-section>
    </q-card>
</template>
