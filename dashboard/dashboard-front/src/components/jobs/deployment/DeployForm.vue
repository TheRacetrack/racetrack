<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import yaml from 'js-yaml'
import { apiClient } from '@/services/ApiClient'
import { toastService } from '@/services/ToastService'
import { progressService } from "@/services/ProgressService"

const yamlManifestRef = ref('')
const gitUsername = ref('')
const gitPassword = ref('')
const forceEnabled = ref(false)
const loading = ref(false)

const router = useRouter()

const deprecatedKeysMap = {
    'lang': 'jobtype',
    'golang': 'jobtype_extra',
    'python': 'jobtype_extra',
    'docker': 'jobtype_extra',
    'wrapper_properties': 'jobtype_extra'
}

interface CredentialsModel {
    username: string
    password: string
}
function deployJob() {
    let manifestDict: Record<string, any>
    try {
        manifestDict = yaml.load(yamlManifestRef.value) as Record<string, any>
        if (typeof manifestDict !== 'object') {
            throw new TypeError('Expected mapping object')
        }
        for (const [deprecatedKey, replacementKey] of Object.entries(deprecatedKeysMap)) {
            if (deprecatedKey in manifestDict) {
                toastService.warning(`${deprecatedKey}: is deprecated. Use ${replacementKey} instead.`);
            }
        }
    } catch(err: any) {
        toastService.showErrorDetails('Invalid Manifest YAML', err)
        return
    }

    let gitCredentials: CredentialsModel | null = null
    if (gitUsername.value !== '' && gitPassword.value !== '') {
        gitCredentials = {
            "username": gitUsername.value,
            "password": gitPassword.value,
        }
    }

    progressService.runLoading({
        task: apiClient.post(`/api/v1/deploy`, {
            "manifest": manifestDict,
            "git_credentials": gitCredentials,
            "secret_vars": null,
            "force": forceEnabled.value,
        }),
        loadingState: loading,
        progressMsg: `Deploying a job...`,
        successMsg: `Job deployment requested.`,
        errorMsg: `Failed to deploy a job`,
        onSuccess: () => {
            router.push({ name: 'deployments' })
        },
    })
}
</script>
<template>
    <q-card>
        <q-card-section class="q-pb-none">
            <div class="text-h6">Deploy a Job</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
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
              <q-checkbox v-model="forceEnabled" label="Overwrite existing job">
                  <q-tooltip>Apply "force" flag to overwrite existing job</q-tooltip>
              </q-checkbox>
            </div>
            <div class="row q-pt-sm">
                <q-space />
                <q-btn color="primary" push label="Deploy" icon="construction"
                    @click="deployJob" :loading="loading" />
            </div>
        </q-card-section>

    </q-card>
</template>
