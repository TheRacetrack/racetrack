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

const pluginDataRef: Ref<PluginData> = ref({
    plugins: [],
    job_type_versions: [],
    infrastructure_targets: new Map(),
    infrastructure_instances: [],
} as PluginData)
const lifecycleAdminUrl = computed(() => `${envInfo.lifecycle_url}/admin`)
const jobTypeVersionsTreeRef: Ref<QTree | null> = ref(null)
const infrastructureTargetsTreeRef: Ref<QTree | null> = ref(null)

interface PluginManifest {
    name: string
    version: string
    url?: string
    category?: string
}

interface InfrastructureGroup {
    kind: string
    instances: string[]
}

interface PluginData {
    plugins: PluginManifest[]
    job_type_versions: string[]
    infrastructure_targets: Map<string, PluginManifest>
    infrastructure_instances: InfrastructureGroup[]
}

const jobTypeVersionsTree = computed(() => [
    {
        label: 'Available Job Type versions',
        children: pluginDataRef.value?.job_type_versions?.map(jobTypeVersion => ({
            label: jobTypeVersion,
        }))
    },
])

const infrastructureTargetsTree = computed(() => [
    {
        label: 'Available Infrastructure Targets',
        children: pluginDataRef.value?.infrastructure_instances?.map(populateInfraTargetGroup),
    },
])

function populateInfraTargetGroup(group: InfrastructureGroup): any {
    return {
        label: group.kind,
        children: group.instances.map(instance => ({
            label: instance,
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
    apiClient.get<PluginData>(`/api/v1/plugin/tree`).then(response => {
        pluginDataRef.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch plugins data`, err)
    })
}

onMounted(() => {
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
    'red', 'pink', 'blue', 'purple', 'deep-purple', 'indigo', 'light-blue', 'cyan', 'teal', 'green',
    'light-green', 'lime', 'amber', 'orange', 'deep-orange', 'brown', 'grey', 'blue-grey',
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
                />
        </q-card-section>

        <q-card-section class="q-pb-none">
            <div class="text-h6">Infrastructure Targets</div>
            <q-tree
                ref="infrastructureTargetsTreeRef"
                :nodes="infrastructureTargetsTree"
                node-key="label"
                default-expand-all
                />
        </q-card-section>
        <q-card-section class="q-py-none">
            
        </q-card-section>
    </q-card>
    
    <q-card class="q-my-lg">
        <q-card-section class="q-pb-none">
            <div class="text-h6">Plugins</div>
        </q-card-section>
        <q-card-section>

            <q-list bordered separator class="rounded-borders">
                <q-item-label header>Active plugins</q-item-label>

                <q-item v-if="pluginDataRef.plugins.length == 0" class="text-grey-6">(empty)</q-item>

                <q-item v-for="plugin in pluginDataRef.plugins">
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
                        </div>
                    </q-item-section>
                </q-item>
            </q-list>
            
        </q-card-section>

        <q-card-section>
            <q-uploader
                url="/dashboard/api/v1/plugin/upload"
                label="Upload plugin"
                :headers="[{name: authHeader, value: authToken}]"
                field-name="file"
                @failed="onPluginUploadFailed"
                @uploaded="onPluginUploaded"
                style="width: 100%"
                />
        </q-card-section>
    </q-card>
</template>
