<script setup lang="ts">
import { ref, type Ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import {formatDuration, timestampToLocalTime} from '@/utils/time'
import {type DeploymentDto} from '@/utils/api-schema'
import TimeAgoLabel from "@/components/jobs/TimeAgoLabel.vue"
import ManifestView from "@/components/jobs/ManifestView.vue"

const route = useRoute()
const deploymentId = route.params.deploymentId
const deployment: Ref<DeploymentDto | null> = ref(null)

function fetchDeploymentData() {
    apiClient.get<DeploymentDto>(`/api/v1/deploy/${deploymentId}`)
        .then(response => {
            deployment.value = response.data
        }).catch(err => {
            toastService.showErrorDetails(`Failed to fetch deployments`, err)
        })
}

onMounted(() => {
    fetchDeploymentData()
})
</script>
<template>
    <q-card>

        <q-card-section>
            <div class="text-h6">Deployment Details</div>
        </q-card-section>

        <q-card-section>
            <q-field outlined label="Deployment ID" stack-label>
                <template v-slot:control>
                    {{ deployment?.id }}
                </template>
            </q-field>

            <div class="full-width row wrap justify-start items-start content-start">
                <div class="col-6">
                    <q-field outlined label="Status" stack-label>
                        <template v-slot:prepend>
                            <q-spinner color="primary" size="2em" v-if="deployment?.status == 'in_progress'"/>
                            <q-icon color="positive" name="check_circle" v-if="deployment?.status == 'done'"/>
                            <q-icon color="negative" name="error" v-if="deployment?.status == 'failed'"/>
                        </template>
                        <template v-slot:control>
                            {{deployment?.status.toUpperCase()}}
                        </template>
                    </q-field>
                </div>
                <div class="col-6">
                    <q-field outlined label="Phase" stack-label>
                        <template v-slot:control>
                            <div>{{ deployment?.phase }}</div>
                        </template>
                    </q-field>
                </div>
                <div class="col-6">
                    <q-field outlined label="Deployed by" stack-label>
                        <template v-slot:control>
                            {{deployment?.deployed_by}}
                        </template>
                    </q-field>
                </div>
                <div class="col-6">
                    <q-field outlined label="Infrastructure target" stack-label>
                        <template v-slot:control>
                            <div>{{ deployment?.infrastructure_target }}</div>
                        </template>
                    </q-field>
                </div>
                <div class="col-6">
                    <q-field outlined label="Job name (and version)" stack-label>
                        <template v-slot:control>
                            <div>{{ deployment?.job_name }} ({{ deployment?.job_version }})</div>
                        </template>
                    </q-field>
                </div>
                <div class="col-6">
                    <q-field outlined label="Duration" stack-label>
                        <template v-slot:control>
                            {{ formatDuration(deployment?.create_time, deployment?.update_time) }}
                        </template>
                    </q-field>
                </div>
            </div>

            <q-field outlined label="Started at" stack-label>
                <template v-slot:prepend><q-icon name="event" /></template>
                <template v-slot:control>
                    {{timestampToLocalTime(deployment?.create_time)}}
                    <span>&nbsp;</span>
                    <TimeAgoLabel :timestamp="deployment?.create_time" />
                </template>
            </q-field>

            <q-field outlined label="Updated at" stack-label>
                <template v-slot:prepend><q-icon name="event" /></template>
                <template v-slot:control>
                    {{timestampToLocalTime(deployment?.update_time)}}
                    <span>&nbsp;</span>
                    <TimeAgoLabel :timestamp="deployment?.update_time" />
                </template>
            </q-field>

            <q-field v-if="deployment?.error" outlined label="Error" stack-label>
                <template v-slot:control>
                    <span class="x-monospace x-overflow-any">
                        {{ deployment?.error }}
                    </span>
                </template>
            </q-field>

            <q-field outlined label="Manifest" stack-label>
                <template v-slot:control>
                    <ManifestView :manifestYaml="deployment?.manifest_yaml" />
                </template>
            </q-field>
        </q-card-section>

    </q-card>
</template>
