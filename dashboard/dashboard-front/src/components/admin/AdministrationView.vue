<script setup lang="ts">
import { computed, ref, watch, type Ref, onMounted, nextTick } from 'vue'
import { copyToClipboard, QTree } from 'quasar'
import { envInfo } from '@/services/EnvironmentInfo'
import { toastService } from '@/services/ToastService'
import { apiClient, authHeader } from '@/services/ApiClient'
import { versionFull } from '@/services/EnvironmentInfo'
import { progressService } from '@/services/ProgressService'
import { authToken } from '@/services/UserDataStore'
import { extractErrorDetails } from "@/utils/error"
import { rememberInLocalStorage } from '@/utils/storage'
import XTooltip from '@/components/XTooltip.vue'

const pluginsDataRef: Ref<PluginsData> = ref({
    plugins: [],
    job_type_plugins_data: [],
    infrastructure_plugins_data: [],
} as PluginsData)
const lifecycleAdminUrl = computed(() => `${envInfo.lifecycle_url}/admin`)
const jobTypeVersionsTreeRef: Ref<QTree | null> = ref(null)
const infrastructureTargetsTreeRef: Ref<QTree | null> = ref(null)
const replacePlugins: Ref<boolean> = ref(false)
const loading = ref(false)

interface PluginManifest {
    name: string
    version: string
    url?: string
    category?: string
}

interface JobTypeData {
    name: string
    active_jobs: number
}

interface JobTypePluginData {
    name: string
    version: string
    job_types: JobTypeData[]
}

interface InfrastructureData {
    name: string
    active_jobs: number
}

interface InfrastructurePluginData {
    name: string
    version: string
    infrastructures: InfrastructureData[]
}

interface PluginsData {
    plugins: PluginManifest[]
    job_type_plugins_data: JobTypePluginData[]
    infrastructure_plugins_data: InfrastructurePluginData[]
}

const jobTypeVersionsTree = computed(() => [{
    label: 'Available Job Type versions',
    children: pluginsDataRef.value?.job_type_plugins_data?.map(populateJobTypeGroup),
}])

const populateJobTypeGroup = (group: JobTypePluginData) => {
    return {
        label: `${group.name} ${group.version}`,
        rt_type: 'plugin',
        children: group.job_types.map((jobtype: JobTypeData) => ({
            label: jobtype.name,
            rt_jobs: jobtype.active_jobs,
        }))
    }
}

const infrastructureTargetsTree = computed(() => [{
    label: 'Available Infrastructure Targets',
    children: pluginsDataRef.value?.infrastructure_plugins_data?.map(populateInfrastructureGroup),
}])

const populateInfrastructureGroup = (group: InfrastructurePluginData) => {
    return {
        label: `${group.name} ${group.version}`,
        rt_type: 'plugin',
        children: group.infrastructures.map((infrastructure: InfrastructureData) => ({
            label: infrastructure.name,
            rt_jobs: infrastructure.active_jobs,
        }))
    }
}

watch(jobTypeVersionsTree, () => {
    nextTick(() => {
        jobTypeVersionsTreeRef.value?.expandAll()
    })
})

watch(infrastructureTargetsTree, () => {
    nextTick(() => {
        infrastructureTargetsTreeRef.value?.expandAll()
    })
})

function copyText(text: string | null) {
    if (!text)
        return
    copyToClipboard(text)
        .then(() => {
            toastService.success(`Copied to clipboard.`)
        }).catch((error) => {
            toastService.error(`Failed to copy to clipboard.`)
        })
}

