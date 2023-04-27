<script setup lang="ts">
import { type Ref, computed } from 'vue'
import { openURL } from 'quasar'
import { type JobData } from '@/utils/schema'
import JobStatus from '@/components/JobStatus.vue'
import * as yaml from 'js-yaml'
import { timestampToLocalTime, timestampPrettyAgo } from '@/services/DateUtils'
import DeleteJobButton from '@/components/DeleteJobButton.vue'

const emit = defineEmits(['refreshJobs'])
const props = defineProps(['currentJob'])
const job: Ref<JobData | null> = computed(() => props.currentJob)

const manifestYaml: Ref<string> = computed(() => 
    yaml.dump(removeNulls(job.value?.manifest)) || ''
)

function showBuildLogs(job: JobData | null) {
}

function showRuntimeLogs(job: JobData | null) {
}

function removeNulls(obj: any): any {
    if (Array.isArray(obj)) {
        return obj.filter(x => x != null).map(x => removeNulls(x))
    } else if (typeof obj === 'object') {
        const newObj: any = {}
        for (let [k, v] of Object.entries(obj)) {
            if (k !== null && v !== null) {
                newObj[k] = removeNulls(v)
            }
        }
        return newObj
    }
    return obj
}
</script>

<template>

    <div class="full-width row wrap justify-end">
    <q-btn-group push class="q-mb-md self-end">
        <q-btn color="primary" push label="Open" icon="open_in_new"
            @click="openURL(job?.pub_url as string)" />

        <q-btn-dropdown push color="primary" label="Logs">
            <q-list>
                <q-item clickable v-close-popup @click="showBuildLogs(job)">
                    <q-item-section>
                        <q-item-label>Build logs</q-item-label>
                    </q-item-section>
                </q-item>
                <q-item clickable v-close-popup @click="showRuntimeLogs(job)">
                    <q-item-section>
                        <q-item-label>Runtime logs</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </q-btn-dropdown>

        <q-btn-dropdown push color="primary" label="Redeploy" icon="build">
            <q-list>
                <q-item clickable v-close-popup>
                    <q-item-section>
                        <q-item-label>Rebuild and provision</q-item-label>
                    </q-item-section>
                </q-item>
                <q-item clickable v-close-popup>
                    <q-item-section>
                        <q-item-label>Reprovision</q-item-label>
                    </q-item-section>
                </q-item>
            </q-list>
        </q-btn-dropdown>

        <DeleteJobButton :jobName="job?.name || ''" :jobVersion="job?.version || ''"
            @deleteJob="emit('refreshJobs', null)" />
    </q-btn-group>
    </div>

    <q-field outlined label="Job name (and version)" stack-label>
        <template v-slot:control>
            <div>{{ job?.name }} ({{ job?.version }})</div>
        </template>
    </q-field>

    <div class="full-width row wrap justify-start items-start content-start">
        <div class="col-6">
            <q-field outlined label="Status" stack-label>
                <template v-slot:control>
                    <JobStatus :status="job?.status" />
                </template>
            </q-field>
        </div>
        <div class="col-6">
            <q-field outlined label="Deployed by" stack-label>
                <template v-slot:control>
                    {{job?.deployed_by}}
                </template>
            </q-field>
        </div>
        <div class="col-6">
            <q-field outlined label="Job type version" stack-label>
                <template v-slot:control>
                    <div>{{ job?.job_type_version }}</div>
                </template>
            </q-field>
        </div>
        <div class="col-6">
            <q-field outlined label="Infrastructure target" stack-label>
                <template v-slot:control>
                    <div>{{ job?.infrastructure_target }}</div>
                </template>
            </q-field>
        </div>
    </div>

    <q-field v-if="job?.error" outlined label="Error" stack-label class="q-mt-md">
        <template v-slot:control>
            <span class="x-monospace x-overflow-any">
                {{ job?.error }}
            </span>
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
            <pre class="x-monospace x-overflow-any">{{ manifestYaml }}</pre>
        </template>
    </q-field>

</template>
