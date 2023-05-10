<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, type Ref } from 'vue'
import { QTree } from 'quasar'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import { type JobData } from '@/utils/api-schema'
import JobDetails from '@/components/jobs/JobDetails.vue'
import JobStatus from '@/components/jobs/JobStatus.vue'

enum JobOrder {
    ByLatestFamily,
    ByLatestJob,
    ByName,
}

const jobsData: Ref<JobData[]> = ref([])
const jobsQTreeRef: Ref<QTree | null> = ref(null)
const splitterModel: Ref<number> = ref(25)
const treeFilter: Ref<string> = ref('')
const jobsByKey: Ref<Map<string, JobData>> = ref(new Map())
const jobsTree: Ref<any[]> = ref([])
const currentJob: Ref<JobData | null> = ref(null)
const jobsCount: Ref<number> = computed(() => jobsData.value?.length || 0)
const selectedNodeKey: Ref<string | null> = ref(null)
const jobOrder: Ref<JobOrder> = ref(JobOrder.ByName)
const loadingTree = ref(true)

function fetchJobs() {
    loadingTree.value = true
    apiClient.get(`/api/v1/job`).then(response => {
        jobsData.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch the jobs`, err)
    }).finally(() => {
        loadingTree.value = false
    })
}

function populateJobsData() {
    const sortedJobs: JobData[] = [...jobsData.value]
    if (jobOrder.value === JobOrder.ByLatestFamily || jobOrder.value === JobOrder.ByLatestJob) {
        sortedJobs.sort((a, b) => {
            return b.update_time - a.update_time
        })
    } else if (jobOrder.value === JobOrder.ByName) {
        sortedJobs.sort((a, b) => {
            return a.name.toLowerCase().localeCompare(b.name.toLowerCase())
                || compareVersions(b.version, a.version)
        })
    }

    jobsByKey.value = jobsData.value?.reduce((map, job) => {
        map.set(`job:${job.name}-${job.version}`, job)
        return map
    }, new Map())

    let leafs = []
    if (jobOrder.value === JobOrder.ByLatestJob) {
        for (let job of sortedJobs) {
            leafs.push({
                label: `${job.name} v${job.version}`,
                key: `job:${job.name}-${job.version}`,
                type: 'job',
            })
        }

    } else {
        const jobFamilies = new Map<string, JobData[]>()
        sortedJobs.forEach(job => {
            const family = jobFamilies.get(job.name)
            if (family) {
                family.push(job)
            } else {
                jobFamilies.set(job.name, [job])
            }
        })

        for (let [familyName, jobs] of jobFamilies) {
            leafs.push({
                label: familyName,
                key: `job-family:${familyName}`,
                type: 'job-family',
                children: jobs.map(job => ({
                    label: `v${job.version}`,
                    key: `job:${job.name}-${job.version}`,
                    type: 'job',
                }))
            })
        }
    }
    jobsTree.value = leafs
}

function selectJobNode(key: string | null) {
    if (key) {
        const job = getJobByKey(key)
        if (job) {
            currentJob.value = job
        } else {
            const isExpanded = jobsQTreeRef.value?.isExpanded(key)
            jobsQTreeRef.value?.setExpanded(key, !isExpanded)
            selectedNodeKey.value = null
        }
    }
}

function compareVersions(a: string, b: string): number {
    const regexp = /^(\d+)\.(\d+)\.(\d+)(.*)$/g
    const matchesA = regexp.exec(a)
    regexp.lastIndex = 0
    const matchesB = regexp.exec(b)
    if (!matchesA || !matchesB) {
        return 0
    }
    return parseInt(matchesA[1]) - parseInt(matchesB[1])
        || parseInt(matchesA[2]) - parseInt(matchesB[2])
        || parseInt(matchesA[3]) - parseInt(matchesB[3])
        || matchesA[4].localeCompare(matchesB[4])
}

function getJobByKey(key: string): JobData | null {
    return jobsByKey.value?.get(key) || null
}

function filterJobsTree(node: any, filter: string): boolean {
    const keywords: string[] = filter.toLowerCase().split(' ')
    const job = getJobByKey(node.key)
    if (!job)
        return false
    if (keywords.length === 0)
        return true
    return keywords.every(keyword => filterJobByKeyword(job, keyword))
}

function filterJobByKeyword(job: JobData, keyword: string): boolean {
    if (job.name.toLowerCase().includes(keyword))
        return true
    if (job.version.toLowerCase().includes(keyword))
        return true
    if (job.deployed_by?.toLowerCase().includes(keyword))
        return true
    if (job.status.toLowerCase().includes(keyword))
        return true
    if (job.job_type_version?.toLowerCase().includes(keyword))
        return true
    if (job.manifest?.['owner_email']?.toLowerCase().includes(keyword))
        return true
    return false
}

function expandAll() {
    jobsQTreeRef.value?.expandAll()
}

function collapseAll() {
    jobsQTreeRef.value?.collapseAll()
}

function changeJobOrder(order: JobOrder) {
    jobOrder.value = order
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

                    <div class="q-mr-sm" style="overflow-x: auto;">
                        <q-input filled v-model="treeFilter" label="Filter">
                            <template v-if="treeFilter" v-slot:append>
                                <q-icon name="cancel" @click.stop.prevent="treeFilter = ''" class="cursor-pointer" />
                            </template>
                        </q-input>

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
                                <q-item clickable v-close-popup @click="changeJobOrder(JobOrder.ByLatestFamily)">
                                    <q-item-section>
                                        <q-item-label>Sort by latest family</q-item-label>
                                    </q-item-section>
                                </q-item>
                                <q-item clickable v-close-popup @click="changeJobOrder(JobOrder.ByLatestJob)">
                                    <q-item-section>
                                        <q-item-label>Sort by latest job</q-item-label>
                                    </q-item-section>
                                </q-item>
                                <q-item clickable v-close-popup @click="changeJobOrder(JobOrder.ByName)">
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
                            @update:selected="(key: string | null) => selectJobNode(key)"
                            >
                            <template v-slot:default-header="prop">
                                <template v-if="prop.node.type == 'job'">
                                    <div class="text-no-wrap">
                                        {{ prop.node.label }}
                                        <JobStatus :status="getJobByKey(prop.node.key)?.status" short />
                                    </div>
                                </template>
                                <template v-else>
                                    {{ prop.node.label }}
                                </template>
                            </template>
                        </q-tree>
                    </div>

                    <q-inner-loading :showing="loadingTree">
                        <q-spinner-gears size="50px" color="primary" />
                    </q-inner-loading>

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
