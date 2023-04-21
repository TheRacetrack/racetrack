<script setup lang="ts">
import { computed, ref, watch, type Ref, onMounted, nextTick } from 'vue'
import { copyToClipboard, QTree } from 'quasar'
import { envInfo } from '@/services/EnvironmentInfo'
import { ToastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import { versionFull } from '@/services/EnvironmentInfo'
import { progressService } from '@/services/ProgressService'

const adminDataRef: Ref<AdminData> = ref({
    plugins: [],
    job_type_versions: [],
    infrastructure_targets: new Map(),
    infrastructure_instances: [],
} as AdminData)
const lifecycleAdminUrl = computed(() => `${envInfo.lifecycle_url}/admin`)
const jobTypeVersionsTreeRef: Ref<QTree | null> = ref(null)
const infrastructureTargetsTreeRef: Ref<QTree | null> = ref(null)

interface PluginManifest {
    name: string
    version: string
    url?: string
}

interface InfrastructureGroup {
    kind: string
    instances: string[]
}

interface AdminData {
    plugins: PluginManifest[]
    job_type_versions: string[]
    infrastructure_targets: Map<string, PluginManifest>
    infrastructure_instances: InfrastructureGroup[]
}

const jobTypeVersionsTree = computed(() => [
    {
        label: 'Available Job Type versions',
        children: adminDataRef.value?.job_type_versions?.map(jobTypeVersion => ({
            label: jobTypeVersion,
        }))
    },
])

const infrastructureTargetsTree = computed(() => [
    {
        label: 'Available Infrastructure Targets',
        children: adminDataRef.value?.infrastructure_instances?.map(populateInfraTargetGroup),
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

function getAllTreeLabels(obj: any, labels: string[] = []): string[] {
    if (Array.isArray(obj)) {
        for (const child of obj) {
            getAllTreeLabels(child, labels)
        }
    }
    if (obj.hasOwnProperty('label')) {
        labels.push(obj['label'])
    }
    if (obj.hasOwnProperty('children')) {
        const children = obj['children']
        for (const index in children) {
            const child = children[index]
            getAllTreeLabels(child, labels)
        }
    }
    return labels
}

function copyText(text: string | null) {
    if (text == null)
        return
    copyToClipboard(text)
        .then(() => {
            ToastService.success(`Copied to clipboard.`)
        }).catch((error) => {
            ToastService.error(`Failed to copy to clipboard.`)
        })
}

function fetchAdministrationData() {
    apiClient.get(`/api/administration`).then(response => {
        adminDataRef.value = response.data
    }).catch(err => {
        ToastService.showRequestError(`Failed to fetch administration data`, err)
    })
}

onMounted(() => {
    fetchAdministrationData()
})

function deletePlugin(name: string, version: string) {
    progressService.showDialog(`Are you sure you want to delete the plugin "${name} ${version}"?`)
        .then(async () => {
            ToastService.info(`Deleting a plugin ${name} ${version}...`)
            progressService.startProgressLoading()

            await new Promise(r => setTimeout(r, 2000))

            //TODO DELETE
            return apiClient.get(`/api/plugin/${name}/${version}`)
            
        }).then(response => {
            ToastService.success(`Plugin ${name} ${version} has been deleted.`)
            fetchAdministrationData()

        }).catch(err => {
            ToastService.showRequestError(`Failed to delete a plugin`, err)
        }).finally(() => {
            progressService.stopProgressLoading()
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
                    <a :href="envInfo.lifecycle_url || ''" target="_blank" class="x-monospace x-overflow-any">
                        {{ envInfo.lifecycle_url }}
                    </a>
                </template>
                <template v-slot:append>
                    <q-btn round dense flat icon="content_copy" @click="copyText(envInfo.lifecycle_url)" />
                </template>
            </q-field>
            
            <q-field outlined label="Lifecycle Admin panel" stack-label class="q-mt-md">
                <template v-slot:control>
                    <a :href="lifecycleAdminUrl" target="_blank" class="x-monospace x-overflow-any">
                        {{ lifecycleAdminUrl }}
                    </a>
                </template>
                <template v-slot:append>
                    <q-btn round dense flat icon="content_copy" @click="copyText(lifecycleAdminUrl)" />
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

                <q-item v-if="adminDataRef.plugins.length == 0" class="text-grey-6">(empty)</q-item>

                <q-item v-for="plugin in adminDataRef.plugins">
                    <q-item-section>
                        <q-item-label>{{ plugin.name }}</q-item-label>
                        <q-item-label caption>Version {{plugin.version}}</q-item-label>
                        <q-item-label caption v-if="plugin.url">
                            <a :href="plugin.url" target="_blank">{{ plugin.url }}</a>
                        </q-item-label>
                    </q-item-section>

                    <q-item-section side>
                        <div class="text-grey-8 q-gutter-xs">
                            <q-btn class="gt-xs" size="12px" flat dense round icon="edit">
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
    </q-card>
</template>