function fetchPluginsData() {
    apiClient.get<PluginsData>(`/api/v1/plugin/tree`).then(response => {
        const pluginData: PluginsData = response.data
        pluginData.plugins.sort((a, b) => a.name.localeCompare(b.name) || a.version.localeCompare(b.version))
        pluginsDataRef.value = pluginData
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch plugins data`, err)
    })
}

onMounted(() => {
    rememberInLocalStorage(replacePlugins, 'administration.replacePlugins')
    fetchPluginsData()
})

function deletePlugin(name: string, version: string) {
    progressService.confirmWithLoading({
        confirmQuestion: `Are you sure you want to delete the plugin "${name} ${version}"?`,
        onConfirm: () => {
            return apiClient.delete(`/api/v1/plugin/${name}/${version}`)
        },
        progressMsg: `Deleting plugin ${name} ${version}...`,
        successMsg: `Plugin ${name} ${version} has been deleted.`,
        errorMsg: `Failed to delete plugin ${name} ${version}`,
        onSuccess: () => {
            fetchPluginsData()
        },
    })
}

const downloadPlugin = (name: string, version: string) => {
    window.location.href = `/dashboard/api/v1/plugin/${name}/${version}/download`;
};

function onPluginUploadFailed(err: any) {
    console.error(err)
    let details = extractErrorDetails(err)
    toastService.showErrorDetails(`Failed to upload plugin`, details)
}

function onPluginUploaded(info: any) {
    toastService.success(`Plugin uploaded`)
    fetchPluginsData()
}

const badgeColors = [
    'pink', 'light-green', 'purple', 'deep-purple', 'green', 'indigo', 'red', 'light-blue', 'cyan', 'teal',
    'blue', 'amber', 'orange', 'deep-orange', 'brown', 'grey', 'blue-grey',
]

function stringToColour(str: string) {
    let hash: number = 0;
    for (let i = 0; i < str.length; i++) {
        const chr = str.charCodeAt(i)
        hash = ((hash << 5) - hash) + chr
        hash |= 0
    }
    const colorIndex = (hash % badgeColors.length + badgeColors.length) % badgeColors.length
    return badgeColors[colorIndex]
}

function reconcileAllJobs() {
    progressService.runLoading({
        task: apiClient.post(`/api/v1/job/all/reconcile`, {}),
        loadingState: loading,
        progressMsg: `Reconciling jobs...`,
        successMsg: `Reconciliation finished.`,
        errorMsg: `Failed to reconcile jobs`,
    })
}
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <div class="text-h6">Links</div>
        </q-card-section>
        <q-card-section class="q-pt-none">

            <q-field outlined label="Lifecycle API server address" stack-label class="q-mt-md">
                <template v-slot:control>
                    <a :href="envInfo.lifecycle_url || ''" target="_blank" class="x-overflow-any">
                        {{ envInfo.lifecycle_url }}
                    </a>
                </template>
                <template v-slot:append>
                    <q-btn round dense flat icon="content_copy" @click="copyText(envInfo.lifecycle_url)" />
                </template>
            </q-field>

            <q-field outlined label="Lifecycle Admin panel" stack-label class="q-mt-md">
                <template v-slot:control>
                    <a :href="lifecycleAdminUrl" target="_blank" class="x-overflow-any">
                        {{ lifecycleAdminUrl }}
                    </a>
                </template>
                <template v-slot:append>
                    <q-btn round dense flat icon="content_copy" @click="copyText(lifecycleAdminUrl)" />
                </template>
            </q-field>

            <q-field outlined label="Grafana dashboards" stack-label class="q-mt-md">
                <template v-slot:control>
                    <a :href="envInfo.grafana_url || ''" target="_blank" class="x-overflow-any">
                        {{ envInfo.grafana_url }}
                    </a>
                </template>
                <template v-slot:append>
                    <q-btn round dense flat icon="content_copy" @click="copyText(envInfo.grafana_url)" />
                </template>
            </q-field>

        </q-card-section>
    </q-card>

    <q-card class="q-my-lg q-pb-md">
        <q-card-section class="q-pb-none">
            <div class="text-h6">Versions</div>
        </q-card-section>
        <q-card-section class="q-py-none">
            <q-field outlined label="Racetrack version" stack-label class="q-mt-md">
                <template v-slot:control>
                    <span class="x-monospace x-overflow-any">
                        {{ versionFull }}
                    </span>
                </template>
            </q-field>
        </q-card-section>

        <q-card-section class="q-pb-none">
            <div class="text-h6">Job Types</div>
        </q-card-section>
        <q-card-section class="q-py-none">
            <q-tree
                ref="jobTypeVersionsTreeRef"
                :nodes="jobTypeVersionsTree"
                node-key="label"
                default-expand-all
                dense
                >
                <template v-slot:default-header="prop">
                    <span>
                        {{ prop.node.label }}
                        <template v-if="prop.node.rt_type == 'plugin'">
                            <XTooltip>A plugin providing the job types</XTooltip>
                        </template>
                        <template v-if="prop.node.rt_jobs != null">
                            <q-badge outline :color="prop.node.rt_jobs > 0 ? 'primary' : 'grey'" class="q-ml-sm">
                                {{prop.node.rt_jobs}}
                                <XTooltip>{{prop.node.rt_jobs}} jobs use this job type</XTooltip>
                            </q-badge>
                        </template>
                    </span>
                </template>
            </q-tree>
        </q-card-section>

        <q-card-section class="q-pb-none">
            <div class="text-h6">Infrastructure Targets</div>
            <q-tree
                ref="infrastructureTargetsTreeRef"
                :nodes="infrastructureTargetsTree"
                node-key="label"
                default-expand-all
                dense
                >
                <template v-slot:default-header="prop">
                    <span>
                        {{ prop.node.label }}
                        <template v-if="prop.node.rt_type == 'plugin'">
                            <XTooltip>A plugin providing the infrastructure targets</XTooltip>
                        </template>
                        <template v-if="prop.node.rt_jobs != null">
                            <q-badge outline :color="prop.node.rt_jobs > 0 ? 'primary' : 'grey'" class="q-ml-sm">
                                {{prop.node.rt_jobs}}
                                <XTooltip>{{prop.node.rt_jobs}} jobs use this infrastructure target</XTooltip>
                            </q-badge>
                        </template>
                    </span>
                </template>
            </q-tree>
        </q-card-section>
    </q-card>

    <q-card class="q-my-lg">
        <q-card-section class="q-pb-none">
            <div class="text-h6">Plugins</div>
        </q-card-section>
        <q-card-section>

            <q-list bordered separator class="rounded-borders">
                <q-item-label header>Active plugins</q-item-label>

                <q-item v-if="pluginsDataRef.plugins.length == 0" class="text-grey-6">(empty)</q-item>

                <q-item v-for="plugin in pluginsDataRef.plugins">
                    <q-item-section>
                        <q-item-label>{{ plugin.name }}</q-item-label>
                        <q-item-label caption>
                            Version {{plugin.version}}
                            <span v-if="plugin.category">
                                <q-badge :color="stringToColour(plugin.category)" rounded :label="plugin.category" class="q-ml-xs" />
                            </span>
                        </q-item-label>
                        <q-item-label caption v-if="plugin.url">
                            <a :href="plugin.url" target="_blank">{{ plugin.url }}</a>
                        </q-item-label>
                    </q-item-section>

                    <q-item-section side>
                        <div class="text-grey-8 q-gutter-xs">
                            <q-btn class="gt-xs" size="12px" flat dense round icon="edit"
                                :to="{name: 'plugin-config', params: {pluginName: plugin.name, pluginVersion: plugin.version}}">
                                <q-tooltip>Edit plugin's config</q-tooltip>
                            </q-btn>
                            <q-btn class="gt-xs" size="12px" flat dense round icon="delete"
                                @click="deletePlugin(plugin.name, plugin.version)">
                                <q-tooltip>Delete plugin</q-tooltip>
                            </q-btn>
                            <q-btn class="gt-xs" size="12px" flat dense round icon="download"
                                @click="downloadPlugin(plugin.name, plugin.version)">
                                <q-tooltip>Download plugin</q-tooltip>
                            </q-btn>
                        </div>
                    </q-item-section>
                </q-item>
            </q-list>

        </q-card-section>

        <q-card-section>
            <q-checkbox v-model="replacePlugins" label="Replace on upload">
                <q-tooltip>Delete the existing versions of the same uploaded plugin</q-tooltip>
            </q-checkbox>
            <q-uploader
                :url="`/dashboard/api/v1/plugin/upload?replace=${replacePlugins ? '1' : '0'}`"
                label="Upload plugin"
                :headers="[{name: authHeader, value: authToken}]"
                field-name="file"
                @failed="onPluginUploadFailed"
                @uploaded="onPluginUploaded"
                style="width: 100%"
                />
        </q-card-section>
    </q-card>

    <q-card class="q-my-lg">
        <q-card-section class="q-pb-none">
            <div class="text-h6">Maintenance</div>
        </q-card-section>
        <q-card-section>
            <div class="row q-pt-sm">
                <q-btn color="primary" push label="Reconcile jobs" icon="construction"
                    @click="reconcileAllJobs" :loading="loading">
                    <q-tooltip>Re-provision all missing jobs</q-tooltip>
                </q-btn>
            </div>
        </q-card-section>
    </q-card>
</template>
