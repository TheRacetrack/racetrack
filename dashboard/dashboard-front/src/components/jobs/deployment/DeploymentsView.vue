<script setup lang="ts">
import { ref, type Ref } from 'vue'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import {progressService} from "@/services/ProgressService"
import yaml from 'js-yaml'

</script>
<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <q-btn color="primary" push label="Deploy a new job" icon="add" :to="{name: 'deploy-job'}" />
        </q-card-section>

        <q-card-section class="">
            <div class="text-h6">Deployments</div>
        </q-card-section>

    </q-card>
</template>
