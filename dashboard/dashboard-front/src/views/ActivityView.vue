<script setup lang="ts">
import { computed, ref, watch, type Ref, onMounted, nextTick } from 'vue'
import { copyToClipboard, QTree } from 'quasar'
import { envInfo } from '@/services/EnvironmentInfo'
import { toastService } from '@/services/ToastService'
import { apiClient, authHeader } from '@/services/ApiClient'
import { versionFull } from '@/services/EnvironmentInfo'
import { progressService } from '@/services/ProgressService'
import { authToken } from '@/services/UserDataStore'
import { timestampToLocalTime, formatTimestampIso8601 } from '@/services/DateUtils'

const auditLogData: Ref<AuditLogData> = ref({
    events: [],
} as AuditLogData)
const jobNameFilter: Ref<string> = ref('')
const jobVersionFilter: Ref<string> = ref('')
const relatedToMeFilter: Ref<boolean> = ref(false)

interface AuditLogData {
    events: AuditLogEvent[]
}

interface AuditLogEvent {
    id: string
    version: number
    timestamp: number
    time_ago: string
    event_type: string
    properties?: Map<string, any>
    username_executor?: string
    username_subject?: string
    job_name?: string
    job_version?: string
    explanation: string
}

function fetchAuditLogData() {
    const encodedJobName = encodeURI(jobNameFilter.value)
    const encodedJobVersion = encodeURI(jobVersionFilter.value)
    const encodedRelatedToMe = relatedToMeFilter.value ? '1' : '0'
    apiClient.get(`/api/v1/audit/activity?job_name=${encodedJobName}&job_version=${encodedJobVersion}&related_to_me=${encodedRelatedToMe}`).then(response => {
        auditLogData.value = response.data
    }).catch(err => {
        toastService.showErrorDetails(`Failed to fetch audit log`, err)
    })
}

function capitalizeEventType(title: string): string {
    title = title.replace(/_/g, ' ')
    title = title.replace(/\w\S*/g, function(txt){
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
    })
    return title
}

onMounted(() => {
    fetchAuditLogData()
})
</script>

<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <div class="text-h6">Audit Log</div>
        </q-card-section>

        <q-card-section>
            <q-card>
                <div class="row">
                    <q-input outlined v-model="jobNameFilter" label="Job Name" @keydown.enter.prevent="fetchAuditLogData" />
                    <q-input outlined v-model="jobVersionFilter" label="Job Version" @keydown.enter.prevent="fetchAuditLogData" />
                    <q-checkbox v-model="relatedToMeFilter" label="Related to me" />
                    <q-space />
                    <q-btn push label="Filter" icon="search" color="primary" @click="fetchAuditLogData" />
                </div>
            </q-card>
        </q-card-section>

        <q-card-section>
            <q-list bordered separator class="rounded-borders">
                
                <q-item v-if="auditLogData.events.length == 0" class="text-grey-6">(empty)</q-item>
                
                <q-item v-for="event in auditLogData.events">
                    <q-item-section>
                        <q-item-label>{{capitalizeEventType(event.event_type)}}</q-item-label>
                        <q-item-label caption>{{event.explanation}}</q-item-label>
                    </q-item-section>
                    
                    <q-item-section side>
                        <q-item-label>
                            {{event.time_ago}}
                            <q-tooltip>{{timestampToLocalTime(event.timestamp)}}</q-tooltip>
                        </q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </q-card-section>
    </q-card>
</template>
