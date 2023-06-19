<script setup lang="ts">
import { type Ref, computed, ref } from 'vue'
import { openURL } from 'quasar'
import { mdiDotsVertical, mdiTextBoxOutline } from '@quasar/extras/mdi-v7'
import hljs from 'highlight.js/lib/core'
import hljs_yaml from 'highlight.js/lib/languages/yaml'
import { progressService } from '@/services/ProgressService'
import { apiClient } from '@/services/ApiClient'
import { type JobData } from '@/utils/api-schema'
import { timestampToLocalTime } from '@/utils/time'
import JobStatus from '@/components/jobs/JobStatus.vue'
import DeleteJobButton from '@/components/jobs/DeleteJobButton.vue'
import LogsView from '@/components/jobs/LogsView.vue'
import { getJobGraphanaUrl } from '@/utils/jobs'
import ManifestEditDialog from './ManifestEditDialog.vue'
import TimeAgoLabel from './TimeAgoLabel.vue'
import 'highlight.js/styles/github.css'

hljs.registerLanguage('yaml', hljs_yaml)

const emit = defineEmits(['refreshJobs'])
const props = defineProps(['currentJob'])
const job: Ref<JobData> = computed(() => props.currentJob)
const loadingRedeploy = ref(false)

const logsTitle: Ref<string> = ref('')
const logsContent: Ref<string> = ref('')
const logsOpen: Ref<boolean> = ref(false)
const loadingLogs: Ref<boolean> = ref(false)
const manifestDialogRef: Ref<typeof ManifestEditDialog | null> = ref(null)

const manifestYaml: Ref<string> = computed(() => {
    return job.value?.manifest_yaml || ''
})

const manifestHtml: Ref<string> = computed(() => {
    let html = hljs.highlight(manifestYaml.value, {language: 'yaml'}).value
    html = html.replaceAll('\n', '<br>')
    return html
})

function showBuildLogs(job: JobData) {
    progressService.runLoading({
        task: apiClient.get(`/api/v1/job/${job.name}/${job.version}/build-logs/plain`),
        loadingState: loadingLogs,
        progressMsg: `Loading build logs...`,
        errorMsg: `Failed to load build logs`,
        onSuccess: (response) => {
            logsTitle.value = `Build logs of ${job.name} ${job.version}`
            logsContent.value = response.data
            logsOpen.value = true
        },
    })
}

function showRuntimeLogs(job: JobData) {
    progressService.runLoading({
        task: apiClient.get(`/api/v1/job/${job.name}/${job.version}/logs/plain`),
        loadingState: loadingLogs,
        progressMsg: `Loading runtime logs...`,
        errorMsg: `Failed to load runtime logs`,
        onSuccess: (response) => {
            logsTitle.value = `Runtime logs of ${job.name} ${job.version}`
            logsContent.value = response.data
            logsOpen.value = true
        },
    })
}

function closeLogs() {
    logsOpen.value = false
    logsContent.value = ''
}

function redeployJob(job: JobData) {
    const name: string = job.name
    const version: string = job.version
    progressService.confirmWithLoading({
        confirmQuestion: `Do you really want to redeploy the job "${name} ${version}" (rebuild it and reprovision)?`,
        onConfirm: () => {
            loadingRedeploy.value = true
            return apiClient.post(`/api/v1/job/${name}/${version}/redeploy`)
        },
        progressMsg: `Redeploying job ${name} ${version}...`,
        successMsg: `Job ${name} ${version} has been redeployed.`,
        errorMsg: `Failed to redeploy a job ${name} ${version}`,
        onSuccess: () => {
            emit('refreshJobs', null)
        },
        onFinalize: () => {
            loadingRedeploy.value = false
        },
    })
}

function reprovisionJob(job: JobData) {
    const name: string = job.name
    const version: string = job.version
    progressService.confirmWithLoading({
        confirmQuestion: `Do you really want to reprovision the job "${name} ${version}" (deploy it without rebuilding)?`,
        onConfirm: () => {
            loadingRedeploy.value = true
            return apiClient.post(`/api/v1/job/${name}/${version}/reprovision`)
        },
        progressMsg: `Reprovisioning job ${name} ${version}...`,
        successMsg: `Job ${name} ${version} has been reprovisioned.`,
        errorMsg: `Failed to reprovision a job ${name} ${version}`,
        onSuccess: () => {
            emit('refreshJobs', null)
        },
        onFinalize: () => {
            loadingRedeploy.value = false
        },
    })
}

function openJobGrafanaDashboard(job: JobData) {
    openURL(getJobGraphanaUrl(job))
}

function editJobManifest(job: JobData) {
    manifestDialogRef.value?.openDialog(job, manifestYaml.value)
}

function onManifestUpdated() {
    emit('refreshJobs', null)
    const jobData: JobData = job.value
    const name: string = jobData.name
    const version: string = jobData.version
    progressService.runLoading({
        task: apiClient.post(`/api/v1/job/${name}/${version}/redeploy`),
        progressMsg: `Redeploying job ${name} ${version}...`,
        successMsg: `Job ${name} ${version} has been redeployed.`,
        errorMsg: `Failed to redeploy a job ${name} ${version}`,
    })
}
</script>

