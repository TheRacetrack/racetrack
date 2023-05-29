<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch, type Ref } from 'vue'
import { QTree } from 'quasar'
import { io, Socket } from "socket.io-client"
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import { type JobData } from '@/utils/api-schema'
import JobDetails from '@/components/jobs/JobDetails.vue'
import JobStatus from '@/components/jobs/JobStatus.vue'
import { JobOrder, filterJobByKeyword, sortedJobs } from '@/utils/jobs'
import { envInfo } from '@/services/EnvironmentInfo'

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

function populateJobsTree() {
    const jobs: JobData[] = sortedJobs(jobsData.value, jobOrder.value)

    jobsByKey.value = jobsData.value?.reduce((map, job) => {
        map.set(`job:${job.name}-${job.version}`, job)
        return map
    }, new Map())

    let leafs = []
    if (jobOrder.value === JobOrder.ByLatestJob || jobOrder.value === JobOrder.ByStatus) { // flat list
        for (let job of jobs) {
            leafs.push({
                label: `${job.name} v${job.version}`,
                key: `job:${job.name}-${job.version}`,
                type: 'job',
            })
        }

    } else { // tree grouped by families
        const jobFamilies = new Map<string, JobData[]>()
        jobs.forEach(job => {
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
                childrenCount: jobs.length,
                children: jobs.map(job => ({
                    label: `v${job.version}`,
                    key: `job:${job.name}-${job.version}`,
                    type: 'job',
                }))
            })
        }
    }
    jobsTree.value = leafs

    if (selectedNodeKey.value) {
        currentJob.value = getJobByKey(selectedNodeKey.value)
    }
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

function expandAll() {
    jobsQTreeRef.value?.expandAll()
}

function collapseAll() {
    jobsQTreeRef.value?.collapseAll()
}

function updatedJobOrder() {
    localStorage.setItem('jobs.order', JSON.stringify(jobOrder.value))
    populateJobsTree()
}

watch(jobsData, () => {
    populateJobsTree()
})

watch(jobsTree, () => {
    nextTick(() => {
        jobsQTreeRef.value?.expandAll()
    })
})

watch(envInfo, () => {
    setupEventStreamClient()
})

function setupEventStreamClient() {
    if (!envInfo.lifecycle_url)
        return
    const socket: Socket = io("http://localhost:7102/", {
        path: '/lifecycle/socketio/events',
    })

    socket.on("connect", () => {
        console.log(`connected to live events stream: ${socket.id}`)
        socket.on("broadcast_event", (data) => {
            console.log('live event received:', data)
            fetchJobs()
        })
    })

    socket.on("disconnect", () => {
        console.log('disconnected')
    })
}

onMounted(() => {
    const storedOrder = localStorage.getItem('jobs.order')
    if (storedOrder) {
        try {
            jobOrder.value = JSON.parse(storedOrder) as JobOrder
        } catch(e) {
            console.error(e)
        }
    }

    fetchJobs()
    setupEventStreamClient()
})
</script>
<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <div class="text-h6">Jobs
                <q-badge outline color="grey">{{jobsCount}}</q-badge>
            </div>
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
                        <q-btn-dropdown rounded flat color="grey-7" dropdown-icon="sort" no-icon-animation>
                            <q-list>
                                <q-item>
                                    <q-radio v-model="jobOrder" :val="JobOrder.ByName" @click="updatedJobOrder()" v-close-popup
                                        label="Sort by name"/>
                                </q-item>
                                <q-item>
                                    <q-radio v-model="jobOrder" :val="JobOrder.ByLatestFamily" @click="updatedJobOrder()" v-close-popup
                                        label="Sort by latest family"/>
                                </q-item>
                                <q-item>
                                    <q-radio v-model="jobOrder" :val="JobOrder.ByLatestJob" @click="updatedJobOrder()" v-close-popup
                                        label="Sort by latest job"/>
                                </q-item>
                                <q-item>
                                    <q-radio v-model="jobOrder" :val="JobOrder.ByStatus" @click="updatedJobOrder()" v-close-popup
                                        label="Sort by status"/>
                                </q-item>
                            </q-list>
                        </q-btn-dropdown>
                        </span>

                        <q-scroll-area style="height: 64vh;" visible>
                        <q-tree
                            ref="jobsQTreeRef"
                            :nodes="jobsTree"
                            node-key="key"
                            v-model:selected="selectedNodeKey"
                            selected-color="primary"
                            default-expand-all
                            :filter="treeFilter"
                            :filter-method="filterJobsTree"
                            no-nodes-label="No jobs available"
                            no-results-label="No matching jobs found"
                            @update:selected="(key: string | null) => selectJobNode(key)"
                            >
                            <template v-slot:default-header="prop">
                                <template v-if="prop.node.type == 'job'">
                                    <div class="text-no-wrap">
                                        {{ prop.node.label }}
                                        <JobStatus :status="getJobByKey(prop.node.key)?.status" short />
                                    </div>
                                </template>
                                <template v-else-if="prop.node.type == 'job-family'">
                                    {{ prop.node.label }}
                                    &nbsp;
                                    <q-badge outline color="grey">{{prop.node.childrenCount}}</q-badge>
                                </template>
                                <template v-else>
                                    {{ prop.node.label }}
                                </template>
                            </template>
                        </q-tree>
                        </q-scroll-area>
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
