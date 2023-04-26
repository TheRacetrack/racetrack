<script setup lang="ts">
import { nextTick, onMounted, ref, watch, type Ref } from 'vue'
import { QTree } from 'quasar'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import JobDetails from '@/components/JobDetails.vue'
import JobStatus from '@/components/JobStatus.vue'
import { type JobData } from '@/utils/schema'

const jobsData: Ref<JobData[]> = ref([])
const jobsQTreeRef: Ref<QTree | null> = ref(null)
const splitterModel: Ref<number> = ref(30)
const treeFilter: Ref<string> = ref('')
const jobFamilies: Ref<Map<string, JobData[]>> = ref(new Map())
const jobsByKey: Ref<Map<string, JobData>> = ref(new Map())
const jobsTree: Ref<any[]> = ref([])
const currentJob: Ref<JobData | null> = ref(null)

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
            type: 'job-family',
            children: jobs.map(job => ({
                label: `${job.name} v${job.version}`,
                key: `job:${job.name}-${job.version}`,
                type: 'job',
            }))
        })
    }

    const jobsCount = jobsData.value?.length || 0

    jobsTree.value = [{
        label: `All jobs (${jobsCount})`,
        key: 'root',
        type: 'root',
        children: familyLeafs,
    }]

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
        }
    } else {
        currentJob.value = null
    }
}

function getJobByKey(key: string): JobData | null {
    return jobsByKey.value?.get(key) || null
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

                    <div class="q-mr-sm">
                        <q-input filled v-model="treeFilter" label="Filter" />
                        <q-tree
                            ref="jobsQTreeRef"
                            :nodes="jobsTree"
                            node-key="key"
                            selected-color="primary"
                            default-expand-all
                            :filter="treeFilter"
                            >
                            <template v-slot:default-header="prop">
                                <template v-if="prop.node.type == 'job'">
                                <div @click="selectJobNode(prop.node.key)" class="q-hoverable cursor-pointer full-width">
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
                        <JobDetails :currentJob="currentJob" v-if="currentJob != null"/>
                    </div>
                    
                </template>
            </q-splitter>
        </q-card-section>
    </q-card>
</template>