<template>

    <LogsView :title="logsTitle" :content="logsContent" :open="logsOpen" @close="closeLogs" />
    <ManifestEditDialog ref="manifestDialogRef" @jobUpdated="onManifestUpdated" />

    <div class="full-width row wrap justify-end">
    <q-btn-group push class="q-mb-md self-end">
        <q-btn color="primary" push label="Open" icon="open_in_new"
            @click="openURL(job?.pub_url as string)" />

        <q-btn-dropdown push color="primary" label="Logs" :icon="mdiTextBoxOutline" :loading="loadingLogs">
            <q-list>
                <q-item clickable v-close-popup @click="showBuildLogs(job)">
                    <q-item-section>
                        <q-item-label>Build logs</q-item-label>
                    </q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="showRuntimeLogs(job)">
                    <q-item-section>
                        <q-item-label>Runtime logs</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </q-btn-dropdown>

        <q-btn-dropdown push color="primary" label="Redeploy" icon="build" :loading="loadingRedeploy">
            <q-list>
                <q-item clickable v-close-popup @click="redeployJob(job)">
                    <q-item-section>
                        <q-item-label>Rebuild and provision</q-item-label>
                    </q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="reprovisionJob(job)">
                    <q-item-section>
                        <q-item-label>Reprovision</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </q-btn-dropdown>

        <DeleteJobButton :jobName="job?.name || ''" :jobVersion="job?.version || ''"
            @jobDeleted="emit('refreshJobs', null)" />

        <q-btn-dropdown push color="white" label="" :dropdown-icon="mdiDotsVertical" text-color="black" no-icon-animation>
            <q-list>
                <q-item clickable v-close-popup @click="openJobGrafanaDashboard(job)">
                    <q-item-section>
                        <q-item-label><q-icon name="open_in_new" /> Open Grafana Dashboard</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </q-btn-dropdown>
    </q-btn-group>
    </div>

    <q-field outlined label="Job name (and version)" stack-label>
        <template v-slot:control>
            <div>{{ job?.name }} ({{ job?.version }})</div>
        </template>
    </q-field>

    <div class="full-width row wrap justify-start items-start content-start">
        <div class="col-6">
            <q-field outlined label="Status" stack-label>
                <template v-slot:control>
                    <JobStatus :status="job?.status" />
                </template>
            </q-field>
        </div>
        <div class="col-6">
            <q-field outlined label="Deployed by" stack-label>
                <template v-slot:control>
                    {{job?.deployed_by}}
                </template>
            </q-field>
        </div>
        <div class="col-6">
            <q-field outlined label="Job type version" stack-label>
                <template v-slot:control>
                    <div>{{ job?.job_type_version }}</div>
                </template>
            </q-field>
        </div>
        <div class="col-6">
            <q-field outlined label="Infrastructure target" stack-label>
                <template v-slot:control>
                    <div>{{ job?.infrastructure_target }}</div>
                </template>
            </q-field>
        </div>
    </div>

    <q-field v-if="job?.error" outlined label="Error" stack-label>
        <template v-slot:control>
            <span class="x-monospace x-overflow-any">
                {{ job?.error }}
            </span>
        </template>
    </q-field>

    <q-field v-if="job?.notice" outlined label="Notice" stack-label>
        <template v-slot:control>
            {{ job?.notice }}
        </template>
    </q-field>

    <q-field outlined label="Created at" stack-label>
        <template v-slot:prepend><q-icon name="event" /></template>
        <template v-slot:control>
            {{timestampToLocalTime(job?.create_time)}}
            <span>&nbsp;</span>
            <TimeAgoLabel :timestamp="job?.create_time" />
        </template>
    </q-field>

    <q-field outlined label="Updated at" stack-label>
        <template v-slot:prepend><q-icon name="event" /></template>
        <template v-slot:control>
            {{timestampToLocalTime(job?.update_time)}}
            <span>&nbsp;</span>
            <TimeAgoLabel :timestamp="job?.update_time" />
        </template>
    </q-field>

    <q-field outlined label="Last called at" stack-label>
        <template v-slot:prepend><q-icon name="event" /></template>
        <template v-slot:control>
            {{timestampToLocalTime(job?.last_call_time)}}
            <span>&nbsp;</span>
            <TimeAgoLabel :timestamp="job?.last_call_time" />
        </template>
    </q-field>

    <q-field outlined label="Manifest" stack-label class="q-mt-md">
        <template v-slot:control>
            <div class="x-monospace x-overflow-any" v-html="manifestHtml" style="white-space: pre;"></div>
        </template>
        <template v-slot:append>
            <q-btn round flat icon="edit" @click="editJobManifest(job)">
                <q-tooltip>Edit Manifest</q-tooltip>
            </q-btn>
        </template>
    </q-field>

</template>
