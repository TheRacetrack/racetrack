<script setup lang="ts">
import { ref, type Ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import { progressService } from '@/services/ProgressService'

const route = useRoute()
const pluginName = route.params.pluginName
const pluginVersion = route.params.pluginVersion

const configRef: Ref<string> = ref('')
const loading = ref(false)

function fetchPluginData() {
    apiClient.get<string>(`/api/v1/plugin/${pluginName}/${pluginVersion}/config`).then(response => {
        configRef.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch plugin data`, err)
    })
}

onMounted(() => {
    fetchPluginData()
})

function saveConfig() {
    progressService.runLoading({
        task: apiClient.put(`/api/v1/plugin/${pluginName}/${pluginVersion}/config`, {
            config_data: configRef.value,
        }),
        loadingState: loading,
        progressMsg: `Saving plugin's config...`,
        successMsg: `Plugin's config saved.`,
        errorMsg: `Failed to save plugin config`,
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
            <div class="row q-pt-sm">
                <q-space />
                <q-btn color="primary" push label="Save" icon="save"
                    @click="saveConfig" :loading="loading" />
            </div>
        </q-card-section>
    </q-card>
</template>
