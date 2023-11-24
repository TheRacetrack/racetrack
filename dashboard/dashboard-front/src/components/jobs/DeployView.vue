<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { QTree } from 'quasar'
import { io, Socket } from "socket.io-client"
import { mdiDotsVertical } from '@quasar/extras/mdi-v7'
import { outlinedInfo } from '@quasar/extras/material-icons-outlined'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import { envInfo } from '@/services/EnvironmentInfo'
import { type JobData } from '@/utils/api-schema'
import JobDetails from '@/components/jobs/JobDetails.vue'
import JobStatus from '@/components/jobs/JobStatus.vue'
import TimeAgoLabel from '@/components/jobs/TimeAgoLabel.vue'
import { JobOrder, filterJobByKeyword, sortedJobs } from '@/utils/jobs'
import {progressService} from "@/services/ProgressService";

const yamlManifestRef: Ref<string> = ref('')
const gitUsername = ref('')
const gitPassword = ref('')
const forceEnabled: Ref<boolean> = ref(false)
const loading = ref(false)

function deployJob() {
    progressService.runLoading({
        task: apiClient.post(`/api/v1/deploy`, {
        }),
        loadingState: loading,
        progressMsg: `Deploying a job...`,
        successMsg: `Job deployed.`,
        errorMsg: `Failed to deploy a job`,
    })
}
</script>
<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <div class="text-h6">Deploy a new Job</div>
        </q-card-section>
        
        <q-card-section class="q-pt-none">
            <p>YAML Manifest of a job:</p>
            <div>
                <q-input
                    outlined
                    v-model="yamlManifestRef"
                    label="YAML Manifest"
                    type="textarea"
                    class="x-monospace"
                    input-style="min-height: 20em !important;"
                    autogrow
                    />
            </div>
            <q-input outlined type="text" label="Git repository username (optional)" name="git_username"
              v-model="gitUsername"
              />
            <q-input outlined type="password" label="Git repository auth token (optional)" name="git_password"
              v-model="gitPassword"
              />
            <div>
              <q-checkbox v-model="forceEnabled" label="Overwrite existing job (force)">
                  <q-tooltip>Apply "force" flag to overwrite existing job</q-tooltip>
              </q-checkbox>
            </div>
            <div class="row q-pt-sm">
                <q-space />
                <q-btn color="primary" push label="Deploy" icon="save"
                    @click="deployJob" :loading="loading" />
            </div>
        </q-card-section>

    </q-card>
</template>
