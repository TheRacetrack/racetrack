<script setup lang="ts">
import { ref, type Ref, onMounted } from 'vue'
import { toastService } from '@/services/ToastService'
import { apiClient } from '@/services/ApiClient'
import { timestampToLocalTime } from '@/utils/time'

const auditLogData: Ref<AuditLogData> = ref({
    events: [],
} as AuditLogData)
const jobNameFilter: Ref<string> = ref('')
const jobVersionFilter: Ref<string> = ref('')
const relatedToMeFilter: Ref<boolean> = ref(false)
const loading = ref(false)

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
    loading.value = true
    const encodedJobName = encodeURI(jobNameFilter.value)
    const encodedJobVersion = encodeURI(jobVersionFilter.value)
    const encodedRelatedToMe = relatedToMeFilter.value ? '1' : '0'
    apiClient.get<AuditLogData>(`/api/v1/audit/activity?job_name=${encodedJobName}&job_version=${encodedJobVersion}&related_to_me=${encodedRelatedToMe}`)
        .then(response => {
            auditLogData.value = response.data
        }).catch(err => {
            toastService.showErrorDetails(`Failed to fetch audit log`, err)
        }).finally(() => {
            loading.value = false
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
            <div class="row">
                <q-input dense outlined v-model="jobNameFilter" label="Filter by job name" @keydown.enter.prevent="fetchAuditLogData" />
                <q-input dense outlined v-model="jobVersionFilter" label="Filter by job version" @keydown.enter.prevent="fetchAuditLogData" />
                <q-checkbox v-model="relatedToMeFilter" label="Only related to me" />
                <q-space />
                <q-btn push label="Filter" icon="search" color="primary" :loading="loading" @click="fetchAuditLogData" />
            </div>
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
