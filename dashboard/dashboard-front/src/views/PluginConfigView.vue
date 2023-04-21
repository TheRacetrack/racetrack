<script setup lang="ts">
import { computed, ref, watch, type Ref, onMounted, nextTick } from 'vue'
import { envInfo } from '@/services/EnvironmentInfo'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import { versionFull } from '@/services/EnvironmentInfo'
import { progressService } from '@/services/ProgressService'
import { useRoute, useRouter, type RouteLocationRaw } from 'vue-router'

const route = useRoute()

const pluginName = route.params.pluginName
const pluginVersion = route.params.pluginVersion

const pluginDataRef: Ref<PluginData | null> = ref(null)
const configRef: Ref<string> = ref('')

interface PluginData {
    plugin_name: string
    plugin_version: string
    plugin_config: string
}

function fetchPluginData() {
    apiClient.get(`/api/plugin/${pluginName}/${pluginVersion}`).then(response => {
        pluginDataRef.value = response.data
        configRef.value = response.data.plugin_config
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch plugin data`, err)
    })
}

onMounted(() => {
    fetchPluginData()
})

function saveConfig() {
    apiClient.post(`/api/plugin/${pluginName}/${pluginVersion}/config`, {
        config: configRef.value,
    }).then(response => {
        toastService.success(`Plugin's config saved.`)
    }).catch(err => {
        toastService.showErrorDetails(`Failed to save plugin config`, err)
    })
}
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <div class="text-h6">Plugin Config</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
            <p>YAML configuration of plugin <b>{{ pluginName }}</b>:</p>
            <div>
                <q-input
                    outlined
                    v-model="configRef"
                    label="YAML Configuration"
                    type="textarea"
                    class="x-monospace"
                    input-style="min-height: 20em !important;"
                    autogrow
                    />
            </div>
            <q-btn color="primary" push label="Save" icon="save" @click="saveConfig" />
        </q-card-section>
    </q-card>
</template>
