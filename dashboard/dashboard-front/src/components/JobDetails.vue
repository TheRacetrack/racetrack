<script setup lang="ts">
import { type Ref, computed } from 'vue'
import { type JobData } from '@/utils/schema'
import JobStatus from '@/components/JobStatus.vue'
import { timestampToLocalTime, timestampPrettyAgo } from '@/services/DateUtils'

const props = defineProps(['currentJob'])
const job: Ref<JobData | null> = computed(() => props.currentJob)
</script>

<template>
    <q-field outlined label="Job name (and version)" stack-label>
        <template v-slot:control>
            <div>{{ job?.name }} ({{ job?.version }})</div>
        </template>
    </q-field>

    <q-field outlined label="Status" stack-label>
        <template v-slot:control>
            <JobStatus :status="job?.status" />
        </template>
    </q-field>

    <q-field outlined label="Infrastructure target" stack-label>
        <template v-slot:control>
            <div>{{ job?.infrastructure_target }}</div>
        </template>
    </q-field>

    <q-field outlined label="Job type version" stack-label>
        <template v-slot:control>
            <div>{{ job?.job_type_version }}</div>
        </template>
    </q-field>

    <q-field v-if="job?.error" outlined label="Error" stack-label class="q-mt-md">
        <template v-slot:control>
            <span class="x-monospace x-overflow-any">
                {{ job?.error }}
            </span>
        </template>
    </q-field>

    <q-field outlined label="Deployed by" stack-label>
        <template v-slot:control>
            {{job?.deployed_by}}
        </template>
    </q-field>

    <q-field outlined label="Created at" stack-label>
        <template v-slot:prepend><q-icon name="event" /></template>
        <template v-slot:control>
            {{timestampToLocalTime(job?.create_time)}}
            <span>&nbsp;</span>
            <q-badge color="primary" rounded outline>{{timestampPrettyAgo(job?.create_time)}}</q-badge>
        </template>
    </q-field>

    <q-field outlined label="Updated at" stack-label>
        <template v-slot:prepend><q-icon name="event" /></template>
        <template v-slot:control>
            {{timestampToLocalTime(job?.update_time)}}
            <span>&nbsp;</span>
            <q-badge color="primary" rounded outline>{{timestampPrettyAgo(job?.update_time)}}</q-badge>
        </template>
    </q-field>

    <q-field outlined label="Last called at" stack-label>
        <template v-slot:prepend><q-icon name="event" /></template>
        <template v-slot:control>
            {{timestampToLocalTime(job?.last_call_time)}}
            <span>&nbsp;</span>
            <q-badge color="primary" rounded outline>{{timestampPrettyAgo(job?.last_call_time)}}</q-badge>
        </template>
    </q-field>

    <q-field outlined label="Manifest" stack-label class="q-mt-md">
        <template v-slot:control>
            <span class="x-monospace x-overflow-any">
                {{ job?.manifest }}
            </span>
        </template>
    </q-field>

    <p>Pub URL: {{ job?.pub_url }}</p>
</template>
