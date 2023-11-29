<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import { timestampPrettyAgo, timestampToLocalTime } from '@/utils/time'
import { type DeploymentDto } from '@/utils/api-schema'

const deploymentsData = ref<DeploymentDto[]>([])
const loading = ref(false)

function fetchDeploymentsData() {
    loading.value = true
    apiClient.get<DeploymentDto[]>(`/api/v1/deploy`)
        .then(response => {
            deploymentsData.value = response.data
        }).catch(err => {
            toastService.showErrorDetails(`Failed to fetch deployments`, err)
        }).finally(() => {
            loading.value = false
        })
}

onMounted(() => {
    fetchDeploymentsData()
})
</script>
<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <span class="text-h6">
                Deployments
                <q-tooltip>Recent deployment attempts</q-tooltip>
            </span>
        </q-card-section>

        <q-card-section class="q-pb-none">
            <div class="full-width row wrap justify-end">
                <q-btn color="primary" push label="Deploy a new job" icon="add" :to="{name: 'deploy-job'}" />
            </div>
        </q-card-section>

        <q-card-section>
            <q-list bordered separator class="rounded-borders">

                <q-item v-if="!deploymentsData.length" class="text-grey-6">(empty)</q-item>

                <q-item clickable v-ripple
                        v-for="item in deploymentsData"
                        :to="{name: 'deployment-details', params: {deploymentId: item.id}}">

                    <q-item-section avatar>
                        <q-spinner color="primary" size="2em" v-if="item.status == 'in_progress'"/>
                        <q-icon color="positive" name="check_circle" v-if="item.status == 'done'"/>
                        <q-icon color="negative" name="error" v-if="item.status == 'failed'"/>
                    </q-item-section>

                    <q-item-section>
                        <q-item-label>{{item.job_name}} {{item.job_version}}, by {{item.deployed_by}}</q-item-label>
                        <q-item-label caption>{{item.status.toUpperCase()}}, {{item.id}}</q-item-label>
                    </q-item-section>

                    <q-item-section side>
                        <q-item-label>
                            {{timestampPrettyAgo(item.update_time)}}
                            <q-tooltip>{{timestampToLocalTime(item.update_time)}}</q-tooltip>
                        </q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </q-card-section>

    </q-card>
</template>
